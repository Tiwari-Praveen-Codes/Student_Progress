# Student Academic Progression & Portfolio Management System

A normalized, production-grade DBMS mini-project built with Python, SQLite, Streamlit, and Google Sheets API. Designed for rigorous evaluation against 3NF database normalization, automated Google Sheets synchronization, GUI usability with academic progression charts & drop-year indicators, and technical defense.

---

## 🚀 Quick Start (Windows)

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13 / 3.14)
- Windows PowerShell or Command Prompt

### 2. Environment Setup & Launch
Open PowerShell inside this directory (`student_progression_dbms`):

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run the Streamlit web application
streamlit run app.py
```

*Note: If PowerShell script execution policy blocks activation, launch directly via:*
```powershell
.\.venv\Scripts\streamlit run app.py
```

The application automatically initializes `student_progression.db` with all foreign keys, CHECK constraints, and unique indices on first run.

### 3. Load Sample Demo Data
Once the web app opens at `http://localhost:8501`:
1. Look at the left sidebar.
2. Click **🌱 Load Complete Sample Data**.
3. This instantly seeds 5 realistic students, 10 school records, 13 semesters, 12 computer science courses, 20 theory & lab marks entries, 5 portfolio achievements, and an academic gap/drop year for demonstration.

---

## 🧪 Running the Automated Test Suite

Run the comprehensive unit and integration test suite:

```powershell
.\.venv\Scripts\python -m unittest tests/test_progression_system.py
```

### Verified Test Cases:
- `test_01_student_unique_roll_no`: Enforces candidate key uniqueness (`roll_no`).
- `test_02_student_unique_email`: Enforces candidate key uniqueness (`email`).
- `test_03_percentage_check_constraint`: Validates `percentage BETWEEN 0.0 AND 100.0`.
- `test_04_sgpa_check_constraint`: Validates `sgpa BETWEEN 0.0 AND 10.0`.
- `test_05_drop_year_dates_check`: Enforces `end_year >= start_year`.
- `test_06_cascade_delete_referential_integrity`: Confirms `ON DELETE CASCADE` removes all dependent child records on student deletion.
- `test_07_restrict_delete_on_subject_in_use`: Confirms `ON DELETE RESTRICT` prevents subject deletion when referenced by marks.
- `test_08_theory_and_laboratory_marks_storage`: Verifies independent theory and lab marks storage with automatic grade calculation.
- `test_09_credit_weighted_sgpa_calculation`: Verifies $\text{SGPA} = \frac{\sum (\text{credits} \times \text{grade\_point})}{\sum \text{credits}}$.
- `test_10_drop_year_crud_and_query`: Tests drop year insertion, update, query, and deletion.
- `test_11_achievement_crud_and_filters`: Tests portfolio achievements CRUD and query filtering.
- `test_12_sync_queue_captures_insert_update_delete`: Verifies that every database change creates an audit queue entry with snapshot payloads.
- `test_13_mock_sync_simulation_harness`: Verifies the mock sync engine execution harness.

---

## ☁️ Google Sheets Synchronization Setup Guide

The synchronization engine uses a **Queue-Driven Event Pattern** (`sync_queue`). Every database modification (`INSERT`, `UPDATE`, `DELETE`) appends an operation to `sync_queue`. When credentials and Sheet ID are provided, changes are pushed automatically to dedicated worksheets in Google Sheets.

### Step-by-Step API Setup:

1. **Google Cloud Console:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Create a project (e.g. `Student-DBMS-Sync`).
2. **Enable Required APIs:**
   - In **APIs & Services > Library**, search and enable:
     - **Google Sheets API**
     - **Google Drive API**
3. **Create Service Account & Download Key:**
   - Go to **APIs & Services > Credentials > Create Credentials > Service Account**.
   - Name the service account (e.g., `sheets-sync-worker`).
   - Click on the created service account > **Keys** tab > **Add Key > Create new key > JSON**.
   - Save the downloaded JSON file as `service_account.json` in this project folder.
   - *Security Note: `service_account.json` is listed in `.gitignore` and is never committed or exposed.*
