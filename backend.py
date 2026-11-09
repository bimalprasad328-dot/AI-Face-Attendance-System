# AI Face Attendance System Backend Processor (SQLite + Auth edition)
import os
import sys
import cv2
import subprocess
import threading
import sqlite3
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import face_recognition
from groq import Groq
from datetime import datetime
from dotenv import load_dotenv

from auth import auth_bp, login_required, role_required, get_db, DB_PATH

# Load .env FIRST so every os.environ lookup below can see it
load_dotenv()

app = Flask(__name__)

# Secret key comes from .env (SECRET_KEY=...). No hardcoded fallback.
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise ValueError("SECRET_KEY not found. Add SECRET_KEY=your_key to your .env file")

# supports_credentials=True is required so the session cookie survives
# cross-origin requests from the frontend (credentials: 'include')
CORS(app, supports_credentials=True)

app.register_blueprint(auth_bp)

# Initialize Groq Client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Add GROQ_API_KEY=your_key to your .env file")
groq_client = Groq(api_key=GROQ_API_KEY)

DATASET_DIR = "dataset"

if not os.path.exists(DB_PATH):
    raise RuntimeError(
        f"{DB_PATH} not found. Run migrate_to_sqlite.py first to create the database."
    )


def load_known_faces():
    known_encodings, known_names = [], []
    if not os.path.exists(DATASET_DIR):
        return known_encodings, known_names
    for student_name in os.listdir(DATASET_DIR):
        student_folder = os.path.join(DATASET_DIR, student_name)
        if os.path.isdir(student_folder):
            for img_name in os.listdir(student_folder):
                try:
                    image = face_recognition.load_image_file(os.path.join(student_folder, img_name))
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        known_encodings.append(encodings[0])
                        known_names.append(student_name)
                except Exception:
                    continue
    return known_encodings, known_names


known_face_encodings, known_face_names = load_known_faces()


def synchronize_absentees():
    """Scans ALL student records against today's logs and inserts Absent rows
    for anyone missing. Runs globally regardless of who's logged in -
    role-based filtering only happens when DATA IS READ, not when it's written."""
    conn = get_db()
    today_str = datetime.now().strftime("%Y-%m-%d")

    students = conn.execute("SELECT name, reg_no FROM students").fetchall()
    if not students:
        conn.close()
        return

    today_logs = conn.execute(
        "SELECT reg_no, name, status FROM attendance WHERE timestamp LIKE ?",
        (f"{today_str}%",)
    ).fetchall()

    present_names = {row["name"] for row in today_logs if row["status"] == "Present"}
    already_absent_names = {row["name"] for row in today_logs if row["status"] == "Absent"}

    for student in students:
        name = student["name"]
        reg_no = student["reg_no"]

        if name in present_names:
            # remove any stray Absent row for someone who is actually present
            conn.execute(
                """DELETE FROM attendance
                   WHERE name = ? AND status = 'Absent' AND timestamp LIKE ?""",
                (name, f"{today_str}%")
            )
        elif name not in already_absent_names:
            conn.execute(
                """INSERT INTO attendance (reg_no, name, timestamp, status)
                   VALUES (?, ?, ?, ?)""",
                (reg_no, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Absent")
            )

    conn.commit()
    conn.close()


def generate_ai_insight(s_df, a_df):
    """Feeds the active student/attendance tables straight to Groq for automated insights."""
    if s_df.empty:
        return "Waiting for enrollment data indexes to generate automated insights..."

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = a_df[a_df["Timestamp"].astype(str).str.startswith(today_str)] if not a_df.empty else a_df

    prompt_context = f"""
    Analyze the following university classroom attendance context matrices:
    Master Student Registry:
    {s_df.to_string()}

    Today's Recorded Log Statuses ({today_str}):
    {today_logs.to_string()}

    Task: Write a single, brief sentence summarizing today's attendance metrics or trends (e.g., who is missing, overall attendance rate, or if everyone arrived safely). Keep it concise, natural, and under 25 words.
    """
    try:
        completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You are an automated background analytics engine. Output only your one-sentence summary."},
                {"role": "user", "content": prompt_context}
            ],
            max_tokens=60,
            temperature=0.3
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return "AI Insight Engine currently computing analytical trends..."


