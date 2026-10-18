"""
MySQL Database Manager & Google Sheets Bridge
Student Academic Progression & Portfolio Management System
"""

import json
import os
import pymysql
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

CONFIG_FILE = "mysql_config.json"

DEFAULT_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "student_progression_db",
    "webhook_url": "https://script.google.com/macros/s/AKfycbz-OU53NVsK5Bk4vqn5ox6S0Q4Wom093z1zA-E5J8TSzbc571IvzLg8iitOXIZ8P1g_PA/exec"
}

def load_mysql_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_mysql_config(config_dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_dict, f, indent=2)

def test_mysql_connection(host, port, user, password, database=None):
    """Tests if MySQL can connect with given credentials."""
    try:
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database if database else None,
            connect_timeout=5
        )
        version = None
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION();")
            version = cur.fetchone()[0]
        conn.close()
        return True, f"Connected successfully! MySQL Version: {version}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def init_mysql_database(host, port, user, password, schema_file="schema_mysql.sql"):
    """Creates database and tables in MySQL from schema_mysql.sql."""
    try:
        # Connect to MySQL server without specific DB first
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            autocommit=True
        )
        if not os.path.exists(schema_file):
            return False, f"Schema file '{schema_file}' not found."

        with open(schema_file, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Split commands by semicolon while respecting comments
        statements = []
        cur_stmt = []
        for line in sql_script.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("--"):
                continue
            cur_stmt.append(line)
            if clean.endswith(";"):
                statements.append("\n".join(cur_stmt))
                cur_stmt = []

        with conn.cursor() as cur:
            for stmt in statements:
                if stmt.strip():
                    cur.execute(stmt)

        conn.close()
        return True, "Database 'student_progression_db' and 3NF tables initialized successfully in MySQL!"
    except Exception as e:
        return False, f"Schema initialization error: {str(e)}"

def sync_mysql_to_google_sheets(host, port, user, password, database, spreadsheet_id, service_account_path="service_account.json"):
    """Reads all 3NF tables from MySQL and updates corresponding Google Sheets worksheets."""
    if not os.path.exists(service_account_path):
        return False, "Google credentials 'service_account.json' missing.", 0

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(service_account_path, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)

        conn = pymysql.connect(
            host=host, port=int(port), user=user, password=password, database=database
        )

        tables_to_sync = [
            "students", "school_records", "semesters", "subjects",
            "semester_results", "drop_years", "achievements"
        ]
        total_rows_synced = 0

        for tbl in tables_to_sync:
            df = pd.read_sql(f"SELECT * FROM {tbl}", conn)
            # Find or create worksheet
            try:
                ws = spreadsheet.worksheet(tbl)
            except gspread.WorksheetNotFound:
                ws = spreadsheet.add_worksheet(title=tbl, rows="100", cols="20")

            ws.clear()
            if not df.empty:
                # Convert dates/timestamps to string
                df_str = df.astype(str)
                header = df_str.columns.tolist()
                values = [header] + df_str.values.tolist()
                ws.update("A1", values)
                total_rows_synced += len(df)
            else:
                ws.update("A1", [["(Empty Table)"]])

        conn.close()
        return True, f"Synced {len(tables_to_sync)} MySQL tables to Google Sheets! Total rows: {total_rows_synced}", total_rows_synced

    except Exception as e:
        return False, f"Google Sheets Sync Error: {str(e)}", 0

def migrate_sqlite_to_mysql(host, port, user, password, database="student_progression_db", sqlite_path="student_progression.db"):
    """Copies all records from SQLite into MySQL."""
    import sqlite3
    if not os.path.exists(sqlite_path):
        return False, f"SQLite database '{sqlite_path}' does not exist."

    try:
        s_conn = sqlite3.connect(sqlite_path)
        m_conn = pymysql.connect(
            host=host, port=int(port), user=user, password=password, database=database, autocommit=True
        )

        tables = ["students", "school_records", "semesters", "subjects", "semester_results", "drop_years", "achievement_categories", "achievements"]
        total_migrated = 0

        with m_conn.cursor() as cur:
            # Disable FK checks during load
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for tbl in tables:
                df = pd.read_sql(f"SELECT * FROM {tbl}", s_conn)
                if not df.empty:
                    cur.execute(f"TRUNCATE TABLE {tbl};")
                    cols = ", ".join([f"`{c}`" for c in df.columns])
                    placeholders = ", ".join(["%s"] * len(df.columns))
                    sql = f"INSERT INTO `{tbl}` ({cols}) VALUES ({placeholders})"
                    
                    records = []
                    for row in df.itertuples(index=False):
                        # Convert NaNs to None for MySQL NULL
                        clean_row = [None if pd.isna(x) else x for x in row]
                        records.append(tuple(clean_row))

                    cur.executemany(sql, records)
                    total_migrated += len(records)
            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        s_conn.close()
        m_conn.close()
        return True, f"Successfully migrated {total_migrated} rows across {len(tables)} tables from SQLite to MySQL!"
    except Exception as e:
        return False, f"Migration failed: {str(e)}"

def sync_mysql_via_webhook(host, port, user, password, database, webhook_url):
    """Pushes all MySQL tables to a Google Sheet via a deployed Google Apps Script Webhook."""
    import requests
    try:
        conn = pymysql.connect(host=host, port=int(port), user=user, password=password, database=database)
        tables = [
            "students", "school_records", "semesters", "subjects",
            "semester_results", "drop_years", "achievement_categories", "achievements"
        ]
        payload_data = {}
        total_rows = 0

        with conn.cursor() as cur:
            for tbl in tables:
                cur.execute(f"SELECT * FROM `{tbl}`;")
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                clean_rows = []
                for row in rows:
                    clean_rows.append([str(item) if item is not None else "" for item in row])
                payload_data[tbl] = [cols] + clean_rows
                total_rows += len(rows)

        conn.close()

        # Send POST request to Google Apps Script Web App
        resp = requests.post(webhook_url, json={"tables": payload_data}, timeout=30)
        if resp.status_code == 200:
            return True, f"Successfully synced {len(tables)} MySQL tables ({total_rows} rows) to Google Sheets via Webhook!", total_rows
        else:
            return False, f"Google Webhook returned HTTP {resp.status_code}: {resp.text}", 0
    except Exception as e:
        return False, f"Webhook Sync failed: {str(e)}", 0


