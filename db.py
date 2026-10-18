import os
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

DB_PATH = os.getenv("DB_PATH", "student_progression.db")

def get_conn() -> sqlite3.Connection:
    """Returns a thread-safe connection to the SQLite database with FK enforcement."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(schema_file: str = "schema.sql") -> None:
    """
    Initializes database schema and ensures all table columns and constraints
    are migrated properly even on existing database files.
    """
    with get_conn() as conn:
        # Incremental migration helper: check existing table columns
        def ensure_column(table: str, col_name: str, col_def: str):
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if table in tables:
                cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                if col_name not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

        # Check and apply migrations for older databases before executing schema script
        try:
            ensure_column("students", "phone", "TEXT")
            ensure_column("students", "department", "TEXT NOT NULL DEFAULT 'Computer Science & Engineering'")
            ensure_column("school_records", "institution_name", "TEXT")
            ensure_column("subjects", "credits", "REAL NOT NULL DEFAULT 3.0")
            ensure_column("subjects", "department", "TEXT DEFAULT 'Computer Science & Engineering'")
            ensure_column("subjects", "max_theory_marks", "REAL NOT NULL DEFAULT 100.0")
            ensure_column("subjects", "max_lab_marks", "REAL NOT NULL DEFAULT 100.0")
            ensure_column("semester_results", "total_marks", "REAL")
            ensure_column("semester_results", "grade_point", "REAL")
            ensure_column("semester_results", "attendance_percentage", "REAL")
            ensure_column("drop_years", "approved_by", "TEXT")
            ensure_column("achievements", "award_level", "TEXT")
            ensure_column("achievement_categories", "description", "TEXT")
            ensure_column("sync_queue", "payload_snapshot", "TEXT")
            ensure_column("sync_queue", "synced_at", "TEXT")
            conn.commit()
        except Exception:
            pass

        # Load and execute base schema script if schema file exists
        if os.path.exists(schema_file):
            with open(schema_file, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
        conn.commit()

# Ensure database is initialized at import
init_db()

def df_query(sql: str, params: Tuple = ()) -> pd.DataFrame:
    """Executes a SQL query and returns results as a pandas DataFrame."""
    conn = get_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

def exec_sql(sql: str, params: Tuple = ()) -> int:
    """Executes an INSERT/UPDATE/DELETE query and returns the last inserted row ID."""
    conn = get_conn()
    try:
        with conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid
    finally:
        conn.close()

def fetch_one(sql: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
    """Fetches a single row from the database."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone()
    finally:
        conn.close()

