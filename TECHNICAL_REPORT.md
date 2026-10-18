# Technical Report & Viva Defense Document

**Project Title:** Student Academic Progression & Portfolio Management System  
**Course:** Database Management Systems (DBMS Mini-Project)  
**Database Engine:** SQLite 3 (ACID compliant, relational with foreign keys enabled)  
**Application Framework:** Streamlit (Python 3.13)  
**External Integration:** Google Sheets API v4 via `gspread` and `google-auth`  

---

## 1. System Architecture & Relational Design

The system is designed with a layered three-tier architecture:
1. **Presentation Layer (Streamlit GUI):** Provides intuitive CRUD forms, real-time student search, portfolio filters, dual-line progression graphs, and drop-year indicators.
2. **Business & Integration Layer (`db.py` & `sync_engine.py`):** Handles transactions, credit-weighted SGPA/CGPA calculation algorithms, payload snapshots, and Google Sheets queue dispatching.
3. **Database Layer (`schema.sql` on SQLite 3):** Fully normalized relational schema with primary keys, candidate unique keys, `CHECK` constraints, indexes, and referential integrity actions (`CASCADE` and `RESTRICT`).

```
+-------------------------------------------------------------+
|                     Streamlit GUI                           |
| (Dashboard, CRUD Forms, Progression Chart, Drop-Year Banner)|
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                Business & Calculation Engine                |
|  - Credit-Weighted SGPA Formula: Sum(C*GP) / Sum(C)         |
|  - Auto CGPA Averaging across Completed Semesters           |
|  - Sync Queue Dispatcher & Payload Snapshot Generator       |
+--------------+-------------------------------+--------------+
               |                               |
               v                               v
+-------------------------------+   +-------------------------+
|    Normalized Relational DB   |   |   Google Sheets Sync    |
|   (SQLite 3 - 3NF / BCNF)     |   |   (Queue-Driven Event   |
|   - PRAGMA foreign_keys = ON  |   |    Mirror per Table)    |
|   - 9 Tables, CHECKs, Indexes |   +-------------------------+
+-------------------------------+
```

---

## 2. Database Normalization & Mathematical 3NF Proofs

A relational schema is in **Third Normal Form (3NF)** if and only if for every non-trivial functional dependency $X \to Y$:
1. $X$ is a superkey, OR
2. Every attribute in $Y \setminus X$ is a prime attribute (part of some candidate key).

### Normalization Proof by Entity:

#### A. `students` Table
- **Attributes:** `student_id` (PK), `roll_no` (CK), `full_name`, `email` (CK), `phone`, `department`, `admission_year`, `current_status`.
- **Functional Dependencies:**
  - $F_1: \text{student\_id} \to \{\text{roll\_no}, \text{full\_name}, \text{email}, \text{phone}, \text{department}, \text{admission\_year}, \text{current\_status}\}$
  - $F_2: \text{roll\_no} \to \{\text{student\_id}, \text{full\_name}, \dots\}$
- **1NF:** Every column holds strictly atomic values (single phone, single department, no repeating groups).
- **2NF:** No composite candidate keys exist; hence, no partial functional dependency is possible.
- **3NF:** There is no transitive dependency ($X \to Y$ and $Y \to Z$ where $Y$ is non-key). Every non-key attribute is determined directly by the candidate keys `student_id` and `roll_no`.

#### B. `school_records` Table
- **Attributes:** `record_id` (PK), `student_id` (FK), `level`, `board`, `passing_year`, `percentage`, `institution_name`.
- **Candidate Key:** `(student_id, level)`
- **Functional Dependencies:**
  - $F_1: (\text{student\_id}, \text{level}) \to \{\text{board}, \text{passing\_year}, \text{percentage}, \text{institution\_name}\}$
- **3NF Proof:** Board, passing year, and percentage depend on the full composite key $(\text{student\_id}, \text{level})$. A student can have at most one 10th record and one 12th record. No attribute depends on only a subset of the candidate key (satisfies 2NF), and there is no dependency between non-key attributes (satisfies 3NF).

#### C. `semesters` Table
- **Attributes:** `semester_id` (PK), `student_id` (FK), `semester_no`, `academic_year`, `sgpa`, `cgpa`, `status`.
- **Candidate Key:** `(student_id, semester_no)`
- **Functional Dependencies:**
  - $F_1: (\text{student\_id}, \text{semester\_no}) \to \{\text{academic\_year}, \text{sgpa}, \text{cgpa}, \text{status}\}$
