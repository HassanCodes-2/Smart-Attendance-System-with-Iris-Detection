import sqlite3
import pickle
import os
from datetime import datetime, date, timedelta

DATABASE = os.path.join('/data', 'iris_system.db') if os.path.isdir('/data') else 'iris_system.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.close()


def migrate_db():
    conn = get_db_connection()
    migrations = [
        "ALTER TABLE attendance ADD COLUMN status TEXT DEFAULT 'present'",
        "ALTER TABLE users ADD COLUMN password TEXT",
        """CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            subject TEXT NOT NULL,
            instructor TEXT,
            room TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            target TEXT DEFAULT 'all',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for m in migrations:
        try:
            conn.execute(m)
            conn.commit()
        except Exception:
            pass
    conn.close()


# ── Users ─────────────────────────────────────────────────────────────────────

def add_user(user_id, name, department, features, parent_email=None, password=None):
    conn = get_db_connection()
    blob = pickle.dumps(features)
    cur = conn.execute(
        'INSERT INTO users (user_id, name, department, parent_email, iris_features, password) VALUES (?,?,?,?,?,?)',
        (user_id, name, department, parent_email, blob, password)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def delete_user(uid):
    conn = get_db_connection()
    conn.execute('DELETE FROM attendance WHERE user_id=?', (uid,))
    conn.execute('DELETE FROM users WHERE id=?', (uid,))
    conn.commit()
    conn.close()


def get_user_by_id(uid):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    conn.close()
    return row


def get_user_by_user_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return row


def get_all_users():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    result = []
    for u in rows:
        result.append({
            'id': u['id'], 'user_id': u['user_id'],
            'name': u['name'], 'department': u['department'],
            'parent_email': u['parent_email'],
            'features': pickle.loads(u['iris_features']),
        })
    return result


def get_all_students():
    """All users as plain dicts (no features blob)."""
    conn = get_db_connection()
    rows = conn.execute('SELECT id,user_id,name,department,parent_email,created_at FROM users ORDER BY name').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_count():
    conn = get_db_connection()
    n = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    return n


def get_all_departments():
    conn = get_db_connection()
    rows = conn.execute('SELECT DISTINCT department FROM users ORDER BY department').fetchall()
    conn.close()
    return [r['department'] for r in rows]


# ── Attendance ────────────────────────────────────────────────────────────────

def mark_attendance(user_id, status='present'):
    conn = get_db_connection()
    conn.execute('INSERT INTO attendance (user_id, status) VALUES (?,?)', (user_id, status))
    conn.commit()
    conn.close()


def already_marked_today(user_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM attendance WHERE user_id=? AND DATE(timestamp)=DATE('now')",
        (user_id,)
    ).fetchone()
    conn.close()
    return row is not None


def get_attendance_logs(departments=None, date_from=None, date_to=None, limit=None):
    conn = get_db_connection()
    q = '''SELECT a.id, u.id AS uid, u.name, u.user_id, u.department,
                  a.timestamp, a.status
           FROM attendance a JOIN users u ON a.user_id=u.id WHERE 1=1'''
    p = []
    if departments:
        q += f' AND u.department IN ({",".join("?"*len(departments))})'
        p += list(departments)
    if date_from:
        q += ' AND DATE(a.timestamp) >= ?'
        p.append(date_from)
    if date_to:
        q += ' AND DATE(a.timestamp) <= ?'
        p.append(date_to)
    q += ' ORDER BY a.timestamp DESC'
    if limit:
        q += f' LIMIT {int(limit)}'
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return rows


def get_attendance_by_user(uid):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DATE(timestamp) AS date, status FROM attendance WHERE user_id=? ORDER BY timestamp DESC",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_absent_users(date_str):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT id, name, parent_email, department FROM users
        WHERE parent_email IS NOT NULL AND parent_email!=''
          AND id NOT IN (SELECT user_id FROM attendance WHERE DATE(timestamp)=?)
    ''', (date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_summary():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT u.id, u.user_id, u.name, u.department, u.created_at,
               COUNT(DISTINCT DATE(a.timestamp)) AS present_days
        FROM users u LEFT JOIN attendance a ON u.id=a.user_id
        GROUP BY u.id ORDER BY u.name
    ''').fetchall()
    conn.close()
    today = date.today()
    result = []
    for row in rows:
        r = dict(row)
        try:
            created = datetime.strptime(r['created_at'][:10], '%Y-%m-%d').date()
        except Exception:
            created = today
        total = max((today - created).days, 1)
        present = r['present_days'] or 0
        r['percentage'] = min(round((present / total) * 100), 100)
        r['total_days'] = total
        result.append(r)
    return result


# ── Charts ────────────────────────────────────────────────────────────────────

def get_chart_daily_trend(days=30):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT DATE(timestamp) AS d, COUNT(*) AS cnt
        FROM attendance WHERE timestamp >= date('now', ?)
        GROUP BY d ORDER BY d ASC
    ''', (f'-{days} days',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chart_department_stats():
    conn = get_db_connection()
    depts = conn.execute('SELECT DISTINCT department FROM users ORDER BY department').fetchall()
    result = []
    today = date.today()
    for d in depts:
        dept = d['department']
        total_students = conn.execute('SELECT COUNT(*) FROM users WHERE department=?', (dept,)).fetchone()[0]
        if total_students == 0:
            result.append({'department': dept, 'percentage': 0})
            continue
        present_today = conn.execute(
            "SELECT COUNT(DISTINCT a.user_id) FROM attendance a JOIN users u ON a.user_id=u.id "
            "WHERE u.department=? AND DATE(a.timestamp)=?", (dept, today.isoformat())
        ).fetchone()[0]
        result.append({'department': dept, 'percentage': round((present_today / total_students) * 100)})
    conn.close()
    return result


def get_chart_today_summary():
    conn = get_db_connection()
    today = date.today().isoformat()
    total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    present = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE DATE(timestamp)=? AND status='present'", (today,)
    ).fetchone()[0]
    late = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE DATE(timestamp)=? AND status='late'", (today,)
    ).fetchone()[0]
    conn.close()
    absent = max(total - present - late, 0)
    return {'present': present, 'late': late, 'absent': absent, 'total': total}


def get_today_present_count():
    conn = get_db_connection()
    today = date.today().isoformat()
    n = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE DATE(timestamp)=?", (today,)
    ).fetchone()[0]
    conn.close()
    return n


# ── Admins ────────────────────────────────────────────────────────────────────

def get_admin_by_email(email):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM admins WHERE email=?', (email,)).fetchone()
    conn.close()
    return row


def get_admin_by_id(admin_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM admins WHERE id=?', (admin_id,)).fetchone()
    conn.close()
    return row


# ── Timetable ─────────────────────────────────────────────────────────────────

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def add_timetable_entry(department, day_of_week, subject, instructor, room, start_time, end_time):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO timetable (department,day_of_week,subject,instructor,room,start_time,end_time) VALUES (?,?,?,?,?,?,?)',
        (department, day_of_week, subject, instructor, room, start_time, end_time)
    )
    conn.commit()
    conn.close()


def get_timetable(department=None):
    conn = get_db_connection()
    if department:
        rows = conn.execute(
            'SELECT * FROM timetable WHERE department=? ORDER BY day_of_week, start_time', (department,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM timetable ORDER BY department, day_of_week, start_time').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_timetable_entry(tid):
    conn = get_db_connection()
    conn.execute('DELETE FROM timetable WHERE id=?', (tid,))
    conn.commit()
    conn.close()


# ── Announcements ─────────────────────────────────────────────────────────────

def add_announcement(title, body, target='all'):
    conn = get_db_connection()
    conn.execute('INSERT INTO announcements (title,body,target) VALUES (?,?,?)', (title, body, target))
    conn.commit()
    conn.close()


def get_announcements(department=None):
    conn = get_db_connection()
    if department:
        rows = conn.execute(
            "SELECT * FROM announcements WHERE target='all' OR target=? ORDER BY created_at DESC",
            (department,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM announcements ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_announcement(aid):
    conn = get_db_connection()
    conn.execute('DELETE FROM announcements WHERE id=?', (aid,))
    conn.commit()
    conn.close()


# ── Student helpers ───────────────────────────────────────────────────────────

def get_student_streak(uid):
    """Count consecutive school days present (Mon-Fri)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DISTINCT DATE(timestamp) AS d FROM attendance WHERE user_id=? ORDER BY d DESC",
        (uid,)
    ).fetchall()
    conn.close()
    dates = {r['d'] for r in rows}
    streak = 0
    check = date.today()
    while True:
        if check.weekday() >= 5:
            check -= timedelta(days=1)
            continue
        if check.isoformat() in dates:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def get_student_notifications(uid, department):
    """Generate notification messages for a student."""
    notes = []
    summary = get_attendance_summary()
    s = next((x for x in summary if x['id'] == uid), None)
    if s:
        pct = s['percentage']
        if pct < 75:
            needed = 0
            remaining = s['total_days']
            # days needed to reach 75%
            present = s['present_days']
            for extra in range(1, 60):
                if round(((present + extra) / (remaining + extra)) * 100) >= 75:
                    needed = extra
                    break
            notes.append({'type': 'error', 'msg': f'Your attendance is {pct}%. You need {needed} more days to reach 75%.'})
        elif pct < 85:
            notes.append({'type': 'warning', 'msg': f'Attendance at {pct}%. Keep it up to stay above 75%.'})

    # Check if already marked today
    if already_marked_today(uid):
        notes.append({'type': 'success', 'msg': "You've already marked attendance today. ✅"})
    else:
        today_wd = date.today().weekday()
        if today_wd < 5:
            notes.append({'type': 'info', 'msg': "Don't forget to mark your attendance today."})

    return notes
