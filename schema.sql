-- ==============================================================================
-- Student Academic Progression & Portfolio Management System
-- Relational Database Schema (Normalized to 3NF / BCNF)
-- DBMS Mini-Project
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. STUDENTS TABLE
-- Entity representing enrolled undergraduate/postgraduate students.
-- Primary Key: student_id
-- Candidate Key: roll_no (Unique institutional registration number)
-- 3NF: Every non-key attribute is directly and functionally dependent on student_id.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT NOT NULL UNIQUE CHECK(length(trim(roll_no)) >= 3),
    full_name TEXT NOT NULL CHECK(length(trim(full_name)) >= 2),
    email TEXT UNIQUE CHECK(email IS NULL OR (length(email) >= 5 AND email LIKE '%@%.%')),
    phone TEXT CHECK(phone IS NULL OR length(trim(phone)) BETWEEN 7 AND 15),
    department TEXT NOT NULL DEFAULT 'Computer Science & Engineering' CHECK(length(trim(department)) >= 2),
    admission_year INTEGER NOT NULL CHECK(admission_year BETWEEN 1990 AND 2100),
    current_status TEXT NOT NULL DEFAULT 'Active'
        CHECK(current_status IN ('Active', 'Graduated', 'On Hold', 'Discontinued'))
);

CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_no);
CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department);

-- ------------------------------------------------------------------------------
-- 2. SCHOOL RECORDS TABLE
-- Entity storing prior secondary (10th) and higher-secondary/diploma (12th) qualifications.
-- Primary Key: record_id
-- Candidate Key: (student_id, level)
-- 3NF: No transitive dependency. Board, year, and percentage depend on (student_id, level).
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK(level IN ('10th', '12th', 'Diploma')),
    board TEXT NOT NULL CHECK(length(trim(board)) >= 2),
    passing_year INTEGER NOT NULL CHECK(passing_year BETWEEN 1990 AND 2100),
    percentage REAL NOT NULL CHECK(percentage BETWEEN 0.0 AND 100.0),
    institution_name TEXT,
    UNIQUE(student_id, level)
);

CREATE INDEX IF NOT EXISTS idx_school_student ON school_records(student_id);

-- ------------------------------------------------------------------------------
-- 3. SEMESTERS TABLE
-- Entity storing academic term progression milestones and performance indices.
-- Primary Key: semester_id
-- Candidate Key: (student_id, semester_no)
-- 3NF: Academic term details and overall SGPA/CGPA depend directly on (student_id, semester_no).
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semesters (
    semester_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    semester_no INTEGER NOT NULL CHECK(semester_no BETWEEN 1 AND 12),
    academic_year TEXT NOT NULL CHECK(length(trim(academic_year)) >= 4),
    sgpa REAL NOT NULL CHECK(sgpa BETWEEN 0.0 AND 10.0),
    cgpa REAL CHECK(cgpa IS NULL OR (cgpa BETWEEN 0.0 AND 10.0)),
    status TEXT NOT NULL DEFAULT 'Completed'
        CHECK(status IN ('Completed', 'In Progress', 'Gap')),
    UNIQUE(student_id, semester_no)
);

CREATE INDEX IF NOT EXISTS idx_semesters_student ON semesters(student_id);

-- ------------------------------------------------------------------------------
-- 4. SUBJECTS TABLE (MASTER CATALOG)
-- Reference catalog of courses to eliminate redundancy in semester marks.
-- Primary Key: subject_id
-- Candidate Key: subject_code
-- 3NF: Course name, type, and credits depend solely on subject_id. Separated from
-- student semester attempts to prevent insertion, update, and deletion anomalies.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code TEXT NOT NULL UNIQUE CHECK(length(trim(subject_code)) >= 2),
    subject_name TEXT NOT NULL CHECK(length(trim(subject_name)) >= 2),
    subject_type TEXT NOT NULL CHECK(subject_type IN ('Theory', 'Lab', 'Theory+Lab')),
    credits REAL NOT NULL DEFAULT 3.0 CHECK(credits > 0.0 AND credits <= 10.0),
    department TEXT DEFAULT 'Computer Science & Engineering',
    max_theory_marks REAL NOT NULL DEFAULT 100.0 CHECK(max_theory_marks >= 0.0 AND max_theory_marks <= 100.0),
    max_lab_marks REAL NOT NULL DEFAULT 100.0 CHECK(max_lab_marks >= 0.0 AND max_lab_marks <= 100.0)
);

CREATE INDEX IF NOT EXISTS idx_subjects_code ON subjects(subject_code);

