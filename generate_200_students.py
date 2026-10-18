"""
High-Performance Realistic 200+ Student Data Generator
Student Academic Progression & Portfolio Management System
Institutional Email Domain: @viva-technology.org
"""

import random
import sqlite3
import pymysql
import mysql_manager
import sync_engine

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Aayan", "Krishna", "Ishan",
    "Shaurya", "Atharv", "Dhruv", "Kabir", "Rithvik", "Ananya", "Diya", "Ishita", "Sanya", "Meera",
    "Priya", "Sneha", "Pooja", "Kavya", "Riya", "Tanvi", "Shreya", "Neha", "Riddhi", "Swati",
    "Rahul", "Rohit", "Praveen", "Amit", "Karan", "Varun", "Nikhil", "Harsh", "Manish", "Kunal",
    "Dev", "Jay", "Yash", "Gaurav", "Mayank", "Tushar", "Ayush", "Kartik", "Pranav", "Siddharth",
    "Akash", "Abhishek", "Deepak", "Rakesh", "Suresh", "Vikram", "Anil", "Sunil", "Rajesh", "Manoj",
    "Alok", "Chirag", "Gautam", "Hemant", "Jitendra", "Lalit", "Mohit", "Naveen", "Pankaj", "Raman",
    "Sachin", "Tarun", "Umesh", "Vineet", "Yogesh", "Anjali", "Bhavna", "Chhavi", "Divya", "Garima",
    "Heena", "Jyoti", "Komal", "Lata", "Monika", "Nandini", "Pallavi", "Radha", "Sarita", "Urmila"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Nair", "Iyer", "Gupta", "Singh", "Kumar", "Tiwari", "Mishra",
    "Joshi", "Rao", "Reddy", "Kulkarni", "Deshmukh", "Bhat", "Banerjee", "Chatterjee", "Sen", "Mehta",
    "Shah", "Agarwal", "Jain", "Das", "Ghosh", "Menon", "Pillai", "Choudhury", "Chauhan", "Yadav",
    "Pandey", "Tripathi", "Shukla", "Dubey", "Saxena", "Bhardwaj", "Bhatia", "Malhotra", "Kapoor", "Arora"
]

DEPTS = [
    ("Computer Science & Engineering", "CS"),
    ("Information Science & Engineering", "IS"),
    ("Electronics & Communication", "EC"),
    ("Data Science & AI", "DS"),
    ("Mechanical Engineering", "ME"),
    ("Civil Engineering", "CV"),
]

BOARDS_10 = ["CBSE", "ICSE", "State Board", "Maharashtra State Board"]
BOARDS_12 = ["CBSE", "ISC", "State Board", "HSC Maharashtra", "DTE Technical Diploma"]

