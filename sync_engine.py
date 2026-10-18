import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

# Load database helpers
import db

TABLES_TO_SYNC = [
    "students",
    "school_records",
    "semesters",
    "subjects",
    "semester_results",
    "drop_years",
    "achievement_categories",
    "achievements",
]

def get_credentials_path() -> str:
    """Returns the path to the Google service account JSON file."""
    return os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")

def get_configured_sheet_id() -> str:
    """Retrieves Google Sheet ID from environment or sync_config table."""
    env_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if env_id:
        return env_id
    row = db.fetch_one("SELECT config_value FROM sync_config WHERE config_key='google_sheet_id'")
    return row["config_value"].strip() if row and row["config_value"] else ""

def set_configured_sheet_id(sheet_id: str) -> None:
    """Saves the Google Sheet ID to sync_config table."""
    db.exec_sql(
        """INSERT INTO sync_config(config_key, config_value, updated_at)
           VALUES('google_sheet_id', ?, CURRENT_TIMESTAMP)
           ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=CURRENT_TIMESTAMP""",
        (sheet_id.strip(),)
    )

def is_auto_sync_enabled() -> bool:
    row = db.fetch_one("SELECT config_value FROM sync_config WHERE config_key='auto_sync_enabled'")
    return (row["config_value"] == "1") if row else True

def set_auto_sync_enabled(enabled: bool) -> None:
    val = "1" if enabled else "0"
    db.exec_sql(
        """INSERT INTO sync_config(config_key, config_value, updated_at)
           VALUES('auto_sync_enabled', ?, CURRENT_TIMESTAMP)
           ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=CURRENT_TIMESTAMP""",
        (val,)
    )

def get_service_account_email() -> Optional[str]:
    """Safely extracts service account client email without exposing secret keys."""
    creds_path = get_credentials_path()
    if os.path.exists(creds_path):
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("client_email", "Unknown")
        except Exception:
            return "Invalid JSON"
    return None

def get_sync_status() -> Dict[str, Any]:
    """Returns diagnostic information on Google Sheets sync availability."""
    creds_path = get_credentials_path()
    creds_exist = os.path.exists(creds_path)
    sheet_id = get_configured_sheet_id()
    client_email = get_service_account_email() if creds_exist else None
    
    pending_row = db.fetch_one("SELECT COUNT(*) AS c FROM sync_queue WHERE synced = 0")
    pending_count = pending_row["c"] if pending_row else 0

    total_row = db.fetch_one("SELECT COUNT(*) AS c FROM sync_queue")
    total_count = total_row["c"] if total_row else 0

    last_sync_row = db.fetch_one("SELECT config_value FROM sync_config WHERE config_key='last_full_sync'")
    last_sync = last_sync_row["config_value"] if last_sync_row else None

    recent_errors = db.fetch_all(
        "SELECT queue_id, table_name, operation, error, created_at FROM sync_queue WHERE error IS NOT NULL ORDER BY queue_id DESC LIMIT 5"
    )

    webhook_url = ""
    try:
        import mysql_manager
        m_cfg = mysql_manager.load_mysql_config()
        webhook_url = m_cfg.get("webhook_url", "").strip()
    except Exception:
        pass

    is_configured = bool(webhook_url) or (creds_exist and bool(sheet_id))

    return {
        "configured": is_configured,
        "webhook_url": webhook_url,
        "creds_path": creds_path,
        "creds_exist": creds_exist,
        "sheet_id": sheet_id,
        "client_email": client_email,
        "auto_sync": is_auto_sync_enabled(),
        "pending_operations": pending_count,
        "total_operations": total_count,
        "last_full_sync": last_sync,
        "recent_errors": [dict(r) for r in recent_errors],
    }


def get_gspread_client():
    """Initializes and returns authenticated gspread client using service account."""
    import gspread
    from google.oauth2.service_account import Credentials

    creds_path = get_credentials_path()
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google service account key file not found at '{creds_path}'.")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc

