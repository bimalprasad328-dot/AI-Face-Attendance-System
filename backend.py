import os
import cv2
import subprocess
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import face_recognition
from groq import Groq
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

CORS(app)
# Initialize Groq Client
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Create a .env file with GROQ_API_KEY=your_key")
groq_client = Groq(api_key=GROQ_API_KEY)
DATASET_DIR = "dataset"
ATTENDANCE_FILE = "attendance.csv"
STUDENTS_FILE = "students.csv"

# Validate base storage file infrastructures
for file_path, columns in [(ATTENDANCE_FILE, ["Timestamp", "Name", "Status"]), (STUDENTS_FILE, ["Name", "RegNo", "Gender", "Age"])]:
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        
        pd.DataFrame(columns=columns).to_csv(file_path, index=False)

def load_known_faces():
    known_encodings, known_names = [], []
    if not os.path.exists(DATASET_DIR): return known_encodings, known_names
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
                except Exception: continue
    return known_encodings, known_names

known_face_encodings, known_face_names = load_known_faces()

def synchronize_absentees():
    """Scans student records against today's logs and automatically handles missing students."""
    s_df = pd.read_csv(STUDENTS_FILE)
    a_df = pd.read_csv(ATTENDANCE_FILE)
    if s_df.empty: return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    a_df['Timestamp_Clean'] = a_df['Timestamp'].astype(str)
    today_logs = a_df[a_df['Timestamp_Clean'].str.startswith(today_str)]
    present_today = today_logs[today_logs['Status'] == 'Present']['Name'].unique()
    
    updated_needed = False
    for _, student in s_df.iterrows():
        name = student['Name']
        if name in present_today:
            absent_row_mask = (a_df['Name'] == name) & (a_df['Timestamp_Clean'].str.startswith(today_str)) & (a_df['Status'] == 'Absent')
            if absent_row_mask.any():
                a_df = a_df[~absent_row_mask]
                updated_needed = True
        else:
            absent_today_mask = (today_logs['Name'] == name) & (today_logs['Status'] == 'Absent')
            if not absent_today_mask.any():
                new_absent_entry = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Name": name, "Status": "Absent"}
                a_df = pd.concat([a_df, pd.DataFrame([new_absent_entry])], ignore_index=True)
                updated_needed = True
                
    if updated_needed:
        if 'Timestamp_Clean' in a_df.columns: a_df = a_df.drop(columns=['Timestamp_Clean'])
        a_df.to_csv(ATTENDANCE_FILE, index=False)

def generate_ai_insight(s_df, a_df):
    """Feeds active operational CSV data tables straight to Groq for automated pipeline insights."""
    if s_df.empty:
        return "Waiting for enrollment data indexes to generate automated insights..."
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_logs = a_df[a_df['Timestamp'].astype(str).str.startswith(today_str)]
    
    # Construct an analytic payload context prompt for the Llama architecture
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    synchronize_absentees()
    s_df = pd.read_csv(STUDENTS_FILE)
    a_df = pd.read_csv(ATTENDANCE_FILE)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    today_logs = a_df[a_df['Timestamp'].astype(str).str.startswith(today_str)]
    present_count = today_logs[today_logs['Status'] == 'Present']['Name'].nunique()
    absent_count = today_logs[today_logs['Status'] == 'Absent']['Name'].nunique()
    
    # Run the automated Groq prompt calculation asynchronously
    ai_insight = generate_ai_insight(s_df, a_df)
    
    return jsonify({
        "total_enrolled": int(s_df['Name'].nunique()),
        "present_today": int(present_count),
        "absent_today": int(absent_count),
        "today_logs": today_logs.to_dict(orient="records"),
        "students_list": s_df.to_dict(orient="records"),
        "ai_insight": ai_insight
    })

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    global known_face_encodings, known_face_names
    if 'image' not in request.files: return jsonify({"error": "No image found"}), 400
    
    npimg = np.frombuffer(request.files['image'].read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    a_df = pd.read_csv(ATTENDANCE_FILE)
    today_str = datetime.now().strftime("%Y-%m-%d")
    file_changed = False
    
    for face_encoding in face_encodings:
        if not known_face_encodings: break
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.45)
        name = "Unknown"
        
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if len(face_distances) > 0 and matches[np.argmin(face_distances)]:
            name = known_face_names[np.argmin(face_distances)]
            
            already_present = a_df[(a_df['Name'] == name) & (a_df['Timestamp'].astype(str).str.startswith(today_str)) & (a_df['Status'] == 'Present')]
            if already_present.empty:
                a_df = a_df[~((a_df['Name'] == name) & (a_df['Timestamp'].astype(str).str.startswith(today_str)) & (a_df['Status'] == 'Absent'))]
                new_entry = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Name": name, "Status": "Present"}
                a_df = pd.concat([a_df, pd.DataFrame([new_entry])], ignore_index=True)
                file_changed = True
                
    if file_changed:
        a_df.to_csv(ATTENDANCE_FILE, index=False)
    synchronize_absentees()
    return jsonify({"status": "processed"})

@app.route('/api/enroll', methods=['POST'])
def enroll_student():
    data = request.json
    name, reg, gender, age = data.get("name"), data.get("regNo"), data.get("gender"), data.get("age")
    df = pd.read_csv(STUDENTS_FILE)
    pd.concat([df, pd.DataFrame([{"Name": name, "RegNo": reg, "Gender": gender, "Age": age}])], ignore_index=True).to_csv(STUDENTS_FILE, index=False)
    subprocess.Popen(["python", "data_collection.py"])
    return jsonify({"status": "Success", "message": "Launching tracking hardware camera environment..."})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)