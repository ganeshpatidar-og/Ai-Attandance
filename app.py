import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from insightface.app import FaceAnalysis
import numpy as np
import pandas as pd
import base64
import os
import cv2
from io import BytesIO
from connection import conn


app = Flask(__name__)
app.secret_key = 'your_secret_key'

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")
# buffalo_l includes models for detection (det_10g.onnx), landmark detection (1k3d68.onnx and 2d106det.onnx),
# face recognition (w600k_r50.onnx), and optionally gender/age prediction.
# These work together to detect, align, and recognize faces."
# Load InsightFace face analysis model
face_app = FaceAnalysis(name='buffalo_s', providers=['CPUExecutionProvider'])  # Change to 'cuda' if you have GPU
face_app.prepare(ctx_id=0)
# Initialize the InsightFace app globally
insightface_app = FaceAnalysis(name='buffalo_l')
insightface_app.prepare(ctx_id=0, det_size=(640, 640))  # Prepare the model (ctx_id=0 for CPU)

# Load known faces and names
known_faces = []
known_names = []

def load_known_faces():
    global known_faces, known_names
    results = conn.read("SELECT students.enrollment_no, face_encodings.encoding FROM face_encodings JOIN students ON face_encodings.student_id = students.id")
    for enrollment_no, encoding in results:
        encoding = np.frombuffer(base64.b64decode(encoding), dtype=np.float32)
        known_faces.append(encoding)
        known_names.append(enrollment_no)

load_known_faces()

def load_known_faces():
    known_faces = []
    known_names = []
    results = conn.read("SELECT students.enrollment_no, face_encodings.encoding FROM face_encodings JOIN students ON face_encodings.student_id = students.id")
    for enrollment_no, encoding in results:
        emb_array = np.frombuffer(base64.b64decode(encoding), dtype=np.float32)
        if emb_array.shape[0] == 512:  # Very important!
            known_faces.append(emb_array)
            known_names.append(enrollment_no)
    return known_faces, known_names

def save_insightface_embedding(student_id, image):
    faces = insightface_app.get(image)
    if faces:
        embedding = faces[0].embedding.astype(np.float32)
        encoded = base64.b64encode(embedding.tobytes()).decode('utf-8')
        conn.insert("INSERT INTO face_encodings (student_id, encoding) VALUES (%s, %s)", (student_id, encoded))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def mark_attendance(student_id):
    try:
        current_time = datetime.datetime.now().strftime('%H:%M:%S')
        exists = conn.read("SELECT * FROM attendance WHERE student_id = %s AND date = CURDATE()", (student_id,))
        if len(exists) == 0:
            conn.insert('INSERT INTO attendance (student_id, time, date) VALUES (%s, %s, CURDATE())',
                        (student_id, current_time))
    except Exception as e:
        print(f"Error marking attendance: {e}")

