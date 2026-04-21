try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import pickle
import threading
import atexit
import calendar as cal_module
from datetime import datetime, date, time as dtime

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, flash)
from flask_login import (LoginManager, UserMixin,
                         login_user, logout_user,
                         login_required, current_user)
import bcrypt

from database import (
    init_db, migrate_db,
    add_user, delete_user, get_user_by_id, get_all_users,
    get_all_departments,
    mark_attendance, get_attendance_logs,
    get_attendance_by_user, get_absent_users, get_attendance_summary,
    get_admin_by_email, get_admin_by_id,
    DATABASE, get_db_connection
)
from iris_recognition import decode_image, extract_features, verify_user
from email_service import send_attendance_email

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production')

# ── Flask-Login ───────────────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin panel.'
login_manager.login_message_category = 'error'
login_manager.init_app(app)


class AdminUser(UserMixin):
    def __init__(self, uid, email):
        self.id  = uid
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    admin = get_admin_by_id(int(user_id))
    if admin:
        return AdminUser(admin['id'], admin['email'])
    return None


# ── Database init ─────────────────────────────────────────────────────────────

if not os.path.exists(DATABASE):
    print(" * Initialising database for the first time...")
    init_db()
else:
    print(" * Database exists — running migrations...")
    migrate_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

DUE_TIME_STR = os.environ.get('ATTENDANCE_DUE_TIME', '09:00')
_due_h, _due_m = map(int, DUE_TIME_STR.split(':'))
DUE_TIME = dtime(_due_h, _due_m)


def _attendance_status_now():
    return 'late' if datetime.now().time() > DUE_TIME else 'present'


def build_calendar(history, months_back=3):
    """Return a list of month dicts suitable for the calendar template."""
    today     = date.today()
    date_map  = {h['date']: h['status'] for h in history}
    months    = []

    for offset in range(months_back - 1, -1, -1):
        m = today.month - offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1

        _, days_in_month = cal_module.monthrange(y, m)
        start_wd = date(y, m, 1).weekday()  # 0 = Monday

        flat = [None] * start_wd
        for day_num in range(1, days_in_month + 1):
            d     = date(y, m, day_num)
            d_str = d.isoformat()
            if d > today:
                status = 'future'
            else:
                status = date_map.get(d_str, 'absent')
            flat.append({
                'day':      day_num,
                'date':     d_str,
                'status':   status,
                'is_today': d == today,
            })

        while len(flat) % 7:
            flat.append(None)

        weeks = [flat[i:i + 7] for i in range(0, len(flat), 7)]
        months.append({
            'name':  date(y, m, 1).strftime('%B %Y'),
            'weeks': weeks,
        })

    return months


# ── Absence scheduler ─────────────────────────────────────────────────────────

def _send_absence_notifications():
    today_str = date.today().isoformat()
    absent    = get_absent_users(today_str)
    print(f" * Absence check: {len(absent)} absent user(s) with parent email.")
    for user in absent:
        threading.Thread(
            target=send_attendance_email,
            args=(user['parent_email'], user['name']),
            kwargs={'status': 'absent'},
            daemon=True,
        ).start()


def _start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _send_absence_notifications, 'cron',
        hour=_due_h, minute=_due_m,
        id='absence_check'
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    print(f" * Absence scheduler started — notifications at {DUE_TIME_STR}.")


# Only start scheduler in the main process (avoids double-start with reloader)
if os.environ.get('WERKZEUG_RUN_MAIN', 'false') == 'true' or not app.debug:
    try:
        _start_scheduler()
    except Exception as e:
        print(f" * Scheduler failed to start: {e}")


