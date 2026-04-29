try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import re
import threading
import atexit
import calendar as cal_mod
from functools import wraps
from datetime import datetime, date, time as dtime, timedelta

import bcrypt
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash)
from flask_login import (LoginManager, UserMixin,
                         login_user, logout_user, login_required, current_user)

from database import (
    init_db, migrate_db,
    add_user, delete_user, get_user_by_id, get_user_by_user_id,
    get_all_users, get_all_students, get_student_count, get_all_departments,
    mark_attendance, already_marked_today,
    get_attendance_logs, get_attendance_by_user,
    get_absent_users, get_attendance_summary,
    get_chart_daily_trend, get_chart_department_stats, get_chart_today_summary,
    get_today_present_count,
    get_admin_by_email, get_admin_by_id,
    add_timetable_entry, get_timetable, delete_timetable_entry, DAYS,
    add_announcement, get_announcements, delete_announcement,
    get_student_streak, get_student_notifications,
    DATABASE,
)
from iris_recognition import decode_image, extract_features, verify_user
from email_service import send_attendance_email

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-production')

# ── Flask-Login (admin) ───────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.login_view = 'admin_login'
login_manager.init_app(app)


class AdminUser(UserMixin):
    def __init__(self, uid, email):
        self.id    = uid
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    admin = get_admin_by_id(int(user_id))
    return AdminUser(admin['id'], admin['email']) if admin else None


# ── Student session guard ─────────────────────────────────────────────────────

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'student_id' not in session:
            return redirect(url_for('student_login'))
        if current_student() is None:
            session.pop('student_id', None)
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated


def current_student():
    uid = session.get('student_id')
    if uid:
        row = get_user_by_id(uid)
        return dict(row) if row else None
    return None


# ── DB init ───────────────────────────────────────────────────────────────────

if not os.path.exists(DATABASE):
    init_db()
else:
    migrate_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

DUE_TIME_STR = os.environ.get('ATTENDANCE_DUE_TIME', '09:00')
_h, _m = map(int, DUE_TIME_STR.split(':'))
DUE_TIME = dtime(_h, _m)


def normalize_student_id(raw_id):
    """Strip non-alphanumeric characters and uppercase the student ID."""
    return re.sub(r'[^A-Za-z0-9]', '', raw_id).upper()


def attendance_status_now():
    return 'late' if datetime.now().time() > DUE_TIME else 'present'


def build_calendar(history, months_back=3):
    today    = date.today()
    date_map = {h['date']: h['status'] for h in history}
    months   = []
    for offset in range(months_back - 1, -1, -1):
        m, y = today.month - offset, today.year
        while m <= 0:
            m += 12; y -= 1
        _, days_in = cal_mod.monthrange(y, m)
        start_wd   = date(y, m, 1).weekday()
        flat       = [None] * start_wd
        for day_n in range(1, days_in + 1):
            d     = date(y, m, day_n)
            d_str = d.isoformat()
            if d > today:
                status = 'future'
            elif d.weekday() >= 5:
                # FIX: weekends are not school days — mark neutral,
                # not 'absent', so they don't show red on the calendar
                status = 'weekend'
            else:
                status = date_map.get(d_str, 'absent')
            flat.append({'day': day_n, 'date': d_str,
                         'status': status, 'is_today': d == today})
        while len(flat) % 7:
            flat.append(None)
        months.append({
            'name':  date(y, m, 1).strftime('%B %Y'),
            'weeks': [flat[i:i+7] for i in range(0, len(flat), 7)],
        })
    return months


# ── Absence scheduler ─────────────────────────────────────────────────────────

def _send_absence_notifications():
    today_str = date.today().isoformat()
    for user in get_absent_users(today_str):
        threading.Thread(
            target=send_attendance_email,
            args=(user['parent_email'], user['name']),
            kwargs={'status': 'absent'}, daemon=True,
        ).start()


def _start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    s = BackgroundScheduler(daemon=True)
    s.add_job(_send_absence_notifications, 'cron', hour=_h, minute=_m)
    s.start()
    atexit.register(lambda: s.shutdown(wait=False))


if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    try:
        _start_scheduler()
    except Exception as e:
        print(f" * Scheduler error: {e}")


