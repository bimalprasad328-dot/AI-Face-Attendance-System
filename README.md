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
* `data_collection.py` — Script to gather and register initial student face images.
* `frontend/index.html` — Clean, user-friendly dashboard interface.
* `students.csv` — Contains database details of registered students. (generated locally, not tracked in git)
* `attendance.csv` — Live log recording dates, times, and present names. (generated locally, not tracked in git)

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
git clone https://github.com/bimalprasad328-dot/AI-Face-Attendance-System.git
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

### 3. Set up environment variables
Create a `.env` file in the project root with the following:
You can get a free API key from https://console.groq.com
```
### 4. Register Student Faces
Run the data collection script to snap face samples and update your directory:
```bash
python data_collection.py
```

### 5. Start the Application Server
Launch the backend processor:
```bash
python backend.py
```
Open `frontend/index.html` directly in your browser or run it via a Live Server extension to begin tracking live attendance!

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.