- **3NF Proof:** Term SGPA and status depend on the specific student and semester number. There are no transitive dependencies between academic year and SGPA.

#### D. `subjects` Table (Master Catalog)
- **Attributes:** `subject_id` (PK), `subject_code` (CK), `subject_name`, `subject_type`, `credits`, `department`, `max_theory_marks`, `max_lab_marks`.
- **Functional Dependencies:**
  - $F_1: \text{subject\_code} \to \{\text{subject\_name}, \text{subject\_type}, \text{credits}, \dots\}$
- **3NF Rationale:** Storing subject attributes in their own master catalog prevents:
  - **Insertion Anomaly:** New courses can be added to the curriculum even before any student enrolls.
  - **Update Anomaly:** Changing a course title or credit value requires updating exactly 1 row in `subjects`, rather than thousands of student result rows.
  - **Deletion Anomaly:** Deleting student records does not erase the course catalog.

#### E. `semester_results` Table (Theory & Laboratory Marks)
- **Attributes:** `result_id` (PK), `semester_id` (FK), `subject_id` (FK), `theory_marks`, `lab_marks`, `total_marks`, `credits`, `grade_point`, `grade`, `attendance_percentage`.
- **Candidate Key:** `(semester_id, subject_id)`
- **Functional Dependencies:**
  - $F_1: (\text{semester\_id}, \text{subject\_id}) \to \{\text{theory\_marks}, \text{lab\_marks}, \text{total\_marks}, \text{credits}, \text{grade\_point}, \text{grade}, \text{attendance\_percentage}\}$
- **3NF Proof:** The student's score in a specific subject depends completely on both the semester registration and the subject. All non-key attributes depend on the full candidate key `(semester_id, subject_id)` (2NF). Both theory and laboratory marks are stored as atomic numeric values bounded between 0.0 and 100.0.

#### F. `drop_years` Table
- **Attributes:** `drop_id` (PK), `student_id` (FK), `start_year`, `end_year`, `reason`, `approved_by`.
- **Candidate Key:** `(student_id, start_year)`
- **Constraint:** `CHECK(end_year >= start_year)` prevents invalid chronological spans.

#### G. `achievements` & `achievement_categories` Tables
- Categories are normalized into `achievement_categories(category_id, category_name)` to prevent misspelling, redundancy, and inconsistent category definitions across student portfolios.

---

## 3. Important Database Design Decisions (Viva Preparation)

### Q1: Why use surrogate keys (`AUTOINCREMENT`) when candidate keys exist?
**Answer:** Surrogate integer keys provide high-performance join operations because 64-bit integer comparisons are significantly faster than variable-length string comparisons (such as `roll_no` or composite keys). Additionally, if an institution allows updates to a student's roll number or email, foreign keys referencing `student_id` remain stable without needing expensive cascading key updates across tables.

### Q2: What is the difference between `ON DELETE CASCADE` and `ON DELETE RESTRICT` in your schema?
**Answer:** 
- **`ON DELETE CASCADE`** is used for parent-child lifecycle relationships where child data has no independent meaning without the parent. If a student is deleted, their associated `school_records`, `semesters`, `drop_years`, and `achievements` are automatically deleted.
- **`ON DELETE RESTRICT`** is used for shared master reference data. A course in `subjects` cannot be deleted if any student has an existing mark in `semester_results` pointing to that `subject_id`. This prevents orphaned records and preserves transcript integrity.

### Q3: How are Theory and Laboratory marks stored and evaluated?
**Answer:** In `semester_results`, courses may be classified as `Theory`, `Lab`, or `Theory+Lab`. Theory marks and laboratory marks are stored in separate nullable columns (`theory_marks` and `lab_marks`), both constrained by `CHECK(marks BETWEEN 0.0 AND 100.0)`. The application calculates total marks as:
$$\text{Total Marks} = \text{theory\_marks} + \text{lab\_marks}$$
and determines letter grades (`O, A+, A, B+, B, C, P, F`) and grade points (10.0 to 0.0) using absolute grading thresholds.

### Q4: How is SGPA calculated?
**Answer:** SGPA is calculated using the standard credit-weighted formula:
$$\text{SGPA} = \frac{\sum_{i=1}^{n} (\text{credits}_i \times \text{grade\_point}_i)}{\sum_{i=1}^{n} \text{credits}_i}$$
The SQL query for this calculation is:
```sql
SELECT ROUND(SUM(r.credits * r.grade_point) / SUM(r.credits), 2) AS calculated_sgpa
FROM semester_results r
WHERE r.semester_id = ?;
```