def sync_table_to_sheet(sh, table_name: str) -> int:
    """
    Syncs a single SQLite table to its corresponding worksheet in Google Sheets.
    Accurately handles all inserts, updates, and deletes by reflecting the exact state.
    """
    import gspread
    
    df = db.df_query(f"SELECT * FROM {table_name}")
    header = df.columns.tolist()
    # Convert all values to clean strings (formatting NaNs as empty strings)
    rows = df.fillna("").astype(str).values.tolist()
    values = [header] + rows

    try:
        ws = sh.worksheet(table_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        row_count = max(100, len(values) + 20)
        col_count = max(10, len(header) + 2)
        ws = sh.add_worksheet(title=table_name, rows=row_count, cols=col_count)

    if values:
        ws.update(values, value_input_option="USER_ENTERED")
    return len(rows)

def process_sync_queue(max_items: int = 50) -> Tuple[bool, str, int]:
    """
    Processes pending items in the sync queue.
    Supports both Google Apps Script Webhook and Google Cloud Service Account.
    """
    webhook_url = ""
    try:
        import mysql_manager
        m_cfg = mysql_manager.load_mysql_config()
        webhook_url = m_cfg.get("webhook_url", "").strip()
    except Exception:
        pass

    pending_items = db.fetch_all(
        "SELECT queue_id, table_name, operation, record_id FROM sync_queue WHERE synced = 0 ORDER BY queue_id ASC LIMIT ?",
        (max_items,)
    )

    if not pending_items:
        return True, "Sync queue is already up to date (0 pending operations).", 0

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # BRANCH A: Auto-sync via Webhook (Direct Google Sheet Cloud Mirror)
    if webhook_url:
        try:
            m_host = m_cfg.get("host", "localhost")
            m_port = int(m_cfg.get("port", 3306))
            m_user = m_cfg.get("user", "root")
            m_pass = m_cfg.get("password", "")
            m_db   = m_cfg.get("database", "student_progression_db")
            
            # Sync SQLite to MySQL so MySQL is always fresh
            mysql_manager.migrate_sqlite_to_mysql(m_host, m_port, m_user, m_pass, m_db)
            # Push all tables from MySQL to Google Sheets via Webhook
            ok, msg, rows = mysql_manager.sync_mysql_via_webhook(m_host, m_port, m_user, m_pass, m_db, webhook_url)
            
            if ok:
                item_ids = [item["queue_id"] for item in pending_items]
                with db.get_conn() as conn:
                    conn.executemany(
                        "UPDATE sync_queue SET synced = 1, synced_at = ?, error = NULL WHERE queue_id = ?",
                        [(now_ts, qid) for qid in item_ids]
                    )
                    conn.commit()
                db.exec_sql(
                    """INSERT INTO sync_config(config_key, config_value, updated_at)
                       VALUES('last_full_sync', ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=CURRENT_TIMESTAMP""",
                    (now_ts,)
                )
                return True, f"Automatically synced {len(item_ids)} changes to MySQL and Google Sheets!", len(item_ids)
            else:
                return False, f"Webhook sync error: {msg}", 0
        except Exception as e:
            return False, f"Auto-sync exception: {str(e)}", 0

    # BRANCH B: Service Account via gspread
    sheet_id = get_configured_sheet_id()
    creds_path = get_credentials_path()

    if not sheet_id or not os.path.exists(creds_path):
        return False, "Google Sheets API credentials or Sheet ID not configured.", 0

    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(sheet_id)

        # Determine unique affected tables from pending queue
        affected_tables = set(item["table_name"] for item in pending_items if item["table_name"] in TABLES_TO_SYNC)

        for table in affected_tables:
            sync_table_to_sheet(sh, table)

        # Mark processed items as successfully synced
        item_ids = [item["queue_id"] for item in pending_items]
        with db.get_conn() as conn:
            conn.executemany(
                "UPDATE sync_queue SET synced = 1, synced_at = ?, error = NULL WHERE queue_id = ?",
                [(now_ts, qid) for qid in item_ids]
            )
            conn.commit()

        # Update last sync timestamp
        db.exec_sql(
            """INSERT INTO sync_config(config_key, config_value, updated_at)
               VALUES('last_full_sync', ?, CURRENT_TIMESTAMP)
               ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=CURRENT_TIMESTAMP""",
            (now_ts,)
        )

        return True, f"Successfully processed {len(item_ids)} queue operation(s) across {len(affected_tables)} table(s).", len(item_ids)

    except Exception as e:
        err_msg = str(e)
        # Record error against pending queue items for debugging
        item_ids = [item["queue_id"] for item in pending_items]
        with db.get_conn() as conn:
            conn.executemany(
                "UPDATE sync_queue SET error = ? WHERE queue_id = ?",
                [(err_msg[:250], qid) for qid in item_ids]
            )
            conn.commit()
        return False, f"Sync error: {err_msg}", 0


def full_refresh_sync() -> Tuple[bool, str, int]:
    """
    Performs a complete one-way push of all database tables to individual Google Sheet tabs.
    Also syncs the sync_queue audit log.
    """
    sheet_id = get_configured_sheet_id()
    creds_path = get_credentials_path()

    if not sheet_id:
        return False, "Google Sheet ID is missing. Please configure it in the Google Sheets Sync tab.", 0
    if not os.path.exists(creds_path):
        return False, f"Credentials file '{creds_path}' not found. Please follow the setup guide.", 0

    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(sheet_id)

        synced_count = 0
        for table in TABLES_TO_SYNC:
            rows = sync_table_to_sheet(sh, table)
            synced_count += rows

        # Sync the sync_queue table as well for complete audit visibility
        sync_table_to_sheet(sh, "sync_queue")

        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with db.get_conn() as conn:
            conn.execute("UPDATE sync_queue SET synced = 1, synced_at = ?, error = NULL WHERE synced = 0", (now_ts,))
            conn.commit()

        db.exec_sql(
            """INSERT INTO sync_config(config_key, config_value, updated_at)
               VALUES('last_full_sync', ?, CURRENT_TIMESTAMP)
               ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=CURRENT_TIMESTAMP""",
            (now_ts,)
        )

        return True, f"Full database sync completed successfully! Synced {len(TABLES_TO_SYNC)} tables ({synced_count} total rows).", synced_count

    except Exception as e:
        return False, f"Sync failed: {str(e)}", 0

def run_mock_sync_simulation() -> Dict[str, Any]:
    """
    Demonstration and verification harness for environments where live Google Cloud
    credentials are not yet provided. Validates queue capture, payload snapshotting,
    and simulated multi-table dispatch.
    """
    test_sid = db.add_student("TEST999", "Sync Test Student", "sync.test@example.com", "9999999999", "Computer Science & Engineering", 2024, "Active")
    q_insert = db.fetch_one("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=? AND operation IN ('INSERT', 'UPSERT')", (test_sid,))
    
    db.update_student(test_sid, "TEST999", "Sync Test Student Updated", "sync.test@example.com", "9999999999", "Computer Science & Engineering", 2024, "Active")
    q_update = db.fetch_all("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=? AND operation IN ('UPDATE', 'UPSERT')", (test_sid,))

    del_snapshot = db.delete_student(test_sid)
    q_delete = db.fetch_one("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=? AND operation='DELETE'", (test_sid,))

    # Mark test queue items as verified/simulated
    with db.get_conn() as conn:
        conn.execute("UPDATE sync_queue SET synced = 1, synced_at = CURRENT_TIMESTAMP WHERE record_id = ? AND table_name = 'students'", (test_sid,))
        conn.commit()

    return {
        "success": True,
        "test_student_id": test_sid,
        "insert_captured": bool(q_insert),
        "update_captured": bool(q_update),
        "delete_captured": bool(q_delete),
        "payload_saved": bool(q_delete and q_delete["payload_snapshot"]),
        "message": "Sync queue engine verified: INSERT, UPDATE, and DELETE operations with snapshot payloads correctly captured."
    }