ACH_TITLES = [
    ("1st Prize - Smart India Hackathon", "Ministry of Education / AICTE", "External", "Technical", "1st Prize", 1),
    ("Winner - Inter-College Hack-o-Sprint", "ACM Student Chapter", "External", "Technical", "Winner", 1),
    ("Runner Up - National Web3 Bootcamp", "ETHIndia Foundation", "External", "Technical", "2nd Place", 1),
    ("Finalist - IEEE Hardware Hackathon", "IEEE Student Branch", "External", "Technical", "Finalist", 1),
    ("AWS Certified Solutions Architect Associate", "Amazon Web Services", "External", "Technical", "Certified", 2),
    ("Google Cloud Certified Cloud Engineer", "Google Cloud", "External", "Technical", "Certified", 2),
    ("Oracle Certified Java SE 11 Developer", "Oracle University", "External", "Technical", "Certified", 2),
    ("Deep Learning Specialization Certification", "DeepLearning.AI / Coursera", "External", "Technical", "Distinction", 2),
    ("Research Paper: Optimizing DBMS Indexes with Learned Models", "IEEE Int. Conf. on Data Eng.", "External", "Technical", "Published", 3),
    ("Conference Paper: Edge AI for Traffic Monitoring", "Springer LNCS Proceedings", "External", "Technical", "Published", 3),
    ("Paper Presentation on Quantum Cryptography", "National Tech Symposium", "External", "Technical", "Best Paper", 3),
    ("Keynote Speaker: Scaling PostgreSQL for Real-Time Analytics", "Dept of Computer Science", "Internal", "Seminar", "Speaker", 4),
    ("Workshop Conductor: Full-Stack Web Development with React", "Technical Club", "Internal", "Seminar", "Lead Mentor", 4),
    ("Gold Medalist - Inter-University Badminton Men's Singles", "State University Sports Council", "External", "Extra-curricular", "Gold Medal", 5),
    ("Silver Trophy - Inter-Collegiate Cricket Tournament", "Mumbai University Sports Meet", "External", "Extra-curricular", "Runners-up", 5),
    ("Winner - Annual Classical Music Vocal Solo", "Cultural Affairs Council", "Internal", "Extra-curricular", "1st Prize", 5),
    ("President - Computer Society of India Student Chapter", "CSI College Chapter", "Internal", "Co-curricular", "President", 6),
    ("Secretary - Google Developer Groups Campus Chapter", "GDG Campus", "Internal", "Co-curricular", "Secretary", 6),
]

