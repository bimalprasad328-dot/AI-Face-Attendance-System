"""
FaceAttend AI - CSV/JSON to SQLite Migration Script (v2)
===========================================================
Matches the ACTUAL field names used by your frontend:
  Students:   Name, RegNo, Gender, Age
  Attendance: Timestamp, Name, Status

Adds:
  - users table (admin/teacher login)
  - class_name + teacher_id on students, so Teachers only see their own class

USAGE:
    python migrate_to_sqlite.py

ADJUST BEFORE RUNNING:
- STUDENTS_SOURCE / ATTENDANCE_SOURCE paths + SOURCE_FORMAT below to match
  wherever your current data actually lives (CSV or JSON).
"""

import sqlite3
import csv
import json
import os
from werkzeug.security import generate_password_hash

DB_PATH = "faceattend.db"

# Adjust these to match your actual file locations and format
SOURCE_FORMAT = "csv"                # "csv" or "json"
STUDENTS_SOURCE = "students.csv"     # columns/keys: Name, RegNo, Gender, Age
ATTENDANCE_SOURCE = "attendance.csv" # columns/keys: Timestamp, Name, Status


def create_schema(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher')),
        full_name TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        reg_no TEXT UNIQUE NOT NULL,
        gender TEXT,
        age INTEGER,
        class_name TEXT,
        teacher_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (teacher_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_no TEXT,
        name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Present',
        FOREIGN KEY (reg_no) REFERENCES students(reg_no)
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_attendance_regno ON attendance(reg_no)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_students_teacher ON students(teacher_id)")

    conn.commit()
    print("Schema created.")


def seed_default_admin(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("changeme123"), "admin", "Default Admin")
        )
        conn.commit()
        print("Default admin created -> username: admin | password: changeme123")
        print("CHANGE THIS PASSWORD after first login.")
    else:
        print("Admin user already exists, skipping.")


def _read_source(path):
    if not os.path.exists(path):
        return None
    if SOURCE_FORMAT == "json":
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    else:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def migrate_students(conn):
    rows = _read_source(STUDENTS_SOURCE)
    if rows is None:
        print(f"Skipping students migration - {STUDENTS_SOURCE} not found.")
        return

    cur = conn.cursor()
    count = 0
    for row in rows:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO students (name, reg_no, gender, age)
                   VALUES (?, ?, ?, ?)""",
                (
                    str(row.get("Name", "")).strip(),
                    str(row.get("RegNo", "")).strip(),
                    str(row.get("Gender", "")).strip(),
                    int(row.get("Age", 0) or 0),
                )
            )
            count += 1
        except Exception as e:
            print(f"Row skipped due to error: {row} -> {e}")
    conn.commit()
    print(f"Migrated {count} student rows.")
    print("NOTE: class_name and teacher_id were left NULL - assign them via the")
    print("admin panel, or bulk-update once you decide the class/teacher mapping.")


def migrate_attendance(conn):
    rows = _read_source(ATTENDANCE_SOURCE)
    if rows is None:
        print(f"Skipping attendance migration - {ATTENDANCE_SOURCE} not found.")
        return

    cur = conn.cursor()
    count = 0
    for row in rows:
        try:
            name = str(row.get("Name", "")).strip()
            cur.execute("SELECT reg_no FROM students WHERE name = ? LIMIT 1", (name,))
            match = cur.fetchone()
            reg_no = match[0] if match else None

            cur.execute(
                """INSERT INTO attendance (reg_no, name, timestamp, status)
                   VALUES (?, ?, ?, ?)""",
                (
                    reg_no,
                    name,
                    str(row.get("Timestamp", "")).strip(),
                    str(row.get("Status", "Present")).strip() or "Present",
                )
            )
            count += 1
        except Exception as e:
            print(f"Row skipped due to error: {row} -> {e}")
    conn.commit()
    print(f"Migrated {count} attendance rows.")


def main():
    conn = sqlite3.connect(DB_PATH)
    print(f"Connected to {DB_PATH}")

    create_schema(conn)
    seed_default_admin(conn)
    migrate_students(conn)
    migrate_attendance(conn)

    conn.close()
    print("\nMigration complete.")
    print(f"Database file: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    main()