def fetch_all(sql: str, params: Tuple = ()) -> List[sqlite3.Row]:
    """Fetches all rows matching the query."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

# ------------------------------------------------------------------------------
# SYNC QUEUE OPERATIONS
# ------------------------------------------------------------------------------
def queue_sync(table_name: str, record_id: int, operation: str = "UPSERT", payload: Optional[Dict[str, Any]] = None) -> int:
    """
    Appends an operation to the sync queue for Google Sheets synchronization.
    Saves an optional JSON snapshot for DELETE or AUDIT purposes.
    """
    # Normalize operation to maintain compatibility with existing CHECK constraints
    op = "DELETE" if operation.upper() == "DELETE" else "UPSERT"
    payload_json = json.dumps(payload) if payload else None
    qid = exec_sql(
        """INSERT INTO sync_queue(table_name, record_id, operation, payload_snapshot, synced, error)
           VALUES(?, ?, ?, ?, 0, NULL)""",
        (table_name, record_id, op, payload_json)
    )
    
    # Check if automatic sync on change is enabled
    cfg = fetch_one("SELECT config_value FROM sync_config WHERE config_key='auto_sync_enabled'")
    auto_sync = (cfg["config_value"] == "1") if cfg else True
    
    if auto_sync:
        try:
            # Import dynamically to avoid circular dependencies
            import sync_engine
            sync_engine.process_sync_queue(max_items=10)
        except Exception:
            # Sync failure won't rollback DB transaction, queue record remains unsynced for retry
            pass
            
    return qid

# ------------------------------------------------------------------------------
# ACADEMIC CALCULATION HELPERS (SGPA / CGPA / GRADES)
# ------------------------------------------------------------------------------
def calculate_grade_and_point(total_pct: float) -> Tuple[str, float]:
    """Standard 10-point absolute university grading scale."""
    if total_pct >= 90.0:
        return ("O", 10.0)
    elif total_pct >= 80.0:
        return ("A+", 9.0)
    elif total_pct >= 70.0:
        return ("A", 8.0)
    elif total_pct >= 60.0:
        return ("B+", 7.0)
    elif total_pct >= 55.0:
        return ("B", 6.0)
    elif total_pct >= 50.0:
        return ("C", 5.0)
    elif total_pct >= 40.0:
        return ("P", 4.0)
    else:
        return ("F", 0.0)

def auto_compute_semester_sgpa(semester_id: int) -> Optional[float]:
    """
    Computes SGPA using the standard credit-weighted formula:
    SGPA = Sum(credits * grade_point) / Sum(credits)
    Updates the semesters table and returns the calculated SGPA.
    """
    results = fetch_all(
        "SELECT credits, grade_point FROM semester_results WHERE semester_id=? AND grade_point IS NOT NULL",
        (semester_id,)
    )
    if not results:
        return None
        
    total_credit_points = sum(r["credits"] * r["grade_point"] for r in results)
    total_credits = sum(r["credits"] for r in results)
    
    if total_credits == 0:
        return 0.0
        
    sgpa = round(total_credit_points / total_credits, 2)
    exec_sql("UPDATE semesters SET sgpa=? WHERE semester_id=?", (sgpa, semester_id))
    queue_sync("semesters", semester_id, "UPDATE")
    return sgpa

def auto_compute_student_cgpa(student_id: int) -> Optional[float]:
    """
    Computes cumulative CGPA across all completed semesters for a student.
    CGPA = Sum(Semester SGPA * Semester Total Credits) / Sum(Semester Total Credits)
    (or unweighted mean of SGPAs if credit totals are uniform).
    """
    sems = fetch_all(
        "SELECT semester_id, sgpa FROM semesters WHERE student_id=? AND status='Completed'",
        (student_id,)
    )
    if not sems:
        return None
        
    total_sgpa = sum(s["sgpa"] for s in sems)
    cgpa = round(total_sgpa / len(sems), 2)
    # Update latest semester cgpa
    latest_sem = max(s["semester_id"] for s in sems)
    exec_sql("UPDATE semesters SET cgpa=? WHERE semester_id=?", (cgpa, latest_sem))
    return cgpa

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: STUDENTS
# ------------------------------------------------------------------------------
def get_all_students() -> pd.DataFrame:
    return df_query("SELECT * FROM students ORDER BY roll_no")

def add_student(roll_no: str, full_name: str, email: Optional[str], phone: Optional[str],
                department: str, admission_year: int, current_status: str) -> int:
    sid = exec_sql(
        """INSERT INTO students(roll_no, full_name, email, phone, department, admission_year, current_status)
           VALUES(?, ?, ?, ?, ?, ?, ?)""",
        (roll_no.strip(), full_name.strip(), email.strip() if email else None,
         phone.strip() if phone else None, department.strip(), int(admission_year), current_status)
    )
    queue_sync("students", sid, "INSERT")
    return sid

def update_student(student_id: int, roll_no: str, full_name: str, email: Optional[str],
                   phone: Optional[str], department: str, admission_year: int, current_status: str) -> None:
    exec_sql(
        """UPDATE students
           SET roll_no=?, full_name=?, email=?, phone=?, department=?, admission_year=?, current_status=?
           WHERE student_id=?""",
        (roll_no.strip(), full_name.strip(), email.strip() if email else None,
         phone.strip() if phone else None, department.strip(), int(admission_year), current_status, student_id)
    )
    queue_sync("students", student_id, "UPDATE")

def delete_student(student_id: int) -> Dict[str, Any]:
    row = fetch_one("SELECT * FROM students WHERE student_id=?", (student_id,))
    snapshot = dict(row) if row else {"student_id": student_id}
    exec_sql("DELETE FROM students WHERE student_id=?", (student_id,))
    queue_sync("students", student_id, "DELETE", payload=snapshot)
    return snapshot

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: SCHOOL RECORDS
# ------------------------------------------------------------------------------
def save_school_record(student_id: int, level: str, board: str, passing_year: int,
                       percentage: float, institution_name: Optional[str] = None) -> int:
    rid = exec_sql(
        """INSERT INTO school_records(student_id, level, board, passing_year, percentage, institution_name)
           VALUES(?, ?, ?, ?, ?, ?)
           ON CONFLICT(student_id, level) DO UPDATE SET
               board=excluded.board,
               passing_year=excluded.passing_year,
               percentage=excluded.percentage,
               institution_name=excluded.institution_name""",
        (student_id, level, board.strip(), int(passing_year), float(percentage), institution_name.strip() if institution_name else None)
    )
    actual_id = fetch_one("SELECT record_id FROM school_records WHERE student_id=? AND level=?", (student_id, level))["record_id"]
    queue_sync("school_records", actual_id, "UPSERT")
    return actual_id

def delete_school_record(record_id: int) -> None:
    row = fetch_one("SELECT * FROM school_records WHERE record_id=?", (record_id,))
    snapshot = dict(row) if row else {"record_id": record_id}
    exec_sql("DELETE FROM school_records WHERE record_id=?", (record_id,))
    queue_sync("school_records", record_id, "DELETE", payload=snapshot)

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: SEMESTERS
# ------------------------------------------------------------------------------
def save_semester(student_id: int, semester_no: int, academic_year: str,
                  sgpa: float, cgpa: Optional[float] = None, status: str = "Completed") -> int:
    exec_sql(
        """INSERT INTO semesters(student_id, semester_no, academic_year, sgpa, cgpa, status)
           VALUES(?, ?, ?, ?, ?, ?)
           ON CONFLICT(student_id, semester_no) DO UPDATE SET
               academic_year=excluded.academic_year,
               sgpa=excluded.sgpa,
               cgpa=excluded.cgpa,
               status=excluded.status""",
        (student_id, int(semester_no), academic_year.strip(), float(sgpa), float(cgpa) if cgpa is not None else None, status)
    )
    actual_id = fetch_one("SELECT semester_id FROM semesters WHERE student_id=? AND semester_no=?", (student_id, int(semester_no)))["semester_id"]
    queue_sync("semesters", actual_id, "UPSERT")
    return actual_id

def delete_semester(semester_id: int) -> None:
    row = fetch_one("SELECT * FROM semesters WHERE semester_id=?", (semester_id,))
    snapshot = dict(row) if row else {"semester_id": semester_id}
    exec_sql("DELETE FROM semesters WHERE semester_id=?", (semester_id,))
    queue_sync("semesters", semester_id, "DELETE", payload=snapshot)

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: SUBJECTS CATALOG
# ------------------------------------------------------------------------------
def save_subject(subject_code: str, subject_name: str, subject_type: str,
                 credits: float = 3.0, department: str = "Computer Science & Engineering",
                 max_theory: float = 100.0, max_lab: float = 100.0) -> int:
    exec_sql(
        """INSERT INTO subjects(subject_code, subject_name, subject_type, credits, department, max_theory_marks, max_lab_marks)
           VALUES(?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(subject_code) DO UPDATE SET
               subject_name=excluded.subject_name,
               subject_type=excluded.subject_type,
               credits=excluded.credits,
               department=excluded.department,
               max_theory_marks=excluded.max_theory_marks,
               max_lab_marks=excluded.max_lab_marks""",
        (subject_code.strip().upper(), subject_name.strip(), subject_type, float(credits), department.strip(), float(max_theory), float(max_lab))
    )
    sub = fetch_one("SELECT subject_id FROM subjects WHERE subject_code=?", (subject_code.strip().upper(),))
    sub_id = sub["subject_id"]
    queue_sync("subjects", sub_id, "UPSERT")
    return sub_id

def delete_subject(subject_id: int) -> Tuple[bool, str]:
    # Check foreign key reference in semester_results
    count = fetch_one("SELECT COUNT(*) AS c FROM semester_results WHERE subject_id=?", (subject_id,))["c"]
    if count > 0:
        return False, f"Cannot delete subject: referenced by {count} student semester result(s) (ON DELETE RESTRICT)."
    row = fetch_one("SELECT * FROM subjects WHERE subject_id=?", (subject_id,))
    snapshot = dict(row) if row else {"subject_id": subject_id}
    exec_sql("DELETE FROM subjects WHERE subject_id=?", (subject_id,))
    queue_sync("subjects", subject_id, "DELETE", payload=snapshot)
    return True, "Subject deleted successfully."

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: SEMESTER RESULTS (THEORY & LAB MARKS)
# ------------------------------------------------------------------------------
def save_semester_result(semester_id: int, subject_id: int,
                         theory_marks: Optional[float] = None,
                         lab_marks: Optional[float] = None,
                         credits: float = 3.0,
                         grade: Optional[str] = None,
                         attendance_pct: Optional[float] = None) -> int:
    """
    Stores subject result with individual theory marks, lab marks,
    computed total marks, and automatic grade assignment.
    """
    # Fetch subject details for validation
    subj = fetch_one("SELECT * FROM subjects WHERE subject_id=?", (subject_id,))
    stype = subj["subject_type"] if subj else "Theory"
    
    t_m = float(theory_marks) if theory_marks is not None and stype in ("Theory", "Theory+Lab") else None
    l_m = float(lab_marks) if lab_marks is not None and stype in ("Lab", "Theory+Lab") else None
    
    # Calculate total and percentage
    t_val = t_m or 0.0
    l_val = l_m or 0.0
    max_t = subj["max_theory_marks"] if subj and stype in ("Theory", "Theory+Lab") else 0.0
    max_l = subj["max_lab_marks"] if subj and stype in ("Lab", "Theory+Lab") else 0.0
    total_max = (max_t if max_t > 0 else 100.0) if stype == "Theory" else (
                (max_l if max_l > 0 else 100.0) if stype == "Lab" else (max_t + max_l)
    )
    if total_max <= 0:
        total_max = 100.0
        
    total_m = (t_val if t_m is not None else 0.0) + (l_val if l_m is not None else 0.0)
    pct = (total_m / total_max) * 100.0
    
    auto_g, auto_gp = calculate_grade_and_point(pct)
    final_grade = grade.strip() if grade else auto_g
    final_gp = auto_gp
    
    exec_sql(
        """INSERT INTO semester_results(semester_id, subject_id, theory_marks, lab_marks, total_marks, credits, grade_point, grade, attendance_percentage)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(semester_id, subject_id) DO UPDATE SET
               theory_marks=excluded.theory_marks,
               lab_marks=excluded.lab_marks,
               total_marks=excluded.total_marks,
               credits=excluded.credits,
               grade_point=excluded.grade_point,
               grade=excluded.grade,
               attendance_percentage=excluded.attendance_percentage""",
        (semester_id, subject_id, t_m, l_m, total_m, float(credits), final_gp, final_grade, float(attendance_pct) if attendance_pct is not None else None)
    )
    
    res = fetch_one("SELECT result_id FROM semester_results WHERE semester_id=? AND subject_id=?", (semester_id, subject_id))
    rid = res["result_id"]
    queue_sync("semester_results", rid, "UPSERT")
    
    # Recalculate semester SGPA automatically
    auto_compute_semester_sgpa(semester_id)
    return rid

def delete_semester_result(result_id: int) -> None:
    row = fetch_one("SELECT * FROM semester_results WHERE result_id=?", (result_id,))
    snapshot = dict(row) if row else {"result_id": result_id}
    sem_id = row["semester_id"] if row else None
    exec_sql("DELETE FROM semester_results WHERE result_id=?", (result_id,))
    queue_sync("semester_results", result_id, "DELETE", payload=snapshot)
    if sem_id:
        auto_compute_semester_sgpa(sem_id)

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: DROP YEARS
# ------------------------------------------------------------------------------
def save_drop_year(student_id: int, start_year: int, end_year: int,
                   reason: Optional[str] = None, approved_by: Optional[str] = None) -> int:
    existing = fetch_one("SELECT drop_id FROM drop_years WHERE student_id=? AND start_year=?", (student_id, int(start_year)))
    r_text = reason.strip() if reason else None
    a_text = approved_by.strip() if approved_by else None
    if existing:
        actual_id = existing["drop_id"]
        exec_sql(
            "UPDATE drop_years SET end_year=?, reason=?, approved_by=? WHERE drop_id=?",
            (int(end_year), r_text, a_text, actual_id)
        )
    else:
        actual_id = exec_sql(
            """INSERT INTO drop_years(student_id, start_year, end_year, reason, approved_by)
               VALUES(?, ?, ?, ?, ?)""",
            (student_id, int(start_year), int(end_year), r_text, a_text)
        )
    queue_sync("drop_years", actual_id, "UPSERT")
    return actual_id

def delete_drop_year(drop_id: int) -> None:
    row = fetch_one("SELECT * FROM drop_years WHERE drop_id=?", (drop_id,))
    snapshot = dict(row) if row else {"drop_id": drop_id}
    exec_sql("DELETE FROM drop_years WHERE drop_id=?", (drop_id,))
    queue_sync("drop_years", drop_id, "DELETE", payload=snapshot)

# ------------------------------------------------------------------------------
# CRUD OPERATIONS: ACHIEVEMENTS & PORTFOLIO
# ------------------------------------------------------------------------------
def save_achievement(student_id: int, category_id: int, title: str,
                     organizer: Optional[str] = None, event_scope: Optional[str] = None,
                     activity_type: Optional[str] = None, achievement_date: Optional[str] = None,
                     description: Optional[str] = None, award_level: Optional[str] = None,
                     achievement_id: Optional[int] = None) -> int:
    # Normalize event_scope to match SQLite CHECK constraint ('Internal', 'External')
    clean_scope = None
    if event_scope and event_scope not in ("Not a seminar", "None", ""):
        clean_scope = "Internal" if "internal" in str(event_scope).lower() else "External"

    # Normalize activity_type to ('Technical','Co-curricular','Extra-curricular','Seminar')
    valid_types = ("Technical", "Co-curricular", "Extra-curricular", "Seminar")
    clean_type = activity_type if activity_type in valid_types else "Technical"

    if achievement_id:
        exec_sql(
            """UPDATE achievements
               SET student_id=?, category_id=?, title=?, organizer=?, event_scope=?,
                   activity_type=?, achievement_date=?, description=?, award_level=?
               WHERE achievement_id=?""",
            (student_id, category_id, title.strip(), organizer.strip() if organizer else None,
             clean_scope, clean_type, achievement_date, description.strip() if description else None,
             award_level.strip() if award_level else None, achievement_id)
        )
        queue_sync("achievements", achievement_id, "UPDATE")
        return achievement_id
    else:
        aid = exec_sql(
            """INSERT INTO achievements(student_id, category_id, title, organizer, event_scope,
                                      activity_type, achievement_date, description, award_level)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, category_id, title.strip(), organizer.strip() if organizer else None,
             clean_scope, clean_type, achievement_date, description.strip() if description else None,
             award_level.strip() if award_level else None)
        )
        queue_sync("achievements", aid, "INSERT")
        return aid

