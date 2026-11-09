# FaceAttend AI

An AI-based attendance management system that uses face recognition to mark attendance automatically. Built with a Flask backend and an HTML/JavaScript dashboard.

## Features

- **Face enrollment**: register students with their name, registration number, gender, age and class/section
- **Auto attendance**: live camera face recognition that logs attendance with a timestamp
- **Dashboard**: overview of attendance activity
- **Records**: browse attendance history and download it as CSV for a chosen date
- **Login system with roles**: Admin and Teacher accounts (teachers only see their own students' records)
- **Account settings**: change your username and password from inside the app
- **AI assistant**: built-in assistant powered by Groq / Llama 3, with support for other providers (Anthropic, OpenAI, Gemini, Mistral, custom endpoints)

## Tech Stack

- **Backend:** Python, Flask, SQLite
- **Face recognition:** OpenCV, dlib / face_recognition
- **Frontend:** HTML, CSS, JavaScript
- **Config:** python-dotenv for API keys

## Project Structure

```
face-detection-clean/
├── backend.py             # Flask app and API routes
├── auth.py                # Login, roles, change-credentials, CSV download
├── data_collection.py     # Face capture script used during enrollment
├── migrate_to_sqlite.py   # Migrates old CSV data into SQLite
├── frontend/
│   ├── index.html         # Dashboard
│   └── login.html         # Login page
├── requirements.txt
└── .env                   # Your API keys (not committed)
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/bimalprasad328-dot/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Create an environment and install dependencies

```bash
conda create -n faceattend python=3.11
conda activate faceattend
pip install -r requirements.txt
```

> On Windows, dlib can be hard to build with pip. Installing it through conda is easier.

### 3. Add your API keys

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Add keys for any other AI provider you want to use.

### 4. Set up the database

If you have old CSV data, run the migration once:

```bash
python migrate_to_sqlite.py
```

### 5. Run the app

```bash
python backend.py
```

The server starts at `http://127.0.0.1:5000`. Open the login page, sign in with your admin account, and you can change your credentials from **Account Settings**.

## Usage

1. **Enroll a student** from the Enroll Student page. The camera captures face samples.
2. **Take attendance** from the Auto Attendance page. Recognised students are logged automatically.
3. **View or download records** from the Records page. Pick a date and download the CSV.

## Security Notes

- Passwords are stored as hashes, never in plain text.
- Keep your `.env` file, database and face dataset out of version control.
- Set a strong, random `app.secret_key` in `backend.py` before deploying.

## Roadmap

- Attendance analytics and reports
- Email / SMS notifications
- Docker setup and a setup wizard
- Demo video

## Author

**Bimal**, B.Tech CSE, Aryan Institute of Engineering and Technology, Bhubaneswar
GitHub: [bimalprasad328-dot](https://github.com/bimalprasad328-dot)

## License

Add a license of your choice (for example MIT) before sharing publicly.