### Q5: How is Google Sheets synchronization designed, and why is a sync queue used?
**Answer:** 
A **Queue-Driven Event Sourcing Pattern** is used instead of synchronous remote API calls inside the SQLite transaction:
1. **Performance & Reliability:** External HTTP network calls to Google APIs take hundreds of milliseconds and can fail due to network timeouts or rate limits. Calling them inside a SQLite transaction would hold the SQLite write lock, causing database contention.
2. **Crash Resilience:** Every `INSERT`, `UPDATE`, or `DELETE` appends an operation to `sync_queue` with a snapshot payload within the same local transaction.
3. **Deletions Support:** When a row is deleted from SQLite, its primary key and identifying snapshot are preserved in `payload_snapshot` so the sync engine knows exactly which row to reconcile or remove in Google Sheets.
4. **Honest Reporting:** The app reports queue status as "Pending" until the Google Sheets API responds with HTTP 200, guaranteeing transparency.

---

## 4. Test & Verification Matrix

All 13 automated tests were executed using the Python `unittest` framework on the active workspace. **All 13 tests passed with 0 failures and 0 errors.**

| Test ID | Test Name | Description | Result |
| :--- | :--- | :--- | :--- |
| `01` | `test_01_student_unique_roll_no` | Enforces candidate key uniqueness on `roll_no` | **PASS (0.002s)** |
| `02` | `test_02_student_unique_email` | Enforces candidate key uniqueness on `email` | **PASS (0.002s)** |
| `03` | `test_03_percentage_check_constraint` | Validates `percentage BETWEEN 0.0 AND 100.0` | **PASS (0.002s)** |
| `04` | `test_04_sgpa_check_constraint` | Validates `sgpa BETWEEN 0.0 AND 10.0` | **PASS (0.002s)** |
| `05` | `test_05_drop_year_dates_check` | Validates `end_year >= start_year` | **PASS (0.002s)** |
| `06` | `test_06_cascade_delete_referential_integrity` | Verifies `ON DELETE CASCADE` removes school records, semesters, marks, and drop records | **PASS (0.005s)** |
| `07` | `test_07_restrict_delete_on_subject_in_use` | Verifies `ON DELETE RESTRICT` stops subject deletion if referenced by results | **PASS (0.003s)** |
| `08` | `test_08_theory_and_laboratory_marks_storage` | Verifies theory & lab marks storage and automatic grade computation | **PASS (0.004s)** |
| `09` | `test_09_credit_weighted_sgpa_calculation` | Validates credit-weighted SGPA formula calculation | **PASS (0.003s)** |
| `10` | `test_10_drop_year_crud_and_query` | Verifies drop-year create, read, update, and delete operations | **PASS (0.003s)** |
| `11` | `test_11_achievement_crud_and_filters` | Verifies portfolio achievements CRUD and query filters | **PASS (0.003s)** |
| `12` | `test_12_sync_queue_captures_insert_update_delete` | Validates queue capture for INSERT, UPDATE, and DELETE with payload snapshot | **PASS (0.004s)** |
| `13` | `test_13_mock_sync_simulation_harness` | End-to-end verification of sync queue processing pipeline | **PASS (0.005s)** |

---

## 5. Summary of Verified Features vs Disclosures

### Features Verified in Working Code:
- ✅ Normalized 3NF SQLite schema with all primary keys, candidate unique keys, CHECK constraints, and indexes.
- ✅ Full CRUD operations for Students, School Records, Semesters, Subjects, Theory/Lab Marks, Portfolio Achievements, and Drop Years.
- ✅ Theory and Laboratory marks stored independently per course with auto total, grade, grade point, and credit-weighted SGPA computation.
- ✅ Clean, responsive Streamlit dashboard with real-time student search and KPI cards.
- ✅ Academic progression dual-line graphs (SGPA and CGPA).
- ✅ Prominent drop-year indicators and alert banners with duration and approved reason.
- ✅ Portfolio filter engine with CSV export.
- ✅ Google Sheets queue-driven sync engine with audit logs, payload snapshots for deletions, and in-app local verification harness.
- ✅ Sample data seeder generating 5 diverse students, 10 school records, 13 semesters, 12 subjects, 20 marks records, and drop-year cases.

### Honest Disclosures & Setup Notes:
- To synchronize to an external live Google Sheet, the user must provide a Google Cloud Service Account JSON key (`service_account.json`) and share the target Google Spreadsheet with the service account email as Editor.
- When credentials are not yet configured, the system safely queues all operations in `sync_queue` and allows testing via the built-in **Sync Queue Verification Test**.