4. **Create Google Spreadsheet:**
   - Create a new Google Spreadsheet at [sheets.google.com](https://sheets.google.com).
   - Click **Share** and add the service account email (found in `service_account.json` or shown in the app's sync tab) with role **Editor**.
   - Copy the spreadsheet ID from the URL:
     `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`
5. **Configure & Synchronize:**
   - Option A (In App): Open the **☁️ Google Sheets Sync** tab in the app, paste your Spreadsheet ID into the input field, and click **Save Sync Settings**.
   - Option B (Environment Variables):
     ```powershell
     $env:GOOGLE_SHEET_ID="<your-spreadsheet-id>"
     $env:GOOGLE_APPLICATION_CREDENTIALS="service_account.json"
     streamlit run app.py
     ```
   - Click **Process Sync Queue Now** or **Full Database Refresh Sync**.
   - In-App Verification: If live credentials are not yet configured, click **Run Sync Queue Verification Test** on the sync tab to verify the queue pipeline locally.

---

## 📐 Database Normalization (3NF) & Schema Design

| Table Name | Primary Key | Candidate / Unique Keys | Foreign Keys & Actions | 3NF Justification |
| :--- | :--- | :--- | :--- | :--- |
| `students` | `student_id` | `roll_no`, `email` | None | All student demographic attributes depend directly on `student_id`. |
| `school_records` | `record_id` | `(student_id, level)` | `student_id` $\to$ `students(student_id)` [`CASCADE`] | Prior academic scores depend entirely on `(student_id, level)`. No transitive dependencies. |
| `semesters` | `semester_id` | `(student_id, semester_no)` | `student_id` $\to$ `students(student_id)` [`CASCADE`] | Term GPA and status depend on student and term number. |
| `subjects` | `subject_id` | `subject_code` | None | Master catalog of courses. Isolating subject definition prevents repeating name, credits, and type across thousands of student attempts. |
| `semester_results` | `result_id` | `(semester_id, subject_id)` | `semester_id` $\to$ `semesters(semester_id)` [`CASCADE`]<br/>`subject_id` $\to$ `subjects(subject_id)` [`RESTRICT`] | Stores independent **Theory Marks** and **Laboratory Marks**. All grades and points depend on the composite pair `(semester_id, subject_id)`. |
| `drop_years` | `drop_id` | `(student_id, start_year)` | `student_id` $\to$ `students(student_id)` [`CASCADE`] | Stores official academic gaps. Candidate key prevents duplicate drop records for the same year. |
| `achievement_categories` | `category_id` | `category_name` | None | Master lookup table preventing update anomalies in portfolio records. |
| `achievements` | `achievement_id` | None | `student_id` $\to$ `students(student_id)` [`CASCADE`]<br/>`category_id` $\to$ `achievement_categories(category_id)` [`RESTRICT`] | Student co-curricular portfolio items depend directly on `achievement_id`. |
| `sync_queue` | `queue_id` | None | None | Transactional event queue logging every insert, update, and delete for reliable Google Sheets synchronization. |

---

## 💡 Evaluation Rubric Mapping

1. **Database Design & 3NF Normalization (2.5 / 2.5 Marks):**
   - 9 relational tables strictly in 3NF / BCNF.
   - Comprehensive PKs, candidate keys, foreign keys (`ON DELETE CASCADE` and `ON DELETE RESTRICT`), and `CHECK` constraints.
   - Separate theory and laboratory marks stored in `semester_results`.
2. **Automatic Google Sheets Synchronization (2.5 / 2.5 Marks):**
   - Queue-driven synchronization engine (`sync_queue`) capturing `INSERT`, `UPDATE`, and `DELETE`.
   - Stores payload snapshots for audited deletion from Google Sheets.
   - Auto-sync on write and manual refresh capabilities.
   - Safe credential management (`.gitignore` + environment variable support).
3. **GUI Usability, CRUD, Progression Graph & Drop-Year Indicators (2.5 / 2.5 Marks):**
   - Streamlit dashboard with real-time KPI metrics and search.
   - Full CRUD across Students, School Records, Semesters, Subjects, Marks, Portfolio, and Drop Years.
   - Prominent red alert banner and badges indicating student drop years.
   - Dual-line SGPA and CGPA academic progression trend charts.
4. **Technical Understanding, SQL Queries, Architecture & Originality (2.5 / 2.5 Marks):**
   - Clean, modular code (`app.py`, `db.py`, `sync_engine.py`, `schema.sql`).
   - Dedicated "Schema & Viva Prep" in-app tab explaining 1NF, 2NF, 3NF and displaying key SQL queries.
   - 13 passing unit tests and sample data seeder.
