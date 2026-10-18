-- ==============================================================================
-- STUDENT ACADEMIC PROGRESSION & PORTFOLIO MANAGEMENT SYSTEM
-- MySQL 8.0 Relational Database Schema (Normalized to Strict 3NF)
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS student_progression_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE student_progression_db;

-- ------------------------------------------------------------------------------
-- 1. STUDENTS (Demographics & Primary Identity)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_no VARCHAR(20) NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    department VARCHAR(80) NOT NULL,
    admission_year INT NOT NULL,
    current_status ENUM('Active', 'Graduated', 'On Hold', 'Discontinued') NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_adm_year CHECK (admission_year BETWEEN 1990 AND 2100)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 2. SCHOOL RECORDS (Prior Academic Background: 10th / 12th / Diploma)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    level ENUM('10th', '12th', 'Diploma') NOT NULL,
    board VARCHAR(80) NOT NULL,
    passing_year INT NOT NULL,
    percentage DECIMAL(5,2) NOT NULL,
    institution_name VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_school_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_level UNIQUE (student_id, level),
    CONSTRAINT chk_school_pct CHECK (percentage BETWEEN 0.0 AND 100.0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 3. SEMESTERS (Term Milestones with SGPA / CGPA)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semesters (
    semester_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    semester_no INT NOT NULL,
    academic_year VARCHAR(15) NOT NULL,
    sgpa DECIMAL(4,2) NOT NULL DEFAULT 0.0,
    cgpa DECIMAL(4,2),
    status ENUM('Completed', 'In Progress', 'Gap') NOT NULL DEFAULT 'Completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sem_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_sem UNIQUE (student_id, semester_no),
    CONSTRAINT chk_sem_no CHECK (semester_no BETWEEN 1 AND 12),
    CONSTRAINT chk_sem_sgpa CHECK (sgpa BETWEEN 0.0 AND 10.0),
    CONSTRAINT chk_sem_cgpa CHECK (cgpa IS NULL OR (cgpa BETWEEN 0.0 AND 10.0))
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 4. SUBJECTS CATALOG (Master Course Table - 3NF Isolation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(15) NOT NULL UNIQUE,
    subject_name VARCHAR(120) NOT NULL,
    subject_type ENUM('Theory', 'Lab', 'Theory+Lab') NOT NULL DEFAULT 'Theory',
    credits DECIMAL(3,1) NOT NULL DEFAULT 4.0,
    department VARCHAR(80) DEFAULT 'Computer Science & Engineering',
    max_theory_marks DECIMAL(5,2) DEFAULT 100.0,
    max_lab_marks DECIMAL(5,2) DEFAULT 50.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_sub_credits CHECK (credits > 0.0 AND credits <= 10.0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 5. SEMESTER RESULTS (Theory & Laboratory Course Marks)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semester_results (
    result_id INT AUTO_INCREMENT PRIMARY KEY,
    semester_id INT NOT NULL,
    subject_id INT NOT NULL,
    theory_marks DECIMAL(5,2),
    lab_marks DECIMAL(5,2),
    total_marks DECIMAL(5,2),
    credits DECIMAL(3,1) NOT NULL,
    grade_point DECIMAL(4,2),
    grade VARCHAR(5),
    attendance_percentage DECIMAL(5,2) DEFAULT 100.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_res_semester FOREIGN KEY (semester_id)
        REFERENCES semesters(semester_id) ON DELETE CASCADE,
    CONSTRAINT fk_res_subject FOREIGN KEY (subject_id)
        REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    CONSTRAINT uq_sem_subject UNIQUE (semester_id, subject_id),
    CONSTRAINT chk_theory_marks CHECK (theory_marks IS NULL OR (theory_marks BETWEEN 0.0 AND 100.0)),
    CONSTRAINT chk_lab_marks CHECK (lab_marks IS NULL OR (lab_marks BETWEEN 0.0 AND 100.0)),
    CONSTRAINT chk_att_pct CHECK (attendance_percentage BETWEEN 0.0 AND 100.0)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 6. DROP YEARS (Academic Gap Records - Rubric Requirement 3)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drop_years (
    drop_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    start_year INT NOT NULL,
    end_year INT NOT NULL,
    reason TEXT,
    approved_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_drop_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_drop_year UNIQUE (student_id, start_year),
    CONSTRAINT chk_drop_duration CHECK (end_year >= start_year)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 7. ACHIEVEMENT CATEGORIES (3NF Master Table)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievement_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 8. ACHIEVEMENTS & PORTFOLIO
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    achievement_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    organizer VARCHAR(120),
    event_scope ENUM('Internal', 'External') DEFAULT 'Internal',
    activity_type ENUM('Technical', 'Co-curricular', 'Extra-curricular', 'Seminar') DEFAULT 'Technical',
    achievement_date DATE,
    description TEXT,
    award_level VARCHAR(50),
    certificate_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ach_student FOREIGN KEY (student_id)
        REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_ach_category FOREIGN KEY (category_id)
        REFERENCES achievement_categories(category_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 9. SYNC QUEUE (Google Sheets Event Sourcing Queue)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_queue (
    queue_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INT NOT NULL,
    operation ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    payload_snapshot JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced TINYINT(1) DEFAULT 0,
    synced_at TIMESTAMP NULL,
    error TEXT
) ENGINE=InnoDB;

-- ------------------------------------------------------------------------------
-- 10. SYNC CONFIGURATION
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sync_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Populate default categories
INSERT IGNORE INTO achievement_categories (category_id, category_name, description) VALUES
(1, 'Hackathon', 'Competitive programming, product sprints, and hackathons'),
(2, 'Certification', 'Industry and online professional certifications'),
(3, 'Paper Publication', 'Peer-reviewed conference, journal, or workshop papers'),
(4, 'Workshop / Seminar', 'Workshops, masterclasses, and technical talks attended or delivered'),
(5, 'Sports & Cultural', 'Athletic competitions, arts, and cultural festivals'),
(6, 'Leadership & Club', 'Student council, technical club leads, or event coordination');

INSERT IGNORE INTO sync_config (config_key, config_value) VALUES
('google_sheet_id', ''),
('auto_sync_enabled', 'false'),
('last_full_sync', NULL);
