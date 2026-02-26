import sqlite3
import pickle
import os
from datetime import datetime

# Use /data directory if it exists (Render persistent disk), otherwise local
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

def add_user(user_id, name, department, features):
    conn = get_db_connection()
    # Serialize features (numpy array) to store in BLOB
    features_blob = pickle.dumps(features)
    cur = conn.cursor()
    cur.execute('INSERT INTO users (user_id, name, department, iris_features) VALUES (?, ?, ?, ?)',
                (user_id, name, department, features_blob))
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id

def get_all_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    
    user_list = []
    for user in users:
        # Deserialize features
        features = pickle.loads(user['iris_features'])
        user_list.append({
            'id': user['id'],
            'user_id': user['user_id'],
            'name': user['name'],
            'department': user['department'],
            'features': features
        })
    return user_list

def mark_attendance(user_id):
    conn = get_db_connection()
    # Check if already marked for today to avoid duplicate spam (optional, but good practice)
    # For simplicity, we just insert.
    cur = conn.cursor()
    cur.execute('INSERT INTO attendance (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_attendance_logs():
    conn = get_db_connection()
    query = '''
        SELECT a.id, u.name, u.user_id, a.timestamp
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
    '''
    logs = conn.execute(query).fetchall()
    conn.close()
    return logs
