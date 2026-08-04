# AI Face Attendance System 🚀

An automated attendance tracking system powered by Artificial Intelligence and computer vision. This project uses facial recognition to identify individuals and log their attendance in real-time, eliminating manual paperwork and buddy punching.

---

## 🛠️ Tech Stack & Structure

### Project Components:
* **Frontend**: HTML5, CSS3, and JavaScript (with a responsive, modern UI)
* **Backend**: Python (Flask / FastAPI for processing data endpoints)
* **Storage**: CSV files (`students.csv`, `attendance.csv`) for student directories and daily attendance logging
* **AI & Computer Vision**: Python OpenCV / Face Recognition libraries

### File Directory Layout:
* `backend.py` — Handles API routes and facial recognition data flows.
* `data.collection.py` — Script to gather and register initial student face images.
* `frontend/index.html` — Clean, user-friendly dashboard interface.
* `students.csv` — Contains database details of registered students.
* `attendance.csv` — Live log recording dates, times, and present names.

---

## 🚀 Key Features

* **Real-Time Detection**: Instantly registers faces through camera streaming.
* **Modern UI Dashboard**: Styled with custom CSS variables, custom typography, and responsive grid layouts.
* **Automatic CSV Updates**: Records attendance logs with precise time stamping instantly.
* **Secure Environment Configuration**: Protects system variables using hidden `.env` files.

---

## 📥 Setup & Installation

Follow these steps to run the project locally on your machine:

### 1. Clone the repository
```bash
git clone https://github.com
cd AI-Face-Attendance-System
```

### 2. Set up a Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Register Student Faces
Run the data collection script to snap face samples and update your directory:
```bash
python data.collection.py
```

### 4. Start the Application Server
Launch the backend processor:
```bash
python backend.py
```
Open `frontend/index.html` directly in your browser or run it via a Live Server extension to begin tracking live attendance!

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
