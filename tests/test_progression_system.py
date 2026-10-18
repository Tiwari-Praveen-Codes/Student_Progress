import os
import unittest
import sqlite3
import json

# Ensure test DB path is used to isolate tests
TEST_DB = "test_student_progression.db"
os.environ["DB_PATH"] = TEST_DB

# Remove any old test DB
if os.path.exists(TEST_DB):
    try:
        os.remove(TEST_DB)
    except Exception:
        pass

import db
import sync_engine

class TestStudentProgressionDBMS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize schema in clean test database
        db.init_db("schema.sql")

    def setUp(self):
        # Clean all tables before each test
        with db.get_conn() as conn:
            conn.execute("DELETE FROM achievements;")
            conn.execute("DELETE FROM drop_years;")
            conn.execute("DELETE FROM semester_results;")
            conn.execute("DELETE FROM semesters;")
            conn.execute("DELETE FROM subjects;")
            conn.execute("DELETE FROM school_records;")
            conn.execute("DELETE FROM students;")
            conn.execute("DELETE FROM sync_queue;")
            conn.commit()

    # --------------------------------------------------------------------------
    # 1. RUBRIC 1 TESTS: RELATIONAL SCHEMA, 3NF & CONSTRAINTS
    # --------------------------------------------------------------------------
    def test_01_student_unique_roll_no(self):
        """Verify candidate key constraint: roll_no must be unique."""
        db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        with self.assertRaises(sqlite3.IntegrityError):
            db.add_student("21CS001", "Duplicate Roll", "s2@test.com", "9876543211", "Computer Science", 2021, "Active")

    def test_02_student_unique_email(self):
        """Verify unique email constraint."""
        db.add_student("21CS001", "Student One", "same@test.com", "9876543210", "Computer Science", 2021, "Active")
        with self.assertRaises(sqlite3.IntegrityError):
            db.add_student("21CS002", "Student Two", "same@test.com", "9876543211", "Computer Science", 2021, "Active")

    def test_03_percentage_check_constraint(self):
        """Verify CHECK constraint: percentage must be between 0.0 and 100.0."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        with self.assertRaises(sqlite3.IntegrityError):
            db.save_school_record(sid, "10th", "CBSE", 2019, 105.0)

    def test_04_sgpa_check_constraint(self):
        """Verify CHECK constraint: SGPA must be between 0.0 and 10.0."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        with self.assertRaises(sqlite3.IntegrityError):
            db.save_semester(sid, 1, "2021-22", 11.5, 9.0, "Completed")

    def test_05_drop_year_dates_check(self):
        """Verify CHECK constraint: drop year start_year <= end_year."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        with self.assertRaises(sqlite3.IntegrityError):
            db.save_drop_year(sid, 2024, 2022, "Invalid interval")

    def test_06_cascade_delete_referential_integrity(self):
        """Verify ON DELETE CASCADE: Deleting a student removes all related records."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        db.save_school_record(sid, "10th", "CBSE", 2019, 90.0)
        sem_id = db.save_semester(sid, 1, "2021-22", 8.5, 8.5, "Completed")
        sub_id = db.save_subject("CS101", "Intro to Programming", "Theory+Lab", 4.0)
        db.save_semester_result(sem_id, sub_id, theory_marks=80, lab_marks=40, credits=4.0)
        db.save_drop_year(sid, 2023, 2024, "Medical Leave")

        # Ensure records exist
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM school_records WHERE student_id=?", (sid,))["c"], 1)
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM semesters WHERE student_id=?", (sid,))["c"], 1)
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM drop_years WHERE student_id=?", (sid,))["c"], 1)

        # Delete student
        db.delete_student(sid)

        # Verify cascade removal
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM school_records WHERE student_id=?", (sid,))["c"], 0)
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM semesters WHERE student_id=?", (sid,))["c"], 0)
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM semester_results WHERE semester_id=?", (sem_id,))["c"], 0)
        self.assertEqual(db.fetch_one("SELECT COUNT(*) c FROM drop_years WHERE student_id=?", (sid,))["c"], 0)

    def test_07_restrict_delete_on_subject_in_use(self):
        """Verify ON DELETE RESTRICT: Cannot delete a subject referenced in semester_results."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        sem_id = db.save_semester(sid, 1, "2021-22", 8.5, 8.5, "Completed")
        sub_id = db.save_subject("CS101", "Intro to Programming", "Theory+Lab", 4.0)
        db.save_semester_result(sem_id, sub_id, theory_marks=80, lab_marks=40, credits=4.0)

        # Attempt to delete subject
        success, msg = db.delete_subject(sub_id)
        self.assertFalse(success)
        self.assertIn("ON DELETE RESTRICT", msg)

    # --------------------------------------------------------------------------
    # 2. RUBRIC 2 & MARKS STORAGE TESTS: THEORY & LAB MARKS, SGPA/CGPA FORMULA
    # --------------------------------------------------------------------------
    def test_08_theory_and_laboratory_marks_storage(self):
        """Verify independent theory and lab marks storage and automatic grade calculation."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        sem_id = db.save_semester(sid, 1, "2021-22", 8.0, 8.0, "Completed")
        sub_id = db.save_subject("CS101", "Data Structures", "Theory+Lab", 4.0, max_theory=100.0, max_lab=50.0)

        # Save marks: 90/100 theory, 45/50 lab -> 135/150 = 90% -> Grade 'O', Grade Point 10.0
        rid = db.save_semester_result(sem_id, sub_id, theory_marks=90.0, lab_marks=45.0, credits=4.0)
        res = db.fetch_one("SELECT * FROM semester_results WHERE result_id=?", (rid,))
        
        self.assertEqual(res["theory_marks"], 90.0)
        self.assertEqual(res["lab_marks"], 45.0)
        self.assertEqual(res["total_marks"], 135.0)
        self.assertEqual(res["grade_point"], 10.0)
        self.assertEqual(res["grade"], "O")

    def test_09_credit_weighted_sgpa_calculation(self):
        """Verify credit-weighted SGPA formula: Sum(Credits * GradePoint) / Sum(Credits)."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        sem_id = db.save_semester(sid, 1, "2021-22", 0.0, None, "In Progress")

        # Subject 1: 4 credits, Grade O (10.0) -> 40 points
        sub1 = db.save_subject("CS101", "Subject 1", "Theory", 4.0, max_theory=100.0)
        db.save_semester_result(sem_id, sub1, theory_marks=95.0, lab_marks=None, credits=4.0)

        # Subject 2: 4 credits, Grade A (8.0) -> 32 points
        sub2 = db.save_subject("CS102", "Subject 2", "Theory", 4.0, max_theory=100.0)
        db.save_semester_result(sem_id, sub2, theory_marks=75.0, lab_marks=None, credits=4.0)

        # Expected SGPA = (40 + 32) / 8 = 72 / 8 = 9.0
        computed_sgpa = db.auto_compute_semester_sgpa(sem_id)
        self.assertEqual(computed_sgpa, 9.0)

        # Check that semesters table was updated
        sem_row = db.fetch_one("SELECT sgpa FROM semesters WHERE semester_id=?", (sem_id,))
        self.assertEqual(sem_row["sgpa"], 9.0)

    # --------------------------------------------------------------------------
    # 3. RUBRIC 3 & CRUD TESTS: FULL ENTITY CRUD
    # --------------------------------------------------------------------------
    def test_10_drop_year_crud_and_query(self):
        """Verify drop year insertion, update, query, and deletion."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        did = db.save_drop_year(sid, 2022, 2023, "Family emergency", "Dean Office")
        
        row = db.fetch_one("SELECT * FROM drop_years WHERE drop_id=?", (did,))
        self.assertEqual(row["start_year"], 2022)
        self.assertEqual(row["end_year"], 2023)
        self.assertEqual(row["reason"], "Family emergency")

        # Update
        db.save_drop_year(sid, 2022, 2024, "Updated reason", "Academic Council")
        row_up = db.fetch_one("SELECT * FROM drop_years WHERE drop_id=?", (did,))
        self.assertEqual(row_up["end_year"], 2024)

        # Delete
        db.delete_drop_year(did)
        self.assertIsNone(db.fetch_one("SELECT * FROM drop_years WHERE drop_id=?", (did,)))

    def test_11_achievement_crud_and_filters(self):
        """Verify portfolio achievements CRUD and query filters."""
        sid = db.add_student("21CS001", "Student One", "s1@test.com", "9876543210", "Computer Science", 2021, "Active")
        cats = {r["category_name"]: r["category_id"] for r in db.fetch_all("SELECT * FROM achievement_categories")}
        cat_tech = cats.get("Technical") or list(cats.values())[0]

        aid = db.save_achievement(sid, cat_tech, "Hackathon 1st Place", "Tech Org", "External", "Technical", "2023-05-10", "Built portal", "1st Prize")
        self.assertIsNotNone(aid)

        ach = db.fetch_one("SELECT * FROM achievements WHERE achievement_id=?", (aid,))
        self.assertEqual(ach["title"], "Hackathon 1st Place")

        # Delete
        db.delete_achievement(aid)
        self.assertIsNone(db.fetch_one("SELECT * FROM achievements WHERE achievement_id=?", (aid,)))

    # --------------------------------------------------------------------------
    # 4. RUBRIC 4 & SYNC TESTS: GOOGLE SHEETS QUEUE & OPERATIONS
    # --------------------------------------------------------------------------
    def test_12_sync_queue_captures_insert_update_delete(self):
        """Verify that every database modification appends a queue record."""
        # 1. Insert student
        sid = db.add_student("21CS001", "Sync Test Student", "sync@test.com", "9876543210", "Computer Science", 2021, "Active")
        q1 = db.fetch_one("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=?", (sid,))
        self.assertIsNotNone(q1)
        self.assertIn(q1["operation"], ("INSERT", "UPSERT"))

        # 2. Update student
        db.update_student(sid, "21CS001", "Updated Name", "sync@test.com", "9876543210", "Computer Science", 2021, "Active")
        q_rows = db.fetch_all("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=?", (sid,))
        self.assertGreaterEqual(len(q_rows), 2)

        # 3. Delete student (with payload snapshot)
        db.delete_student(sid)
        q_del = db.fetch_one("SELECT * FROM sync_queue WHERE table_name='students' AND record_id=? AND operation='DELETE'", (sid,))
        self.assertIsNotNone(q_del)
        self.assertIsNotNone(q_del["payload_snapshot"])
        payload = json.loads(q_del["payload_snapshot"])
        self.assertEqual(payload["roll_no"], "21CS001")

    def test_13_mock_sync_simulation_harness(self):
        """Verify the mock sync test simulation harness runs without error."""
        result = sync_engine.run_mock_sync_simulation()
        self.assertTrue(result["success"])
        self.assertTrue(result["insert_captured"])
        self.assertTrue(result["update_captured"])
        self.assertTrue(result["delete_captured"])
        self.assertTrue(result["payload_saved"])

    @classmethod
    def tearDownClass(cls):
        # Reset DB_PATH env var
        os.environ["DB_PATH"] = "student_progression.db"
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

if __name__ == "__main__":
    unittest.main()
