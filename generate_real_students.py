"""
Curated 105 Unique Real Indian Students Dataset (Zero Repetitions)
Institutional Email Domain: @viva-technology.org
Student Academic Progression & Portfolio Management System
"""

import sqlite3
import random
import pymysql
import mysql_manager
import sync_engine

# 105 completely distinct, non-repetitive authentic Indian student names (Male & Female)
REAL_STUDENTS = [
    ("Praveen Manoj Tiwari", "M"),
    ("Raj Malhotra", "M"),
    ("Anjali Sharma", "F"),
    ("Rohan Verma", "M"),
    ("Sneha Patel", "F"),
    ("Aditya Nair", "M"),
    ("Pooja Iyer", "F"),
    ("Vikram Singh", "M"),
    ("Kavya Rao", "F"),
    ("Harsh Gupta", "M"),
    ("Riya Deshmukh", "F"),
    ("Kunal Joshi", "M"),
    ("Tanvi Kulkarni", "F"),
    ("Arjun Reddy", "M"),
    ("Diya Bhat", "F"),
    ("Ayush Banerjee", "M"),
    ("Ishita Chatterjee", "F"),
    ("Siddharth Sen", "M"),
    ("Meera Mehta", "F"),
    ("Gaurav Shah", "M"),
    ("Neha Agarwal", "F"),
    ("Mayank Jain", "M"),
    ("Swati Das", "F"),
    ("Nikhil Ghosh", "M"),
    ("Shreya Menon", "F"),
    ("Varun Pillai", "M"),
    ("Riddhi Choudhury", "F"),
    ("Karan Chauhan", "M"),
    ("Garima Yadav", "F"),
    ("Manish Pandey", "M"),
    ("Divya Tripathi", "F"),
    ("Tushar Shukla", "M"),
    ("Monika Dubey", "F"),
    ("Pranav Saxena", "M"),
    ("Pallavi Bhardwaj", "F"),
    ("Akash Bhatia", "M"),
    ("Chhavi Kapoor", "F"),
    ("Abhishek Arora", "M"),
    ("Komal Mishra", "F"),
    ("Deepak Soni", "M"),
    ("Jyoti Rawat", "F"),
    ("Rakesh Negi", "M"),
    ("Bhavna Bhatt", "F"),
    ("Suresh Solanki", "M"),
    ("Heena Rathore", "F"),
    ("Anil Parmar", "M"),
    ("Nandini Chawla", "F"),
    ("Sunil Makwana", "M"),
    ("Radha Waghela", "F"),
    ("Rajesh Gokhale", "M"),
    ("Sarita Apte", "F"),
    ("Manoj Date", "M"),
    ("Urmila Kadam", "F"),
    ("Alok Jadhav", "M"),
    ("Aarti Shinde", "F"),
    ("Chirag More", "M"),
    ("Priyanka Bhosale", "F"),
    ("Gautam Sawant", "M"),
    ("Deepali Gaikwad", "F"),
    ("Hemant Patil", "M"),
    ("Shruti Mane", "F"),
    ("Jitendra Thorat", "M"),
    ("Smita Pawar", "F"),
    ("Lalit Tambe", "M"),
    ("Preeti Chavan", "F"),
    ("Mohit Salunke", "M"),
    ("Vidya Shelke", "F"),
    ("Naveen Jagtap", "M"),
    ("Vandana Sonawane", "F"),
    ("Pankaj Bhalerao", "M"),
    ("Sunita Khare", "F"),
    ("Raman Vaze", "M"),
    ("Shilpa Kelkar", "F"),
    ("Sachin Gadgil", "M"),
    ("Rekha Pendse", "F"),
    ("Tarun Modak", "M"),
    ("Manisha Gore", "F"),
    ("Umesh Ranade", "M"),
    ("Rashmi Phadke", "F"),
    ("Vineet Sathe", "M"),
    ("Archana Chitnis", "F"),
    ("Yogesh Bapat", "M"),
    ("Sushma Joshi", "F"),
    ("Vivaan Trivedi", "M"),
    ("Namrata Upadhyay", "F"),
    ("Aayan Pathak", "M"),
    ("Seema Tiwari", "F"),
    ("Krishna Awasthi", "M"),
    ("Geeta Bajpai", "F"),
    ("Ishan Dixit", "M"),
    ("Poonam Chaubey", "F"),
    ("Shaurya Dwivedi", "M"),
    ("Pratibha Chaturvedi", "F"),
    ("Atharv Upadhyaya", "M"),
    ("Madhu Ojha", "F"),
    ("Dhruv Purohit", "M"),
    ("Sangeeta Acharya", "F"),
    ("Kabir Shastri", "M"),
    ("Anita Bhattacharya", "F"),
    ("Rithvik Ganguly", "M"),
    ("Madhuri Mukherjee", "F"),
    ("Reyansh Chakraborty", "M"),
    ("Sulochana Majumdar", "F"),
    ("Sanya Bose", "F"),
    ("Rahul Roy", "M")
]