def identify_person():
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("Error: Could not open camera.")
        return

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Detect faces using InsightFace
        faces = face_app.get(frame)

        recognized_names = []
        for face in faces:
            embedding = face.embedding
            name = "Unknown"
            best_score = 0
            best_match = None

            for db_embedding, enrollment_no in zip(known_faces, known_names):
                sim = cosine_similarity(embedding, db_embedding)
                if sim > best_score:
                    best_score = sim
                    best_match = enrollment_no

            if best_score > 0.7 :  # Adjustable threshold
                name = best_match
                recognized_names.append(name)

            if recognized_names:
                for name in recognized_names:
                    print(f"Marking attendance for: {name}")
                    mark_attendance(name)

            # Draw bounding box
            bbox = [int(coord) for coord in face.bbox]
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, name, (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv2.imshow('Camera', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

@app.route('/')
def home():
    """
    Home page with options for admin login, student login, and registration.
    """
    return render_template('home.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login page.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password", "error")
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/admin_dashboard')
def admin_dashboard():
    """
    Admin dashboard.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    response = make_response(render_template('admin_dashboard.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response
    # return render_template('admin_dashboard.html')


@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        class_section = request.form['class_section']
        year = request.form['year']
        semester = request.form['semester']
        dob = request.form['dob']
        enrollment_no = request.form['enrollment_no']
        photo = request.files['photo']

        # Save the photo
        os.makedirs('static/faces', exist_ok=True)
        image_path = os.path.join('static/faces', f"{name}_{enrollment_no}.jpg")
        photo.save(image_path)

        # Save student details to the database
        student_id = conn.insert(
            'INSERT INTO students (name, mobile, class_section, year, semester, dob, enrollment_no, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (name, mobile, class_section, year, semester, dob, enrollment_no, image_path)
        )

        # Load image using OpenCV (InsightFace uses BGR format)
        image = cv2.imread(image_path)

        # Detect face and extract embedding
        faces = insightface_app.get(image)
        if faces:
            embedding = faces[0].embedding.astype(np.float32)
            encoding = base64.b64encode(embedding.tobytes()).decode('utf-8')
            print("Student ID:", student_id)
            print("Encoding:", encoding[:30])  # Print the first 30 characters of the encoding to verify

            # Save encoding to DB
            conn.insert('INSERT INTO face_encodings (student_id, encoding) VALUES (%s, %s)', (student_id, encoding))
        else:
            flash("Face not detected. Please upload a clear front-facing image.", "danger")
            # Optionally delete the student entry if no face is found
            conn.execute("DELETE FROM students WHERE id = %s", (student_id,))
            return redirect(url_for('register_student'))

        flash("Registration request submitted. Waiting for admin approval.", "success")
        return redirect(url_for('home'))

    return render_template('register_student.html')

@app.route('/take_attendance')
def take_attendance():
    """
    Take attendance using face recognition.
    """
    identify_person()
    return redirect(url_for('home'))

# @app.route('/view_attendance')
@app.route('/view_attendance', methods=['GET'])
def view_attendance():
    """
    View attendance records by date or name.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Get query parameters
    date = request.args.get('date', datetime.datetime.today().strftime('%Y-%m-%d'))
    name = request.args.get('name', '')

    # Validate date format
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD.", 400

    # Build SQL query
    query = """
        SELECT students.name, students.enrollment_no, attendance.date, attendance.time
        FROM attendance
        JOIN students ON attendance.student_id = students.enrollment_no
        WHERE 1=1
    """
    params = []

    if date:
        query += " AND attendance.date = %s"
        params.append(date)
    if name:
        query += " AND students.name LIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY students.name ASC, attendance.date DESC, attendance.time DESC"

    # Execute query using the existing connection
    try:
        attendance_records = conn.read(query, params)
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

    return render_template('view_attendance.html', attendance_records=attendance_records, datetime=datetime, date = date,timedelta=datetime.timedelta, name=name)

@app.route('/export_attendance', methods=['GET'])
def export_attendance():
    """
    Export attendance records to an Excel file.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    date = request.args.get('date', datetime.datetime.today().strftime('%Y-%m-%d'))
    name = request.args.get('name', '')

    query = """
        SELECT students.name, students.enrollment_no, attendance.date, attendance.time
        FROM attendance
        JOIN students ON attendance.student_id = students.enrollment_no
        WHERE 1=1
    """
    params = []

    if date:
        query += " AND attendance.date = %s"
        params.append(date)
    if name:
        query += " AND students.name LIKE %s"
        params.append(f"%{name}%")

    query += " ORDER BY students.name ASC, attendance.date DESC, attendance.time DESC"

    attendance_records = conn.read(query, params)

    # Create a DataFrame
    df = pd.DataFrame(attendance_records, columns=['Name', 'Enrollment No', 'Date', 'Time'])

    # Export to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')
    output.seek(0)

    return send_file(output, download_name='attendance.xlsx', as_attachment=True)
@app.route('/approve_students')
def approve_students():
    """
    Approve pending student registrations.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    results = conn.read("SELECT * FROM students WHERE approved = FALSE")
    return render_template('approve_students.html', students=results)

@app.route('/student_list')
def student_list():
    """
    Approve pending student registrations.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    results = conn.read("SELECT * FROM students WHERE approved = TRUE")
    return render_template('student_list.html', students=results)

@app.route('/approve_student/<int:student_id>')
def approve_student(student_id):
    """
    Approve a specific student registration.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    conn.insert("UPDATE students SET approved = TRUE WHERE id = %s", (student_id,))
    flash("Student approved successfully!", "success")
    return redirect(url_for('approve_students'))

@app.route('/delete_student/<int:student_id>')
def delete_student(student_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    conn.insert("delete from students where id = %s", (student_id,))
    flash("Student Deleted successfully!", "success")
    return redirect(url_for('approve_students'))

@app.route('/logout')
def logout():
    """
    Log out the current user.
    """
    session.pop('admin_logged_in', None)
    session.pop('student_logged_in', None)
    session.pop('student_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)