def generate_200_dataset():
    random.seed(42)  # reproducible high-quality data

    conn = sqlite3.connect("student_progression.db")
    cur = conn.cursor()

    # Clear old data
    cur.execute("PRAGMA foreign_keys = OFF;")
    for t in ["achievements", "drop_years", "semester_results", "semesters", "school_records", "students", "subjects", "sync_queue"]:
        cur.execute(f"DELETE FROM {t};")
    cur.execute("PRAGMA foreign_keys = ON;")

    # 1. Subjects Catalog
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
    sub_ids = []
    for code, name, stype, creds, mt, ml in subjects_data:
        cur.execute("""
            INSERT INTO subjects (subject_code, subject_name, subject_type, credits, department, max_theory_marks, max_lab_marks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code, name, stype, creds, "Computer Science & Engineering", mt, ml))
        sub_ids.append((cur.lastrowid, creds, stype))

    # 2. Generate 200 Students
    # Include PRAVEEN.MANOJ. TIWARI. as first highlighted student!
    students = [
        ("21CS100", "Praveen Manoj Tiwari", "praveen.tiwari@viva-technology.org", "9876543210", "Data Science & AI", 2021, "Active")
    ]

    used_rolls = {"21CS100"}
    used_emails = {"praveen.tiwari@viva-technology.org"}

    years = [2021, 2022, 2023, 2024]
    year_weights = [0.35, 0.30, 0.25, 0.10]

    while len(students) < 200:
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        full_name = f"{fn} {ln}"
        
        dept_name, dept_code = random.choice(DEPTS)
        adm_year = random.choices(years, weights=year_weights)[0]
        
        # Roll format: YY + DEPT + 3-digit number (e.g. 21CS045)
        roll_num = random.randint(1, 99)
        roll = f"{str(adm_year)[2:]}{dept_code}{roll_num:03d}"
        if roll in used_rolls:
            continue
        used_rolls.add(roll)

        # Email format: firstname.lastname@viva-technology.org
        clean_fn = fn.lower().replace(" ", "")
        clean_ln = ln.lower().replace(" ", "")
        email_cand = f"{clean_fn}.{clean_ln}@viva-technology.org"
        if email_cand in used_emails:
            email_cand = f"{clean_fn}.{clean_ln}{random.randint(1,99)}@viva-technology.org"
        used_emails.add(email_cand)

        phone = f"9{random.randint(100000000, 999999999)}"
        status = "Active" if adm_year >= 2022 else random.choices(["Active", "Graduated"], weights=[0.85, 0.15])[0]

        students.append((roll, full_name, email_cand, phone, dept_name, adm_year, status))

    print(f"Generated {len(students)} student profiles with @viva-technology.org emails.")

    # Insert Students and track IDs
    student_records = []
    for roll, name, email, phone, dept, y, status in students:
        cur.execute("""
            INSERT INTO students (roll_no, full_name, email, phone, department, admission_year, current_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (roll, name, email, phone, dept, y, status))
        sid = cur.lastrowid
        student_records.append((sid, roll, name, email, dept, y, status))

    # 3. School Records (10th and 12th for all 200 students = 400 records)
    for sid, roll, name, email, dept, y, status in student_records:
        y10 = y - 4
        y12 = y - 2
        pct10 = round(min(99.0, max(65.0, random.uniform(72.0, 97.5))), 1)
        pct12 = round(min(99.5, max(60.0, pct10 + random.uniform(-6.0, 2.0))), 1)
        b10 = random.choice(BOARDS_10)
        b12 = random.choice(BOARDS_12)
        inst = f"VIVA Institute of Technology / School {random.randint(1, 15)}"

        cur.execute("""
            INSERT INTO school_records (student_id, level, board, passing_year, percentage, institution_name)
            VALUES (?, '10th', ?, ?, ?, ?)
        """, (sid, b10, y10, pct10, inst))
        cur.execute("""
            INSERT INTO school_records (student_id, level, board, passing_year, percentage, institution_name)
            VALUES (?, '12th', ?, ?, ?, ?)
        """, (sid, b12, y12, pct12, inst))

    print("Created 400 School Records (10th & 12th).")

    # 4. Semesters & Theory/Lab Marks
    total_semesters = 0
    total_marks = 0

    # Pick ~12 students to have drop years
    drop_candidates = random.sample(student_records, 12)
    drop_sids = {s[0] for s in drop_candidates}

    for sid, roll, name, email, dept, adm_year, status in student_records:
        # Determine how many semesters student has completed based on admission year
        if adm_year == 2021:
            max_sem = 6
        elif adm_year == 2022:
            max_sem = 4
        elif adm_year == 2023:
            max_sem = 2
        else:
            max_sem = 1

        # Base student capability factor (6.0 to 9.8)
        base_ability = random.uniform(6.5, 9.6)
        if "Praveen" in name:
            base_ability = 9.4

        cgpa_running_pts = 0.0
        cgpa_running_creds = 0.0

        for sem_no in range(1, max_sem + 1):
            sem_yr = f"{adm_year + (sem_no - 1)//2}-{str(adm_year + (sem_no - 1)//2 + 1)[2:]}"
            
            # Semester SGPA with natural variance
            sem_sgpa = min(10.0, max(5.0, round(base_ability + random.uniform(-0.6, 0.6), 2)))
            
            cur.execute("""
                INSERT INTO semesters (student_id, semester_no, academic_year, sgpa, cgpa, status)
                VALUES (?, ?, ?, ?, ?, 'Completed')
            """, (sid, sem_no, sem_yr, sem_sgpa, sem_sgpa))
            sem_id = cur.lastrowid
            total_semesters += 1

            # Pick 3-4 subjects per semester
            sem_subs = random.sample(sub_ids, k=3)
            sem_credit_sum = 0.0
            sem_point_sum = 0.0

            for sub_id, creds, stype in sem_subs:
                # Target marks aligned with ability
                target_pct = min(98.0, max(50.0, (sem_sgpa * 9.5) + random.uniform(-5.0, 5.0)))
                
                th_marks = None
                lab_marks = None
                if stype in ("Theory", "Theory+Lab"):
                    th_marks = round(min(100.0, max(40.0, target_pct + random.uniform(-6.0, 6.0))), 1)
                if stype in ("Lab", "Theory+Lab"):
                    lab_marks = round(min(50.0, max(25.0, (target_pct / 2.0) + random.uniform(-3.0, 3.0))), 1)

                # Total marks & Grade
                tot = (th_marks or 0.0) + ((lab_marks or 0.0) * (2.0 if stype == "Theory+Lab" else 1.0))
                calc_pct = (tot / 2.0) if stype == "Theory+Lab" else (th_marks if th_marks else lab_marks * 2.0)
                
                gp = round(min(10.0, max(4.0, calc_pct / 10.0)), 1)
                grade = "O" if gp >= 9.5 else ("A+" if gp >= 8.5 else ("A" if gp >= 7.5 else ("B+" if gp >= 6.5 else "B")))

                cur.execute("""
                    INSERT INTO semester_results (semester_id, subject_id, theory_marks, lab_marks, total_marks, credits, grade_point, grade, attendance_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sem_id, sub_id, th_marks, lab_marks, tot, creds, gp, grade, round(random.uniform(78.0, 99.0), 1)))
                total_marks += 1

                sem_credit_sum += creds
                sem_point_sum += (creds * gp)

            # Recompute accurate SGPA & running CGPA
            if sem_credit_sum > 0:
                accurate_sgpa = round(sem_point_sum / sem_credit_sum, 2)
                cgpa_running_pts += sem_point_sum
                cgpa_running_creds += sem_credit_sum
                accurate_cgpa = round(cgpa_running_pts / cgpa_running_creds, 2)
                cur.execute("UPDATE semesters SET sgpa=?, cgpa=? WHERE semester_id=?", (accurate_sgpa, accurate_cgpa, sem_id))

    print(f"Created {total_semesters} Semesters and {total_marks} Theory/Lab Mark Results.")

    # 5. Drop Years (12 students)
    reasons = [
        "Medical leave for orthopedic recovery and surgery",
        "Family economic exigency and academic hiatus",
        "Preparation for national competitive examinations",
        "Extended medical leave due to prolonged illness",
        "Industry apprenticeship and technical internship sabbatical"
    ]
    approvals = ["Dean of Academics", "Academic Review Board", "Institutional Grievance Council", "University Registrar"]
    
    for sid in drop_sids:
        s_row = [s for s in student_records if s[0] == sid][0]
        st_yr = s_row[5] + 1
        en_yr = st_yr + 1
        rsn = random.choice(reasons)
        appr = random.choice(approvals)
        cur.execute("""
            INSERT INTO drop_years (student_id, start_year, end_year, reason, approved_by)
            VALUES (?, ?, ?, ?, ?)
        """, (sid, st_yr, en_yr, rsn, appr))

    print("Created 12 Drop-Year Records.")

    # 6. Extracurricular Achievements (~65 records)
    for _ in range(65):
        s_item = random.choice(student_records)
        ach = random.choice(ACH_TITLES)
        ach_date = f"{random.choice([2022, 2023, 2024])}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        cur.execute("""
            INSERT INTO achievements (student_id, category_id, title, organizer, event_scope, activity_type, achievement_date, description, award_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s_item[0], ach[5], ach[0], ach[1], ach[2], ach[3], ach_date, f"Demonstrated high technical and problem-solving merit representing {s_item[4]}.", ach[4]))

    conn.commit()
    conn.close()
    print("Database seeded successfully in SQLite!")

    # 7. Migrate all data to MySQL
    print("Migrating 200+ students to MySQL...")
    cfg = mysql_manager.load_mysql_config()
    ok_mig, msg_mig = mysql_manager.migrate_sqlite_to_mysql(
        cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["database"]
    )
    print(f"MySQL Migration: {ok_mig} | {msg_mig}")

    # 8. Push to Google Sheets via Webhook
    if cfg.get("webhook_url"):
        print("Pushing 200+ students to Google Sheets via Webhook...")
        ok_ws, msg_ws, rows_ws = mysql_manager.sync_mysql_via_webhook(
            cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["database"], cfg["webhook_url"]
        )
        print(f"Google Sheets Sync: {ok_ws} | {msg_ws} ({rows_ws} rows)")

if __name__ == "__main__":
    generate_200_dataset()
