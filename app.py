from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import init_db, add_user, mark_attendance, get_all_users, get_attendance_logs, DATABASE
from iris_recognition import decode_image, extract_features, verify_user
from email_service import send_attendance_email
import os

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

if not os.path.exists(DATABASE):
    print(" * Initializing database for the first time...")
    init_db()
else:
    print(" * Database already exists, skipping init.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    data = request.json
    user_id = data.get('user_id')
    name = data.get('name')
    department = data.get('department')
    parent_email = data.get('parent_email') or None
    image_data = data.get('image')
    
    if not user_id or not name or not department or not image_data:
        return jsonify({'success': False, 'message': 'Missing data'}), 400
        
    try:
        img = decode_image(image_data)
        features, annotated_img = extract_features(img, return_annotated=True)
        
        if features is None:
             return jsonify({'success': False, 'message': 'No eye features detected. Try again.'}), 400
             
        add_user(user_id, name, department, features, parent_email)
        return jsonify({
            'success': True, 
            'message': 'User registered successfully!',
            'annotated_image': annotated_img
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'GET':
        return render_template('attendance.html')
        
    data = request.json
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
        
    try:
        img = decode_image(image_data)
        captured_features, annotated_img = extract_features(img, return_annotated=True)
        
        users = get_all_users()
        matched_user, score = verify_user(captured_features, users)
        
        if matched_user:
            mark_attendance(matched_user['id'])

            # Send email to parent if one is on file (fire-and-forget)
            if matched_user.get('parent_email'):
                send_attendance_email(
                    parent_email=matched_user['parent_email'],
                    student_name=matched_user['name']
                )

            return jsonify({
                'success': True, 
                'message': f"Welcome, {matched_user['name']}!", 
                'user': matched_user['name'],
                'score': score,
                'annotated_image': annotated_img
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'No match found.', 
                'score': score,
                'annotated_image': annotated_img
            }), 404
            
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

@app.route('/admin')
def admin():
    logs = get_attendance_logs()
    return render_template('admin.html', logs=logs)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