# ════════════════════════════════════════════════════════════════════════════
#  PUBLIC
# ════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Auth
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        admin    = get_admin_by_email(email)
        if admin and bcrypt.checkpw(password.encode(), admin['password'].encode()):
            login_user(AdminUser(admin['id'], admin['email']), remember=True)
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid email or password.'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Dashboard
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
@login_required
def admin_dashboard():
    summary        = get_attendance_summary()
    at_risk        = [s for s in summary if s['percentage'] < 75]
    trend          = get_chart_daily_trend(30)
    dept_stats     = get_chart_department_stats()
    today_summary  = get_chart_today_summary()
    recent         = get_attendance_logs(limit=8)
    announcements  = get_announcements()
    return render_template('admin/dashboard.html',
        total_students  = get_student_count(),
        today_present   = get_today_present_count(),
        total_depts     = len(get_all_departments()),
        at_risk_count   = len(at_risk),
        at_risk         = at_risk[:5],
        trend           = trend,
        dept_stats      = dept_stats,
        today_summary   = today_summary,
        recent          = recent,
        announcements   = announcements[:3],
    )


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Register Student (with iris)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/register', methods=['GET', 'POST'])
@login_required
def admin_register():
    if request.method == 'GET':
        return render_template('admin/register.html')

    data         = request.json or {}
    user_id      = normalize_student_id((data.get('user_id') or '').strip())
    name         = (data.get('name')    or '').strip()
    department   = (data.get('department') or '').strip()
    parent_email = (data.get('parent_email') or '').strip() or None
    password     = (data.get('password') or '').strip()
    image_data   = data.get('image')

    if not all([user_id, name, department, password, image_data]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400

    if get_user_by_user_id(user_id):
        return jsonify({'success': False, 'message': f'Student ID "{user_id}" is already registered.'}), 400

    try:
        img = decode_image(image_data)
        features, annotated = extract_features(img, return_annotated=True)

        if features is None:
            return jsonify({'success': False, 'message': 'No iris detected. Please ensure the student is looking at the camera.'}), 400

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        add_user(user_id, name, department, features, parent_email, hashed)
        return jsonify({'success': True, 'message': f'{name} registered successfully! (ID: {user_id})',
                        'annotated_image': annotated})
    except Exception as e:
        print(f"Register error: {e}")
        return jsonify({'success': False, 'message': 'Server error. Please try again.'}), 500


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Students
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/students')
@login_required
def admin_students():
    summary  = get_attendance_summary()
    pct_map  = {s['id']: s['percentage'] for s in summary}
    students = get_all_students()
    for s in students:
        s['percentage'] = pct_map.get(s['id'], 0)
    return render_template('admin/students.html', students=students,
                           departments=get_all_departments())


@app.route('/admin/student/<int:uid>')
@login_required
def admin_student_detail(uid):
    user     = get_user_by_id(uid)
    if not user:
        return 'Not found', 404
    history  = get_attendance_by_user(uid)
    calendar = build_calendar(history, months_back=3)
    summary  = get_attendance_summary()
    user_sum = next((s for s in summary if s['id'] == uid), None)
    present  = sum(1 for h in history if h['status'] == 'present')
    late     = sum(1 for h in history if h['status'] == 'late')
    return render_template('admin/student_detail.html',
        user=user, history=history, calendar=calendar,
        user_sum=user_sum, present=present, late=late, total=present+late)


@app.route('/admin/delete-student/<int:uid>', methods=['POST'])
@login_required
def admin_delete_student(uid):
    try:
        delete_user(uid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Attendance Logs
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/attendance')
@login_required
def admin_attendance():
    active_depts = request.args.getlist('dept')
    date_from    = request.args.get('from', '')
    date_to      = request.args.get('to', '')
    logs         = get_attendance_logs(
        departments = active_depts or None,
        date_from   = date_from or None,
        date_to     = date_to   or None,
    )
    at_risk = [s for s in get_attendance_summary() if s['percentage'] < 75]
    return render_template('admin/attendance.html',
        logs=logs, all_depts=get_all_departments(),
        active_depts=active_depts, at_risk=at_risk,
        date_from=date_from, date_to=date_to)


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Timetable
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/timetable', methods=['GET'])
@login_required
def admin_timetable():
    filter_dept = request.args.get('dept', '')
    entries     = get_timetable(filter_dept or None)
    grouped = {}
    for e in entries:
        d = e['department']
        day = DAYS[e['day_of_week']]
        grouped.setdefault(d, {}).setdefault(day, []).append(e)
    return render_template('admin/timetable.html',
        grouped=grouped, entries=entries,
        departments=get_all_departments(), days=DAYS,
        filter_dept=filter_dept)


@app.route('/admin/timetable/add', methods=['POST'])
@login_required
def admin_timetable_add():
    data = request.json or {}
    try:
        add_timetable_entry(
            data['department'], int(data['day_of_week']),
            data['subject'], data.get('instructor', ''),
            data.get('room', ''), data['start_time'], data['end_time']
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/admin/timetable/delete/<int:tid>', methods=['POST'])
@login_required
def admin_timetable_delete(tid):
    delete_timetable_entry(tid)
    return jsonify({'success': True})


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN — Announcements
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/announcements', methods=['GET'])
@login_required
def admin_announcements():
    return render_template('admin/announcements.html',
        announcements=get_announcements(),
        departments=get_all_departments())


@app.route('/admin/announcements/add', methods=['POST'])
@login_required
def admin_announcements_add():
    data = request.json or {}
    title  = (data.get('title') or '').strip()
    body   = (data.get('body')  or '').strip()
    target = (data.get('target') or 'all').strip()
    if not title or not body:
        return jsonify({'success': False, 'message': 'Title and body required.'}), 400
    add_announcement(title, body, target)
    return jsonify({'success': True})


@app.route('/admin/announcements/delete/<int:aid>', methods=['POST'])
@login_required
def admin_announcements_delete(aid):
    delete_announcement(aid)
    return jsonify({'success': True})


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Auth
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if 'student_id' in session:
        return redirect(url_for('student_dashboard'))
    error = None
    if request.method == 'POST':
        uid      = normalize_student_id(request.form.get('user_id', ''))
        password = request.form.get('password', '')
        user     = get_user_by_user_id(uid)
        if user and user['password'] and bcrypt.checkpw(password.encode(), user['password'].encode()):
            session['student_id'] = user['id']
            return redirect(url_for('student_dashboard'))
        error = 'Invalid Student ID or password.'
    return render_template('student/login.html', error=error)


@app.route('/student/logout')
def student_logout():
    session.pop('student_id', None)
    return redirect(url_for('student_login'))


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Dashboard
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    student  = current_student()
    dept     = student['department']
    uid      = student['id']
    summary  = get_attendance_summary()
    user_sum = next((s for s in summary if s['id'] == uid), None)
    streak   = get_student_streak(uid)
    notes    = get_student_notifications(uid, dept)
    today_tt = [e for e in get_timetable(dept)
                if e['day_of_week'] == date.today().weekday()]
    today_tt.sort(key=lambda x: x['start_time'])
    announcements = get_announcements(dept)[:3]
    marked_today  = already_marked_today(uid)
    return render_template('student/dashboard.html',
        student=student, user_sum=user_sum, streak=streak,
        notifications=notes, today_tt=today_tt,
        announcements=announcements, marked_today=marked_today,
        today=date.today().strftime('%A, %B %d %Y'))


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Mark Attendance
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/attendance', methods=['GET'])
@student_required
def student_attendance():
    student      = current_student()
    marked_today = already_marked_today(student['id'])
    return render_template('student/mark_attendance.html',
                           student=student, marked_today=marked_today)


@app.route('/student/mark-attendance', methods=['POST'])
@student_required
def student_mark_attendance():
    student    = current_student()
    data       = request.json or {}
    image_data = data.get('image')

    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided.'}), 400

    if already_marked_today(student['id']):
        return jsonify({'success': False, 'message': 'You have already marked attendance today.'}), 400

    try:
        img = decode_image(image_data)
        captured, annotated = extract_features(img, return_annotated=True)

        if captured is None:
            return jsonify({'success': False,
                            'message': 'No iris detected. Please look directly at the camera.',
                            'annotated_image': annotated}), 400

        user_dict = {
            'id':           student['id'],
            'user_id':      student['user_id'],
            'name':         student['name'],
            'department':   student['department'],
            'parent_email': student['parent_email'],
            'features':     __import__('pickle').loads(student['iris_features']),
        }
        matched, score = verify_user(captured, [user_dict])

        if matched and matched['id'] == student['id']:
            status = attendance_status_now()
            mark_attendance(student['id'], status)

            if student['parent_email']:
                threading.Thread(
                    target=send_attendance_email,
                    args=(student['parent_email'], student['name']),
                    kwargs={'status': status}, daemon=True,
                ).start()

            label = 'Late arrival' if status == 'late' else 'Attendance marked'
            return jsonify({'success': True, 'message': f'{label} successfully!',
                            'status': status, 'annotated_image': annotated})
        else:
            return jsonify({'success': False,
                            'message': 'Iris did not match. Please try again.',
                            'annotated_image': annotated}), 401

    except Exception as e:
        print(f"Attendance error: {e}")
        return jsonify({'success': False, 'message': 'Server error.'}), 500


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Calendar
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/calendar')
@student_required
def student_calendar():
    student  = current_student()
    history  = get_attendance_by_user(student['id'])
    calendar = build_calendar(history, months_back=3)
    summary  = get_attendance_summary()
    user_sum = next((s for s in summary if s['id'] == student['id']), None)
    present  = sum(1 for h in history if h['status'] == 'present')
    late     = sum(1 for h in history if h['status'] == 'late')
    return render_template('student/calendar.html',
        student=student, calendar=calendar,
        user_sum=user_sum, history=history,
        present=present, late=late, total=present+late)


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Timetable
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/timetable')
@student_required
def student_timetable():
    student = current_student()
    entries = get_timetable(student['department'])
    by_day = {day: [] for day in DAYS[:5]}
    for e in entries:
        day_name = DAYS[e['day_of_week']]
        if day_name in by_day:
            by_day[day_name].append(e)
    for day in by_day:
        by_day[day].sort(key=lambda x: x['start_time'])
    today_name = DAYS[date.today().weekday()] if date.today().weekday() < 5 else None
    return render_template('student/timetable.html',
        student=student, by_day=by_day, days=DAYS[:5], today_name=today_name)


# ════════════════════════════════════════════════════════════════════════════
#  STUDENT — Announcements
# ════════════════════════════════════════════════════════════════════════════

@app.route('/student/announcements')
@student_required
def student_announcements():
    student = current_student()
    return render_template('student/announcements.html',
        student=student,
        announcements=get_announcements(student['department']))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)