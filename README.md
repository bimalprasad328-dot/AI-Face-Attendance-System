# FaceAttend AI

An AI-powered face recognition attendance system with a live camera recognition engine, role-based access control, and AI-generated attendance insights.

## Features

- **Live face recognition attendance** — webcam feed scans and marks attendance automatically every 1.5 seconds
- **Student enrollment** — capture a new student's face via webcam and store their profile
- **Role-based access** — Admin and Teacher accounts, with teachers only seeing their own class's students and attendance records
- **AI-generated insights** — a daily attendance summary generated using Groq's LLM API
- **Date-filtered attendance export** — download attendance records as CSV for any specific date, scoped to what the logged-in user is allowed to see
- **Account settings** — change your username/password directly from the dashboard, no scripts required
- **SQLite-backed** — structured relational storage for users, students, and attendance records

## Tech Stack

- **Backend:** Python, Flask, Flask-CORS
- **Database:** SQLite
- **Face Recognition:** `face_recognition` (dlib), OpenCV
- **AI Insights:** Groq API (Llama 3)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)

## Project Structure

```
face-detection-clean/
├── backend.py              # Main Flask app — stats, enroll, recognize routes
├── auth.py                 # Login/session/role logic + credentials + role-filtered CSV download
├── migrate_to_sqlite.py    # One-time script to create the database
├── data_collection.py      # Webcam capture script used during enrollment
├── requirements.txt
├── .env                    # GROQ_API_KEY (not committed)
├── faceattend.db           # SQLite database (not committed)
├── dataset/                # Captured face images, one folder per student (not committed)
└── frontend/
    ├── login.html          # Sign-in page
    └── index.html          # Main dashboard (Overview, Take Attendance, Enroll, Records)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add your Groq API key

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
FLASK_SECRET_KEY=some_random_secret_string
```

### 3. Create the database

```bash
python migrate_to_sqlite.py
```

This creates `faceattend.db` and a default admin account:

- **Username:** `admin`
- **Password:** `changeme123`

Change this immediately after your first login via the in-app **Account** settings.

### 4. Run the backend

```bash
python backend.py
```

The API runs on `http://127.0.0.1:5000`.

### 5. Open the frontend

Serve the `frontend/` folder with a local server (e.g. VS Code's Live Server extension) and open `login.html` first. After signing in, you'll be redirected to the dashboard.

## Roles

| Role    | Access                                                         |
|---------|------------------------------------------------------------------|
| Admin   | Full access — all students, all attendance records, all classes |
| Teacher | Only their own enrolled students and those students' attendance |

## Notes

- `dataset/`, `faceattend.db`, and `.env` are intentionally excluded from version control — see `.gitignore`.
- New teacher accounts and reassigning existing students to a teacher/class currently require direct database access; an in-app admin tool for this is planned.