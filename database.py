import sqlite3
import pickle
import os
from datetime import datetime, date

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
    """Run safe migrations on an existing database."""
    conn = get_db_connection()

    # Add status column to attendance if missing
    try:
        conn.execute("ALTER TABLE attendance ADD COLUMN status TEXT DEFAULT 'present'")
        conn.commit()
        print(" * Migration: added 'status' column to attendance.")
    except Exception:
        pass

    # Create admins table if missing
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


# ── Users ────────────────────────────────────────────────────────────────────

def add_user(user_id, name, department, features, parent_email=None):
    conn = get_db_connection()
    features_blob = pickle.dumps(features)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO users (user_id, name, department, parent_email, iris_features) VALUES (?, ?, ?, ?, ?)',
        (user_id, name, department, parent_email, features_blob)
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def delete_user(uid):
    """Delete a user and all their attendance records."""
    conn = get_db_connection()
    conn.execute('DELETE FROM attendance WHERE user_id = ?', (uid,))
    conn.execute('DELETE FROM users WHERE id = ?', (uid,))
    conn.commit()
    conn.close()


def get_user_by_id(uid):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    conn.close()
    return user


def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    result = []
    for user in users:
        features = pickle.loads(user['iris_features'])
        result.append({
            'id': user['id'],
            'user_id': user['user_id'],
            'name': user['name'],
            'department': user['department'],
            'parent_email': user['parent_email'],
            'features': features
        })
    return result


def get_all_departments():
    conn = get_db_connection()
    rows = conn.execute('SELECT DISTINCT department FROM users ORDER BY department').fetchall()
    conn.close()
    return [r['department'] for r in rows]


# ── Attendance ────────────────────────────────────────────────────────────────

def mark_attendance(user_id, status='present'):
    conn = get_db_connection()
    conn.execute('INSERT INTO attendance (user_id, status) VALUES (?, ?)', (user_id, status))
    conn.commit()
    conn.close()


def get_attendance_logs(departments=None):
    conn = get_db_connection()
    query = '''
        SELECT a.id, u.id AS uid, u.name, u.user_id, u.department,
               a.timestamp, a.status
        FROM attendance a
        JOIN users u ON a.user_id = u.id
    '''
    params = []
    if departments:
        placeholders = ','.join('?' * len(departments))
        query += f' WHERE u.department IN ({placeholders})'
        params = list(departments)
    query += ' ORDER BY a.timestamp DESC'
    logs = conn.execute(query, params).fetchall()
    conn.close()
    return logs


def get_attendance_by_user(uid):
    """Return all attendance rows for one user, newest first."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT DATE(timestamp) AS date, status FROM attendance WHERE user_id = ? ORDER BY timestamp DESC",
        (uid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_absent_users(date_str):
    """Return users with a parent_email who have no attendance record on date_str."""
    conn = get_db_connection()
    query = '''
        SELECT id, name, parent_email, department
        FROM users
        WHERE parent_email IS NOT NULL AND parent_email != ''
          AND id NOT IN (
              SELECT user_id FROM attendance WHERE DATE(timestamp) = ?
          )
    '''
    rows = conn.execute(query, (date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_summary():
    """Return per-user attendance percentage since enrolment."""
    conn = get_db_connection()
    query = '''
        SELECT u.id, u.user_id, u.name, u.department, u.created_at,
               COUNT(DISTINCT DATE(a.timestamp)) AS present_days
        FROM users u
        LEFT JOIN attendance a ON u.id = a.user_id
        GROUP BY u.id
        ORDER BY u.name
    '''
    rows = conn.execute(query).fetchall()
    conn.close()

    today = date.today()
    summary = []
    for row in rows:
        r = dict(row)
        created_str = r['created_at'][:10]
        try:
            created = datetime.strptime(created_str, '%Y-%m-%d').date()
        except Exception:
            created = today
        total_days = max((today - created).days, 1)
        present = r['present_days'] or 0
        r['percentage'] = min(round((present / total_days) * 100), 100)
        r['total_days'] = total_days
        summary.append(r)
    return summary


# ── Admins ────────────────────────────────────────────────────────────────────

def get_admin_by_email(email):
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admins WHERE email = ?', (email,)).fetchone()
    conn.close()
    return admin


def get_admin_by_id(admin_id):
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM admins WHERE id = ?', (admin_id,)).fetchone()
    conn.close()
    return admin