DEPTS = [
    ("Computer Science & Engineering", "CS"),
    ("Information Science & Engineering", "IS"),
    ("Electronics & Communication", "EC"),
    ("Data Science & AI", "DS"),
    ("Mechanical Engineering", "ME"),
    ("Civil Engineering", "CV"),
]

BOARDS_10 = ["CBSE", "ICSE", "Maharashtra State Board"]
BOARDS_12 = ["CBSE", "HSC Maharashtra", "ISC", "State Board"]

ACH_TEMPLATES = [
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

def seed_unique_real_dataset():
    random.seed(101)  # deterministic quality seed

    conn = sqlite3.connect("student_progression.db")
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys = OFF;")
    for t in ["achievements", "drop_years", "semester_results", "semesters", "school_records", "students", "subjects", "sync_queue"]:
        cur.execute(f"DELETE FROM {t};")
    cur.execute("PRAGMA foreign_keys = ON;")

    # 1. Subjects Master Catalog
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

    # 2. Build 105 completely unique students (NO DUPLICATES)
    student_records = []
    years = [2021, 2022, 2023, 2024]
    dept_counters = {code: 1 for _, code in DEPTS}

    for idx, (full_name, gender) in enumerate(REAL_STUDENTS, 1):
        dept_name, dept_code = DEPTS[idx % len(DEPTS)]
        adm_year = years[idx % len(years)]
        
        # Unique roll number
        roll_seq = dept_counters[dept_code]
        dept_counters[dept_code] += 1
        roll = f"{str(adm_year)[2:]}{dept_code}{roll_seq:03d}"
        
        # Email: firstname.lastname@viva-technology.org
        name_parts = full_name.lower().split()
        first_p = name_parts[0]
        last_p = name_parts[-1]
        email = f"{first_p}.{last_p}@viva-technology.org"
        
        phone = f"98{idx:03d}{random.randint(10000, 99999)}"
        status = "Active" if adm_year >= 2022 else ("Graduated" if idx % 5 == 0 else "Active")

        cur.execute("""
            INSERT INTO students (roll_no, full_name, email, phone, department, admission_year, current_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (roll, full_name, email, phone, dept_name, adm_year, status))
        sid = cur.lastrowid
        student_records.append((sid, roll, full_name, email, dept_name, adm_year, status))

    print(f"Created {len(student_records)} completely unique students with @viva-technology.org emails.")

    # 3. School records (10th and 12th for all 105 students = 210 records)
    for sid, roll, name, email, dept, y, status in student_records:
        y10 = y - 4
        y12 = y - 2
        pct10 = round(random.uniform(70.0, 97.0), 1)
        pct12 = round(min(98.5, max(60.0, pct10 + random.uniform(-6.0, 2.0))), 1)
        b10 = random.choice(BOARDS_10)
        b12 = random.choice(BOARDS_12)
        inst = f"VIVA College of Arts, Science & Commerce / School {random.randint(1, 10)}"

        cur.execute("""
            INSERT INTO school_records (student_id, level, board, passing_year, percentage, institution_name)
            VALUES (?, '10th', ?, ?, ?, ?)
        """, (sid, b10, y10, pct10, inst))
        cur.execute("""
            INSERT INTO school_records (student_id, level, board, passing_year, percentage, institution_name)
            VALUES (?, '12th', ?, ?, ?, ?)
        """, (sid, b12, y12, pct12, inst))

    print("Created 210 School Records (10th & 12th).")

    # 4. Semesters & Theory/Lab Marks
    total_semesters = 0
    total_marks = 0

    # Pick 8 specific students to have academic gap years
    drop_sids = {s[0] for s in student_records[10:18]}

    for sid, roll, name, email, dept, adm_year, status in student_records:
        if adm_year == 2021:
            max_sem = 6
        elif adm_year == 2022:
            max_sem = 4
        elif adm_year == 2023:
            max_sem = 2
        else:
            max_sem = 1

        base_ability = random.uniform(6.8, 9.6)
        if "Praveen" in name or "Raj" in name:
            base_ability = 9.4

        cgpa_running_pts = 0.0
        cgpa_running_creds = 0.0

        for sem_no in range(1, max_sem + 1):
            sem_yr = f"{adm_year + (sem_no - 1)//2}-{str(adm_year + (sem_no - 1)//2 + 1)[2:]}"
            sem_sgpa = min(10.0, max(5.5, round(base_ability + random.uniform(-0.5, 0.5), 2)))

            cur.execute("""
                INSERT INTO semesters (student_id, semester_no, academic_year, sgpa, cgpa, status)
                VALUES (?, ?, ?, ?, ?, 'Completed')
            """, (sid, sem_no, sem_yr, sem_sgpa, sem_sgpa))
            sem_id = cur.lastrowid
            total_semesters += 1

            sem_subs = random.sample(sub_ids, k=3)
            sem_credit_sum = 0.0
            sem_point_sum = 0.0

            for sub_id, creds, stype in sem_subs:
                target_pct = min(98.0, max(50.0, (sem_sgpa * 9.5) + random.uniform(-4.0, 4.0)))
                th_marks = round(min(100.0, max(42.0, target_pct + random.uniform(-5.0, 5.0))), 1) if stype in ("Theory", "Theory+Lab") else None
                lab_marks = round(min(50.0, max(26.0, (target_pct / 2.0) + random.uniform(-2.5, 2.5))), 1) if stype in ("Lab", "Theory+Lab") else None

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

            if sem_credit_sum > 0:
                accurate_sgpa = round(sem_point_sum / sem_credit_sum, 2)
                cgpa_running_pts += sem_point_sum
                cgpa_running_creds += sem_credit_sum
                accurate_cgpa = round(cgpa_running_pts / cgpa_running_creds, 2)
                cur.execute("UPDATE semesters SET sgpa=?, cgpa=? WHERE semester_id=?", (accurate_sgpa, accurate_cgpa, sem_id))

    print(f"Created {total_semesters} Semesters and {total_marks} individual Theory/Lab results.")

    # 5. Drop Years (8 specific distinct students)
    reasons = [
        "Medical leave for knee ligament reconstruction & physiotherapy",
        "Preparation for GATE & civil service examinations",
        "Sabbatical for technical startup incubator participation",
        "Family economic exigency and academic break"
    ]
    approvals = ["Dean of Academics", "Academic Council", "University Registrar"]
    
    for idx, sid in enumerate(drop_sids):
        s_row = [s for s in student_records if s[0] == sid][0]
        st_yr = s_row[5] + 1
        en_yr = st_yr + 1
        cur.execute("""
            INSERT INTO drop_years (student_id, start_year, end_year, reason, approved_by)
            VALUES (?, ?, ?, ?, ?)
        """, (sid, st_yr, en_yr, reasons[idx % len(reasons)], approvals[idx % len(approvals)]))

    print("Created 8 Drop-Year Records.")

    # 6. Achievements (~45 distinct records)
    for idx in range(45):
        s_item = student_records[idx % len(student_records)]
        ach = ACH_TEMPLATES[idx % len(ACH_TEMPLATES)]
        ach_date = f"{random.choice([2022, 2023, 2024])}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
        cur.execute("""
            INSERT INTO achievements (student_id, category_id, title, organizer, event_scope, activity_type, achievement_date, description, award_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s_item[0], ach[5], ach[0], ach[1], ach[2], ach[3], ach_date, f"Demonstrated high merit representing {s_item[4]} at VIVA Institute of Technology.", ach[4]))

    conn.commit()
    conn.close()
    print("SQLite populated successfully!")

    # 7. Migrate all data to MySQL
    print("Migrating unique students to MySQL...")
    cfg = mysql_manager.load_mysql_config()
    ok_mig, msg_mig = mysql_manager.migrate_sqlite_to_mysql(
        cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["database"]
    )
    print(f"MySQL Migration: {ok_mig} | {msg_mig}")

    # 8. Push to Google Sheets via Webhook
    if cfg.get("webhook_url"):
        print("Pushing unique students to Google Sheets via Webhook...")
        ok_ws, msg_ws, rows_ws = mysql_manager.sync_mysql_via_webhook(
            cfg["host"], cfg["port"], cfg["user"], cfg["password"], cfg["database"], cfg["webhook_url"]
        )
        print(f"Google Sheets Sync: {ok_ws} | {msg_ws} ({rows_ws} rows)")

if __name__ == "__main__":
    seed_unique_real_dataset()