def _scope_query(base_students_sql, base_attendance_sql):
    """Returns (students_sql, students_params, attendance_sql, attendance_params)
    scoped to the logged-in user's role. Admin sees everything, teacher sees
    only their own students/records."""
    if session["role"] == "admin":
        return base_students_sql, (), base_attendance_sql, ()
    else:
        return (
            base_students_sql + " WHERE teacher_id = ?", (session["user_id"],),
            base_attendance_sql + """
                WHERE reg_no IN (SELECT reg_no FROM students WHERE teacher_id = ?)
            """, (session["user_id"],)
        )


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    synchronize_absentees()
    conn = get_db()

    s_sql, s_params, a_sql, a_params = _scope_query(
        "SELECT * FROM students", "SELECT * FROM attendance"
    )
    s_df = pd.read_sql_query(s_sql, conn, params=s_params)
    a_df = pd.read_sql_query(a_sql, conn, params=a_params)
    conn.close()

    # Rename to match the existing frontend's expected field names
    s_df = s_df.rename(columns={"name": "Name", "reg_no": "RegNo", "gender": "Gender", "age": "Age"})
    a_df = a_df.rename(columns={"name": "Name", "timestamp": "Timestamp", "status": "Status"})

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = a_df[a_df["Timestamp"].astype(str).str.startswith(today_str)] if not a_df.empty else a_df

    present_count = today_logs[today_logs["Status"] == "Present"]["Name"].nunique() if not today_logs.empty else 0
    absent_count = today_logs[today_logs["Status"] == "Absent"]["Name"].nunique() if not today_logs.empty else 0

    ai_insight = generate_ai_insight(s_df, a_df)

    return jsonify({
        "total_enrolled": int(s_df["Name"].nunique()) if not s_df.empty else 0,
        "present_today": int(present_count),
        "absent_today": int(absent_count),
        "today_logs": today_logs.to_dict(orient="records"),
        "students_list": s_df.to_dict(orient="records"),
        "ai_insight": ai_insight
    })


@app.route('/api/attendance/all', methods=['GET'])
@role_required("admin")
def get_all_attendance():
    """Admin-only full history dump. Most downloads should go through
    /api/attendance/download (in auth.py) instead, which is role-filtered."""
    conn = get_db()
    a_df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()
    a_df = a_df.rename(columns={"name": "Name", "timestamp": "Timestamp", "status": "Status"})
    return jsonify(a_df.to_dict(orient="records"))


@app.route('/api/recognize', methods=['POST'])
@login_required
def recognize_face():
    global known_face_encodings, known_face_names
    if 'image' not in request.files:
        return jsonify({"error": "No image found"}), 400

    npimg = np.frombuffer(request.files['image'].read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    conn = get_db()
    today_str = datetime.now().strftime("%Y-%m-%d")

    for face_encoding in face_encodings:
        if not known_face_encodings:
            break
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.45)
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

        if len(face_distances) > 0 and matches[np.argmin(face_distances)]:
            name = known_face_names[np.argmin(face_distances)]

            already_present = conn.execute(
                """SELECT 1 FROM attendance
                   WHERE name = ? AND status = 'Present' AND timestamp LIKE ?""",
                (name, f"{today_str}%")
            ).fetchone()

            if not already_present:
                conn.execute(
                    """DELETE FROM attendance
                       WHERE name = ? AND status = 'Absent' AND timestamp LIKE ?""",
                    (name, f"{today_str}%")
                )
                student_row = conn.execute(
                    "SELECT reg_no FROM students WHERE name = ? LIMIT 1", (name,)
                ).fetchone()
                reg_no = student_row["reg_no"] if student_row else None

                conn.execute(
                    """INSERT INTO attendance (reg_no, name, timestamp, status)
                       VALUES (?, ?, ?, ?)""",
                    (reg_no, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Present")
                )
                conn.commit()

    conn.close()
    synchronize_absentees()
    return jsonify({"status": "processed"})


def run_capture_and_reload(name):
    global known_face_encodings, known_face_names
    process = subprocess.Popen(
        [sys.executable, "data_collection.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=open("capture_log.txt", "w"),
        stderr=subprocess.STDOUT
    )
    process.wait()  # waits until capture finishes (window closes / 50 photos done)
    known_face_encodings, known_face_names = load_known_faces()
    print(f"Reloaded known faces after enrolling: {name}")


@app.route('/api/enroll', methods=['POST'])
@role_required("admin", "teacher")
def enroll_student():
    data = request.json
    name = data.get("name")
    reg_no = data.get("regNo")
    gender = data.get("gender")
    age = data.get("age")
    class_name = data.get("classSection")

    # Teachers enrolling a student are automatically assigned as that
    # student's teacher. Admins can enroll without an owning teacher
    # (assign one later) unless you add a teacher-picker to the admin UI.
    teacher_id = session["user_id"] if session["role"] == "teacher" else None

    conn = get_db()
    existing = conn.execute("SELECT 1 FROM students WHERE reg_no = ?", (reg_no,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"status": "Error", "message": f"RegNo {reg_no} already exists."}), 400

    conn.execute(
        """INSERT INTO students (name, reg_no, gender, age, class_name, teacher_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, reg_no, gender, age, class_name, teacher_id)
    )
    conn.commit()
    conn.close()

    thread = threading.Thread(target=run_capture_and_reload, args=(name,))
    thread.start()

    return jsonify({"status": "Success", "message": "Launching tracking hardware camera environment..."})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)