def delete_achievement(achievement_id: int) -> None:
    row = fetch_one("SELECT * FROM achievements WHERE achievement_id=?", (achievement_id,))
    snapshot = dict(row) if row else {"achievement_id": achievement_id}
    exec_sql("DELETE FROM achievements WHERE achievement_id=?", (achievement_id,))
    queue_sync("achievements", achievement_id, "DELETE", payload=snapshot)

# ------------------------------------------------------------------------------
# SAMPLE DATA SEEDER
# ------------------------------------------------------------------------------
def seed_sample_data(clear_existing: bool = False) -> Dict[str, int]:
    """
    Populates comprehensive, realistic sample data for demo and viva evaluation.
    Includes multiple semesters, complete theory & lab marks, achievements,
    and distinct students with and without drop years.
    """
    if clear_existing:
        with get_conn() as conn:
            conn.execute("DELETE FROM achievements;")
            conn.execute("DELETE FROM drop_years;")
            conn.execute("DELETE FROM semester_results;")
            conn.execute("DELETE FROM semesters;")
            conn.execute("DELETE FROM subjects;")
            conn.execute("DELETE FROM school_records;")
            conn.execute("DELETE FROM students;")
            conn.execute("DELETE FROM sync_queue;")
            conn.commit()

    # 1. Subjects catalog
    subjects_data = [
        ("CS101", "Programming in C", "Theory+Lab", 4.0, 100.0, 50.0),
        ("MA101", "Engineering Mathematics I", "Theory", 4.0, 100.0, 0.0),
        ("PH101", "Engineering Physics", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS201", "Data Structures & Applications", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS202", "Digital Electronics & Logic Design", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS301", "Database Management Systems", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS302", "Design & Analysis of Algorithms", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS303", "Operating Systems", "Theory", 3.0, 100.0, 0.0),
        ("CS304", "Object Oriented Programming (Java)", "Theory+Lab", 3.0, 50.0, 50.0),
        ("CS401", "Computer Networks", "Theory+Lab", 4.0, 100.0, 50.0),
        ("CS402", "Software Engineering", "Theory", 3.0, 100.0, 0.0),
        ("CS403", "Web Technologies & Frameworks", "Theory+Lab", 4.0, 50.0, 50.0),
    ]
    sub_map = {}
    for code, name, stype, creds, mt, ml in subjects_data:
        sub_id = save_subject(code, name, stype, creds, "Computer Science & Engineering", mt, ml)
        sub_map[code] = sub_id

    # 2. Students data
    students_data = [
        ("21CS001", "Aarav Sharma", "aarav.sharma@college.edu", "9876543210", "Computer Science & Engineering", 2021, "Active"),
        ("21CS015", "Priya Nair", "priya.nair@college.edu", "9876543211", "Computer Science & Engineering", 2021, "Active"),
        ("21CS042", "Rohan Verma", "rohan.verma@college.edu", "9876543212", "Computer Science & Engineering", 2021, "Active"),
        ("22CS008", "Ananya Iyer", "ananya.iyer@college.edu", "9876543213", "Computer Science & Engineering", 2022, "Active"),
        ("22CS025", "Vikram Patel", "vikram.patel@college.edu", "9876543214", "Computer Science & Engineering", 2022, "Active"),
    ]
    student_map = {}
    for rno, name, email, phone, dept, y, status in students_data:
        existing = fetch_one("SELECT student_id FROM students WHERE roll_no=?", (rno,))
        if existing:
            sid = existing["student_id"]
        else:
            sid = add_student(rno, name, email, phone, dept, y, status)
        student_map[rno] = sid

    # 3. School records
    school_data = [
        ("21CS001", "10th", "CBSE", 2019, 94.5, "Delhi Public School"),
        ("21CS001", "12th", "CBSE", 2021, 92.0, "Delhi Public School"),
        ("21CS015", "10th", "ICSE", 2019, 91.0, "Bishop Cotton High School"),
        ("21CS015", "12th", "State Board", 2021, 88.5, "National College"),
        ("21CS042", "10th", "State Board", 2019, 85.0, "St. Aloysius School"),
        ("21CS042", "12th", "State Board", 2021, 79.5, "St. Aloysius PU College"),
        ("22CS008", "10th", "CBSE", 2020, 96.0, "Kendriya Vidyalaya"),
        ("22CS008", "12th", "CBSE", 2022, 95.2, "Kendriya Vidyalaya"),
        ("22CS025", "10th", "State Board", 2020, 82.0, "Government High School"),
        ("22CS025", "12th", "DTE Technical Board", 2022, 86.4, "Government Polytechnic"),
    ]
    for rno, lvl, brd, yr, pct, inst in school_data:
        save_school_record(student_map[rno], lvl, brd, yr, pct, inst)

    # 4. Semesters & Theory/Lab Marks
    # Aarav Sharma (21CS001) - 6 Semesters progression
    aarav_id = student_map["21CS001"]
    s1 = save_semester(aarav_id, 1, "2021-22", 8.8, 8.8, "Completed")
    save_semester_result(s1, sub_map["CS101"], theory_marks=88, lab_marks=45, credits=4.0)
    save_semester_result(s1, sub_map["MA101"], theory_marks=92, lab_marks=None, credits=4.0)
    save_semester_result(s1, sub_map["PH101"], theory_marks=84, lab_marks=46, credits=4.0)

    s2 = save_semester(aarav_id, 2, "2021-22", 9.1, 8.95, "Completed")
    save_semester_result(s2, sub_map["CS201"], theory_marks=92, lab_marks=48, credits=4.0)
    save_semester_result(s2, sub_map["CS202"], theory_marks=86, lab_marks=45, credits=4.0)

    s3 = save_semester(aarav_id, 3, "2022-23", 9.3, 9.07, "Completed")
    save_semester_result(s3, sub_map["CS301"], theory_marks=94, lab_marks=49, credits=4.0)
    save_semester_result(s3, sub_map["CS302"], theory_marks=89, lab_marks=47, credits=4.0)
    save_semester_result(s3, sub_map["CS303"], theory_marks=90, lab_marks=None, credits=3.0)

    s4 = save_semester(aarav_id, 4, "2022-23", 9.4, 9.15, "Completed")
    save_semester_result(s4, sub_map["CS401"], theory_marks=91, lab_marks=48, credits=4.0)
    save_semester_result(s4, sub_map["CS402"], theory_marks=88, lab_marks=None, credits=3.0)
    save_semester_result(s4, sub_map["CS403"], theory_marks=48, lab_marks=49, credits=4.0)

    s5 = save_semester(aarav_id, 5, "2023-24", 9.5, 9.22, "Completed")
    s6 = save_semester(aarav_id, 6, "2023-24", 9.6, 9.28, "Completed")

    # Rohan Verma (21CS042) - Has a drop year between 2023 and 2024!
    rohan_id = student_map["21CS042"]
    r1 = save_semester(rohan_id, 1, "2021-22", 7.6, 7.6, "Completed")
    save_semester_result(r1, sub_map["CS101"], theory_marks=74, lab_marks=38, credits=4.0)
    save_semester_result(r1, sub_map["MA101"], theory_marks=70, lab_marks=None, credits=4.0)

    r2 = save_semester(rohan_id, 2, "2021-22", 7.4, 7.5, "Completed")
    save_semester_result(r2, sub_map["CS201"], theory_marks=72, lab_marks=39, credits=4.0)

    r3 = save_semester(rohan_id, 3, "2022-23", 7.2, 7.4, "Completed")
    save_semester_result(r3, sub_map["CS301"], theory_marks=68, lab_marks=40, credits=4.0)

    # Recorded drop year for Rohan Verma:
    save_drop_year(rohan_id, 2023, 2024, "Medical leave due to orthopedic surgery & rehabilitation", "Dean of Academic Affairs")

    # Rohan resumes in 2024-25 for semester 4
    r4 = save_semester(rohan_id, 4, "2024-25", 8.2, 7.6, "Completed")
    save_semester_result(r4, sub_map["CS401"], theory_marks=80, lab_marks=44, credits=4.0)

    # Ananya Iyer (22CS008) - High performer
    ananya_id = student_map["22CS008"]
    a1 = save_semester(ananya_id, 1, "2022-23", 9.5, 9.5, "Completed")
    save_semester_result(a1, sub_map["CS101"], theory_marks=95, lab_marks=49, credits=4.0)
    save_semester_result(a1, sub_map["MA101"], theory_marks=98, lab_marks=None, credits=4.0)

    a2 = save_semester(ananya_id, 2, "2022-23", 9.6, 9.55, "Completed")
    save_semester_result(a2, sub_map["CS201"], theory_marks=94, lab_marks=49, credits=4.0)

    a3 = save_semester(ananya_id, 3, "2023-24", 9.7, 9.6, "Completed")
    save_semester_result(a3, sub_map["CS301"], theory_marks=96, lab_marks=50, credits=4.0)

    # 5. Portfolio & Achievements
    cats = {r["category_name"]: r["category_id"] for r in fetch_all("SELECT * FROM achievement_categories")}
    c_tech = cats.get("Technical") or list(cats.values())[0]
    c_sem = cats.get("Seminar") or list(cats.values())[0]
    c_extra = cats.get("Extra-curricular") or list(cats.values())[0]

    save_achievement(aarav_id, c_tech, "1st Place - Smart India Hackathon 2023", "Ministry of Education / AICTE", "External", "Technical", "2023-09-22", "Built automated disaster coordination mobile portal.", "1st Prize")
    save_achievement(aarav_id, c_sem, "Keynote: Scalable Microservices Architecture", "Dept of Computer Science", "Internal", "Seminar", "2023-11-15", "Delivered 2-hour technical seminar to 3rd year juniors.", "Speaker")
    save_achievement(ananya_id, c_tech, "Research Paper: Optimizing DBMS B+ Trees for SSDs", "IEEE International Conference", "External", "Technical", "2024-02-18", "Presented peer-reviewed research paper on indexing performance.", "Best Student Paper")
    save_achievement(ananya_id, c_tech, "Winner - Algorithmic Coding Championship", "Google Developer Student Club", "External", "Technical", "2023-10-05", "Solved 6 algorithmic challenges in 2 hours.", "Winner")
    save_achievement(student_map["21CS015"], c_extra, "Gold Medalist - Inter-University Badminton", "State Sports Authority", "External", "Extra-curricular", "2023-12-10", "Represented college women's badminton team.", "Gold Medal")

    counts = {
        "students": fetch_one("SELECT COUNT(*) c FROM students")["c"],
        "school_records": fetch_one("SELECT COUNT(*) c FROM school_records")["c"],
        "semesters": fetch_one("SELECT COUNT(*) c FROM semesters")["c"],
        "subjects": fetch_one("SELECT COUNT(*) c FROM subjects")["c"],
        "semester_results": fetch_one("SELECT COUNT(*) c FROM semester_results")["c"],
        "drop_years": fetch_one("SELECT COUNT(*) c FROM drop_years")["c"],
        "achievements": fetch_one("SELECT COUNT(*) c FROM achievements")["c"],
    }
    return counts