-- ------------------------------------------------------------------------------
-- 5. SEMESTER RESULTS TABLE
-- Intersection entity capturing student performance in each course per semester.
-- Allows storage of both semester theory and laboratory marks separately.
-- Primary Key: result_id
-- Candidate Key: (semester_id, subject_id)
-- 3NF: Marks, grade point, and grade depend on the student semester and specific subject.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semester_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_id INTEGER NOT NULL REFERENCES semesters(semester_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    theory_marks REAL CHECK(theory_marks IS NULL OR (theory_marks BETWEEN 0.0 AND 100.0)),
    lab_marks REAL CHECK(lab_marks IS NULL OR (lab_marks BETWEEN 0.0 AND 100.0)),
    total_marks REAL CHECK(total_marks IS NULL OR (total_marks BETWEEN 0.0 AND 200.0)),
    credits REAL NOT NULL DEFAULT 3.0 CHECK(credits >= 0.0 AND credits <= 10.0),
    grade_point REAL CHECK(grade_point IS NULL OR (grade_point BETWEEN 0.0 AND 10.0)),
    grade TEXT CHECK(grade IS NULL OR grade IN ('O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'Ab')),
    attendance_percentage REAL CHECK(attendance_percentage IS NULL OR (attendance_percentage BETWEEN 0.0 AND 100.0)),
    UNIQUE(semester_id, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_results_semester ON semester_results(semester_id);
CREATE INDEX IF NOT EXISTS idx_results_subject ON semester_results(subject_id);

-- ------------------------------------------------------------------------------
-- 6. DROP YEARS TABLE
-- Entity recording official academic gap / drop years with reasons.
-- Primary Key: drop_id
-- Candidate Key: (student_id, start_year)
-- Constraint: start_year <= end_year to prevent invalid time spans.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drop_years (
    drop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    start_year INTEGER NOT NULL CHECK(start_year BETWEEN 1990 AND 2100),
    end_year INTEGER NOT NULL CHECK(end_year >= start_year AND end_year <= 2100),
    reason TEXT,
    approved_by TEXT,
    UNIQUE(student_id, start_year)
);

CREATE INDEX IF NOT EXISTS idx_drop_student ON drop_years(student_id);

-- ------------------------------------------------------------------------------
-- 7. ACHIEVEMENT CATEGORIES TABLE (MASTER CATALOG)
-- Reference catalog of portfolio categories to maintain 3NF.
-- Primary Key: category_id
-- Candidate Key: category_name
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievement_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE CHECK(length(trim(category_name)) >= 2),
    description TEXT
);

-- Seed core categories
INSERT OR IGNORE INTO achievement_categories(category_name, description) VALUES
    ('Seminar', 'Technical and academic seminars or presentations'),
    ('Technical', 'Coding competitions, hackathons, and technical symposiums'),
    ('Co-curricular', 'Workshops, industrial visits, and professional memberships'),
    ('Extra-curricular', 'Sports, cultural events, debate, and community service'),
    ('Publication', 'Research papers, articles, and journal publications'),
    ('Certification', 'Industry and online certifications (NPTEL, Coursera, AWS, etc.)');

-- ------------------------------------------------------------------------------
-- 8. ACHIEVEMENTS TABLE
-- Portfolio items and extracurricular milestones per student.
-- Primary Key: achievement_id
-- Foreign Keys: student_id -> students, category_id -> achievement_categories
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES achievement_categories(category_id) ON DELETE RESTRICT,
    title TEXT NOT NULL CHECK(length(trim(title)) >= 2),
    organizer TEXT,
    event_scope TEXT CHECK(event_scope IS NULL OR event_scope IN ('Internal', 'External', 'State', 'National', 'International')),
    activity_type TEXT CHECK(activity_type IS NULL OR activity_type IN ('Technical', 'Co-curricular', 'Extra-curricular', 'Seminar', 'Workshop', 'Hackathon', 'Publication', 'Certification')),
    achievement_date TEXT,
    description TEXT,
    award_level TEXT
);

CREATE INDEX IF NOT EXISTS idx_achievements_student ON achievements(student_id);
CREATE INDEX IF NOT EXISTS idx_achievements_cat ON achievements(category_id);

-- ------------------------------------------------------------------------------
-- 9. SYNC QUEUE TABLE
-- Event queue capturing every insert, update, or delete for reliable Google Sheets sync.
-- Primary Key: queue_id
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('INSERT', 'UPDATE', 'DELETE', 'UPSERT')),
    payload_snapshot TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced INTEGER NOT NULL DEFAULT 0 CHECK(synced IN (0, 1)),
    synced_at TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced);

-- ------------------------------------------------------------------------------
-- 10. SYNC CONFIG TABLE
-- Persists synchronization preferences and audit metadata.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO sync_config(config_key, config_value) VALUES
    ('auto_sync_enabled', '1'),
    ('sync_mode', 'queue_driven'),
    ('last_full_sync', NULL);