# ── Public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    data         = request.json
    user_id      = data.get('user_id')
    name         = data.get('name')
    department   = data.get('department')
    parent_email = data.get('parent_email') or None
    image_data   = data.get('image')

    if not user_id or not name or not department or not image_data:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    try:
        img = decode_image(image_data)
        features, annotated_img = extract_features(img, return_annotated=True)
        if features is None:
            return jsonify({'success': False,
                            'message': 'No eye features detected. Try again.'}), 400
        add_user(user_id, name, department, features, parent_email)
        return jsonify({
            'success':          True,
            'message':          'User registered successfully!',
            'annotated_image':  annotated_img,
        })
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500


@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'GET':
        return render_template('attendance.html')

    data       = request.json
    image_data = data.get('image')
    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    try:
        img = decode_image(image_data)
        captured_features, annotated_img = extract_features(img, return_annotated=True)
        users = get_all_users()
        matched_user, score = verify_user(captured_features, users)

        if matched_user:
            status = _attendance_status_now()
            mark_attendance(matched_user['id'], status)

            if matched_user.get('parent_email'):
                threading.Thread(
                    target=send_attendance_email,
                    args=(matched_user['parent_email'], matched_user['name']),
                    kwargs={'status': status},
                    daemon=True,
                ).start()

            label   = 'Late arrival' if status == 'late' else 'Welcome'
            message = f"{label}, {matched_user['name']}!"
            return jsonify({
                'success':         True,
                'message':         message,
                'user':            matched_user['name'],
                'status':          status,
                'score':           score,
                'annotated_image': annotated_img,
            })
        else:
            return jsonify({
                'success':         False,
                'message':         'No match found.',
                'score':           score,
                'annotated_image': annotated_img,
            }), 404

    except Exception as e:
        print(f"Attendance error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500


# ── Admin login ───────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin'))

    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        admin    = get_admin_by_email(email)

        if admin and bcrypt.checkpw(password.encode('utf-8'),
                                    admin['password'].encode('utf-8')):
            login_user(AdminUser(admin['id'], admin['email']), remember=True)
            return redirect(url_for('admin'))

        error = 'Invalid email or password.'

    return render_template('admin_login.html', error=error)


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


# ── Admin dashboard ───────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin():
    active_depts  = request.args.getlist('dept')
    logs          = get_attendance_logs(active_depts if active_depts else None)
    all_depts     = get_all_departments()
    summary       = get_attendance_summary()
    at_risk       = [s for s in summary if s['percentage'] < 75]
    return render_template(
        'admin.html',
        logs=logs,
        all_depts=all_depts,
        active_depts=active_depts,
        at_risk=at_risk,
        summary=summary,
    )


@app.route('/admin/add-student', methods=['POST'])
@login_required
def add_student():
    data = request.json or {}
    uid     = (data.get('user_id') or '').strip()
    name    = (data.get('name')    or '').strip()
    dept    = (data.get('department') or '').strip()
    email   = (data.get('parent_email') or '').strip() or None

    if not uid or not name or not dept:
        return jsonify({'success': False, 'message': 'ID, name, and department are required.'}), 400

    try:
        empty_blob = pickle.dumps(None)
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (user_id, name, department, parent_email, iris_features) VALUES (?, ?, ?, ?, ?)',
            (uid, name, dept, email, empty_blob)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'{name} added successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/admin/delete-student/<int:uid>', methods=['POST'])
@login_required
def admin_delete_student(uid):
    try:
        delete_user(uid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/admin/student/<int:uid>')
@login_required
def student_detail(uid):
    user = get_user_by_id(uid)
    if not user:
        return 'Student not found.', 404
    history   = get_attendance_by_user(uid)
    calendar  = build_calendar(history, months_back=3)
    present   = sum(1 for h in history if h['status'] == 'present')
    late      = sum(1 for h in history if h['status'] == 'late')
    total     = present + late
    summary   = get_attendance_summary()
    user_sum  = next((s for s in summary if s['id'] == uid), None)
    return render_template(
        'student_detail.html',
        user=user,
        history=history,
        calendar=calendar,
        present=present,
        late=late,
        total=total,
        user_sum=user_sum,
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)