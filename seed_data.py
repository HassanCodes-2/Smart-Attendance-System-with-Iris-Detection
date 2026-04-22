"""
Seed the IrisSecure database with demo data.

    python seed_data.py

Creates:
  - 1 admin  (admin@irissecure.com / admin123)
  - 40 students across 5 departments, each with a login password
  - ~90 days of attendance history
  - Full weekly timetable for all 5 departments
  - 5 sample announcements
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sqlite3
import pickle
import bcrypt
import random
import os
from datetime import date, timedelta, datetime

from database import DATABASE, init_db, migrate_db

if not os.path.exists(DATABASE):
    init_db()
else:
    migrate_db()

conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row

def run(sql, params=()):
    conn.execute(sql, params)

# ── 1. Admin ──────────────────────────────────────────────────────────────────
ADMIN_EMAIL    = 'admin@irissecure.com'
ADMIN_PASSWORD = 'admin123'
hashed_admin   = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
try:
    run('INSERT INTO admins (email, password) VALUES (?,?)', (ADMIN_EMAIL, hashed_admin))
    print(f'  ✅  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}')
except sqlite3.IntegrityError:
    print(f'  ℹ️   Admin already exists.')
conn.commit()

# ── 2. Students ───────────────────────────────────────────────────────────────
# Default password for every student is their user_id (e.g. "CS-001")
# They can be changed by the admin later.

STUDENTS = [
    # (user_id, name, department, parent_email, attendance_bias)
    ('CS-001','Ayesha Siddiqui',     'Computer Science',       'parent.ayesha@gmail.com',   0.92),
    ('CS-002','Bilal Ahmed',         'Computer Science',       'bilal.dad@gmail.com',        0.85),
    ('CS-003','Fatima Zahra',        'Computer Science',       'fzahra.parent@hotmail.com',  0.78),
    ('CS-004','Hassan Raza',         'Computer Science',       'raza.family@gmail.com',      0.55),
    ('CS-005','Imran Khan',          'Computer Science',       'imran.guardian@gmail.com',   0.60),
    ('CS-006','Javeria Malik',       'Computer Science',       'javeria.mom@gmail.com',      0.95),
    ('CS-007','Kamran Sheikh',       'Computer Science',       None,                         0.88),
    ('CS-008','Layla Noor',          'Computer Science',       'layla.parent@yahoo.com',     0.72),
    ('EE-001','Muhammad Ali',        'Electrical Engineering', 'maliparent@gmail.com',       0.90),
    ('EE-002','Nadia Hussain',       'Electrical Engineering', 'nadia.guardian@gmail.com',   0.82),
    ('EE-003','Omar Farooq',         'Electrical Engineering', 'farooq.family@gmail.com',    0.50),
    ('EE-004','Parveen Akhtar',      'Electrical Engineering', 'pakhtar.mom@gmail.com',      0.88),
    ('EE-005','Qasim Butt',          'Electrical Engineering', None,                         0.65),
    ('EE-006','Rabia Tariq',         'Electrical Engineering', 'rabia.parent@hotmail.com',   0.93),
    ('EE-007','Saad Ullah',          'Electrical Engineering', 'saad.dad@gmail.com',         0.79),
    ('EE-008','Tahira Bibi',         'Electrical Engineering', 'tahira.guardian@gmail.com',  0.86),
    ('BA-001','Usman Ghani',         'Business Administration','usman.parent@gmail.com',     0.91),
    ('BA-002','Vaneeza Ahmed',       'Business Administration','vaneeza.mom@gmail.com',      0.84),
    ('BA-003','Waqar Zaman',         'Business Administration','waqar.family@gmail.com',     0.68),
    ('BA-004','Xara Niazi',          'Business Administration','xara.parent@yahoo.com',      0.97),
    ('BA-005','Yasir Nawaz',         'Business Administration',None,                         0.45),
    ('BA-006','Zara Saleem',         'Business Administration','zara.guardian@gmail.com',    0.88),
    ('BA-007','Ahsan Iqbal',         'Business Administration','ahsan.dad@gmail.com',        0.76),
    ('BA-008','Bushra Hameed',       'Business Administration','bushra.mom@gmail.com',       0.94),
    ('ME-001','Daniyar Shah',        'Mechanical Engineering', 'daniyar.parent@gmail.com',   0.87),
    ('ME-002','Eman Riaz',           'Mechanical Engineering', 'eman.guardian@gmail.com',    0.80),
    ('ME-003','Fahad Mehmood',       'Mechanical Engineering', 'fahad.dad@gmail.com',        0.73),
    ('ME-004','Ghazala Pasha',       'Mechanical Engineering', 'ghazala.mom@gmail.com',      0.92),
    ('ME-005','Hamza Shahid',        'Mechanical Engineering', None,                         0.58),
    ('ME-006','Iqra Javed',          'Mechanical Engineering', 'iqra.parent@hotmail.com',    0.89),
    ('ME-007','Junaid Alam',         'Mechanical Engineering', 'junaid.family@gmail.com',    0.95),
    ('ME-008','Kiran Bashir',        'Mechanical Engineering', 'kiran.guardian@gmail.com',   0.77),
    ('DS-001','Lubna Arshad',        'Data Science',           'lubna.mom@gmail.com',        0.96),
    ('DS-002','Mohsin Rauf',         'Data Science',           'mohsin.parent@gmail.com',    0.83),
    ('DS-003','Noman Chaudhry',      'Data Science',           None,                         0.61),
    ('DS-004','Omaima Yousaf',       'Data Science',           'omaima.dad@gmail.com',       0.90),
    ('DS-005','Pervez Musharraf Jr', 'Data Science',           'pervez.guardian@gmail.com',  0.70),
    ('DS-006','Quratulain Hyder',    'Data Science',           'quratulain.mom@gmail.com',   0.88),
    ('DS-007','Rameez Raja',         'Data Science',           'rameez.parent@gmail.com',    0.52),
    ('DS-008','Saima Waheed',        'Data Science',           'saima.guardian@gmail.com',   0.93),
]

EMPTY_FEATURES = pickle.dumps(None)
TODAY          = date.today()
HISTORY_DAYS   = 90
inserted_ids   = {}

print(f'\n  Inserting {len(STUDENTS)} students…')
for (uid, name, dept, pemail, _bias) in STUDENTS:
    enrolled_on = TODAY - timedelta(days=HISTORY_DAYS + random.randint(0, 10))
    enrolled_ts = datetime.combine(enrolled_on, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
    # Default password = their user_id
    pwd_hash = bcrypt.hashpw(uid.encode(), bcrypt.gensalt()).decode()
    try:
        cur = conn.execute(
            'INSERT INTO users (user_id,name,department,parent_email,iris_features,password,created_at) VALUES (?,?,?,?,?,?,?)',
            (uid, name, dept, pemail, EMPTY_FEATURES, pwd_hash, enrolled_ts)
        )
        inserted_ids[uid] = cur.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute('SELECT id FROM users WHERE user_id=?', (uid,)).fetchone()
        if row:
            inserted_ids[uid] = row['id']
conn.commit()
print(f'  ✅  Students done.')

# ── 3. Attendance history ─────────────────────────────────────────────────────
print(f'\n  Generating attendance history…')
WEEKDAYS = {0,1,2,3,4}
rows = []
for (uid, name, dept, pemail, bias) in STUDENTS:
    db_id = inserted_ids.get(uid)
    if not db_id: continue
    for day_offset in range(HISTORY_DAYS, -1, -1):
        day = TODAY - timedelta(days=day_offset)
        if day.weekday() not in WEEKDAYS: continue
        if random.random() > bias: continue
        if random.random() < 0.15:
            status = 'late'; hour = random.randint(9, 11); minute = random.randint(1, 59)
        else:
            status = 'present'; hour = random.randint(7, 8); minute = random.randint(0, 59)
        ts = datetime(day.year, day.month, day.day, hour, minute, random.randint(0,59)).strftime('%Y-%m-%d %H:%M:%S')
        rows.append((db_id, status, ts))

conn.executemany('INSERT INTO attendance (user_id,status,timestamp) VALUES (?,?,?)', rows)
conn.commit()
print(f'  ✅  {len(rows)} attendance records.')

# ── 4. Timetable ──────────────────────────────────────────────────────────────
print('\n  Inserting timetable…')

# day_of_week: 0=Mon … 4=Fri
TIMETABLE = [
    # Computer Science
    ('Computer Science', 0, 'Data Structures',         'Dr. Imran',      'CS-101', '08:00', '09:30'),
    ('Computer Science', 0, 'Linear Algebra',           'Dr. Sara',       'M-201',  '10:00', '11:30'),
    ('Computer Science', 1, 'Object-Oriented Programming','Prof. Khalid', 'CS-102', '08:00', '09:30'),
    ('Computer Science', 1, 'Computer Networks',        'Dr. Hina',       'CS-103', '11:00', '12:30'),
    ('Computer Science', 2, 'Database Systems',         'Prof. Kamran',   'CS-201', '09:00', '10:30'),
    ('Computer Science', 2, 'Operating Systems',        'Dr. Imran',      'CS-101', '14:00', '15:30'),
    ('Computer Science', 3, 'Web Engineering',          'Prof. Amna',     'CS-102', '08:00', '09:30'),
    ('Computer Science', 3, 'Software Engineering',     'Dr. Tariq',      'CS-301', '10:00', '11:30'),
    ('Computer Science', 4, 'AI & Machine Learning',    'Dr. Hina',       'CS-201', '09:00', '10:30'),
    ('Computer Science', 4, 'Final Year Project Lab',   'Prof. Kamran',   'FYP-Lab','14:00', '17:00'),
    # Electrical Engineering
    ('Electrical Engineering', 0, 'Circuit Analysis',        'Dr. Asim',    'EE-101', '08:30', '10:00'),
    ('Electrical Engineering', 0, 'Calculus II',              'Dr. Rabia',   'M-101',  '11:00', '12:30'),
    ('Electrical Engineering', 1, 'Digital Logic Design',     'Prof. Naeem', 'EE-Lab', '08:00', '10:00'),
    ('Electrical Engineering', 1, 'Electromagnetic Fields',   'Dr. Asim',    'EE-102', '11:00', '12:30'),
    ('Electrical Engineering', 2, 'Signals & Systems',        'Dr. Zainab',  'EE-201', '09:00', '10:30'),
    ('Electrical Engineering', 3, 'Power Electronics',        'Prof. Naeem', 'EE-102', '08:00', '09:30'),
    ('Electrical Engineering', 3, 'Control Systems',          'Dr. Zainab',  'EE-201', '10:00', '11:30'),
    ('Electrical Engineering', 4, 'Microprocessors Lab',      'Dr. Asim',    'EE-Lab', '09:00', '12:00'),
    # Business Administration
    ('Business Administration', 0, 'Principles of Management','Dr. Farrukh', 'BA-101', '09:00', '10:30'),
    ('Business Administration', 0, 'Business Mathematics',    'Dr. Sana',    'M-301',  '11:00', '12:30'),
    ('Business Administration', 1, 'Microeconomics',          'Prof. Adnan', 'BA-201', '08:00', '09:30'),
    ('Business Administration', 1, 'Accounting I',            'Dr. Farrukh', 'BA-102', '10:00', '11:30'),
    ('Business Administration', 2, 'Marketing Management',    'Prof. Lubna', 'BA-201', '09:00', '10:30'),
    ('Business Administration', 2, 'Business Communication',  'Dr. Sana',    'BA-103', '11:30', '13:00'),
    ('Business Administration', 3, 'Human Resource Mgmt',     'Prof. Adnan', 'BA-201', '08:00', '09:30'),
    ('Business Administration', 4, 'Entrepreneurship',        'Dr. Farrukh', 'BA-101', '10:00', '11:30'),
    # Mechanical Engineering
    ('Mechanical Engineering', 0, 'Engineering Mechanics',    'Dr. Shoaib',  'ME-101', '08:00', '09:30'),
    ('Mechanical Engineering', 0, 'Thermodynamics',           'Dr. Naila',   'ME-102', '10:00', '11:30'),
    ('Mechanical Engineering', 1, 'Machine Drawing Lab',      'Prof. Waseem','ME-Lab', '08:00', '11:00'),
    ('Mechanical Engineering', 2, 'Fluid Mechanics',          'Dr. Shoaib',  'ME-201', '09:00', '10:30'),
    ('Mechanical Engineering', 2, 'Manufacturing Processes',  'Prof. Waseem','ME-102', '11:00', '12:30'),
    ('Mechanical Engineering', 3, 'Material Science',         'Dr. Naila',   'ME-101', '08:00', '09:30'),
    ('Mechanical Engineering', 4, 'CAD/CAM Lab',              'Dr. Shoaib',  'ME-Lab', '09:00', '12:00'),
    # Data Science
    ('Data Science', 0, 'Statistics for DS',         'Dr. Waqar',   'DS-101', '08:00', '09:30'),
    ('Data Science', 0, 'Python Programming',         'Prof. Areeba', 'CS-Lab', '10:00', '11:30'),
    ('Data Science', 1, 'Data Wrangling & EDA',       'Dr. Waqar',   'DS-201', '08:00', '09:30'),
    ('Data Science', 1, 'Linear Algebra for ML',      'Dr. Sidra',   'M-201',  '11:00', '12:30'),
    ('Data Science', 2, 'Machine Learning',            'Prof. Areeba','DS-301', '09:00', '10:30'),
    ('Data Science', 2, 'Big Data Technologies',       'Dr. Waqar',   'DS-201', '14:00', '15:30'),
    ('Data Science', 3, 'Deep Learning',               'Dr. Sidra',   'DS-301', '08:00', '09:30'),
    ('Data Science', 3, 'Data Visualisation',          'Prof. Areeba','CS-Lab', '10:00', '11:30'),
    ('Data Science', 4, 'Capstone Project',            'Dr. Waqar',   'DS-Lab', '09:00', '12:00'),
]

for entry in TIMETABLE:
    try:
        conn.execute(
            'INSERT INTO timetable (department,day_of_week,subject,instructor,room,start_time,end_time) VALUES (?,?,?,?,?,?,?)',
            entry
        )
    except Exception:
        pass
conn.commit()
print(f'  ✅  {len(TIMETABLE)} timetable entries.')

# ── 5. Announcements ──────────────────────────────────────────────────────────
print('\n  Inserting announcements…')
ANNOUNCEMENTS = [
    ('Mid-Term Exam Schedule Released',
     'Mid-term examinations will be held from 5th to 10th May. Detailed timetables have been pinned on all departmental notice boards. Students are advised to check their hall allocation on the student portal.',
     'all'),
    ('No Classes on Wednesday',
     'Due to the Annual Sports Gala, all classes on Wednesday 24th April are cancelled. Attendance will not be marked. Students are encouraged to participate in sporting events.',
     'all'),
    ('Computer Science — Lab Maintenance',
     'The CS Lab will be unavailable on Tuesday from 10:00 AM – 1:00 PM due to scheduled hardware upgrades. Students with lab sessions during this time should contact their instructor.',
     'Computer Science'),
    ('Data Science Project Submission Reminder',
     'All Capstone Project proposals are due by Friday 26th April at 5:00 PM. Late submissions will not be accepted. Upload your proposal PDF to the shared drive link sent via email.',
     'Data Science'),
    ('Library Extended Hours',
     'The university library will remain open until 10:00 PM on weekdays throughout the exam season. Students requiring overnight study access should carry their student ID.',
     'all'),
]
for (title, body, target) in ANNOUNCEMENTS:
    try:
        conn.execute('INSERT INTO announcements (title,body,target) VALUES (?,?,?)', (title, body, target))
    except Exception:
        pass
conn.commit()
print(f'  ✅  {len(ANNOUNCEMENTS)} announcements.')

# ── Summary ───────────────────────────────────────────────────────────────────
print('\n' + '═'*58)
print('  SEED COMPLETE')
print('═'*58)
print(f'\n  Admin portal   →  /admin/login')
print(f'  Email:            {ADMIN_EMAIL}')
print(f'  Password:         {ADMIN_PASSWORD}')
print(f'\n  Student portal →  /student/login')
print(f'  Login with Student ID as both username and password')
print(f'  e.g.  ID: CS-001  /  Password: CS-001')
print(f'\n  Students: {len(STUDENTS)}  |  Attendance: {len(rows)}  |  Timetable: {len(TIMETABLE)}')
at_risk = [s for s in STUDENTS if s[4] < 0.75]
print(f'  At-risk (<75%): {len(at_risk)} students')
print('\n' + '═'*58 + '\n')

conn.close()
