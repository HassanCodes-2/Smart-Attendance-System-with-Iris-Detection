"""
Run once to create the first admin account.

    python seed_admin.py

You will be prompted for an email and password.
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sqlite3
import bcrypt
import getpass
from database import DATABASE, init_db, migrate_db
import os

if not os.path.exists(DATABASE):
    init_db()
else:
    migrate_db()

print("=== IrisSecure — Create Admin Account ===\n")
email    = input("Admin email: ").strip()
password = getpass.getpass("Password:   ")
confirm  = getpass.getpass("Confirm:    ")

if not email or not password:
    print("Email and password cannot be empty.")
    exit(1)

if password != confirm:
    print("Passwords do not match.")
    exit(1)

hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

conn = sqlite3.connect(DATABASE)
try:
    conn.execute(
        'INSERT INTO admins (email, password) VALUES (?, ?)',
        (email, hashed)
    )
    conn.commit()
    print(f"\n✅  Admin account created for {email}")
    print("    You can now log in at /admin/login")
except sqlite3.IntegrityError:
    print(f"\n⚠️   An admin with email '{email}' already exists.")
finally:
    conn.close()
