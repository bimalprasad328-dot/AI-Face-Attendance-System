"""
FaceAttend AI - Auth Module
=============================
Drop this next to backend.py and import from it. See integration notes
at the bottom of this file for exactly what to add to backend.py.
"""

import sqlite3
from functools import wraps
from flask import Blueprint, request, session, jsonify, redirect, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash
import io
import csv

DB_PATH = "faceattend.db"

auth_bp = Blueprint("auth", __name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Decorators ----------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Not logged in"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Not authorized for this action"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ---------- Routes ----------

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    return jsonify({
        "message": "Logged in",
        "username": user["username"],
        "role": user["role"]
    })


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/api/session", methods=["GET"])
def session_info():
    if "user_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "username": session.get("username"),
        "role": session.get("role")
    })


@auth_bp.route("/api/change-credentials", methods=["POST"])
@login_required
def change_credentials():
    data = request.get_json(force=True)
    current_password = data.get("currentPassword") or ""
    new_username = (data.get("newUsername") or "").strip()
    new_password = data.get("newPassword") or ""

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], current_password):
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 401

    if not new_username and not new_password:
        conn.close()
        return jsonify({"error": "Provide a new username and/or new password"}), 400

    if new_username:
        clash = conn.execute(
            "SELECT 1 FROM users WHERE username = ? AND id != ?",
            (new_username, user["id"])
        ).fetchone()
        if clash:
            conn.close()
            return jsonify({"error": f"Username '{new_username}' is already taken"}), 400
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, user["id"]))
        session["username"] = new_username

    if new_password:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user["id"])
        )

    conn.commit()
    conn.close()

    return jsonify({"message": "Credentials updated successfully"})


# ---------- Role-filtered attendance download ----------
# Replaces the old client-side "/api/attendance/all" + JS filtering.
# Admin gets everyone's records; Teacher only gets their own students' records.

@auth_bp.route("/api/attendance/download", methods=["GET"])
@login_required
def download_attendance():
    date = request.args.get("date")  # expected format: YYYY-MM-DD
    if not date:
        return jsonify({"error": "date query param is required"}), 400

    conn = get_db()

    if session["role"] == "admin":
        rows = conn.execute(
            """SELECT a.timestamp, a.name, a.status
               FROM attendance a
               WHERE a.timestamp LIKE ?
               ORDER BY a.timestamp""",
            (f"{date}%",)
        ).fetchall()
    else:  # teacher - only their own students
        rows = conn.execute(
            """SELECT a.timestamp, a.name, a.status
               FROM attendance a
               JOIN students s ON a.reg_no = s.reg_no
               WHERE a.timestamp LIKE ? AND s.teacher_id = ?
               ORDER BY a.timestamp""",
            (f"{date}%", session["user_id"])
        ).fetchall()

    conn.close()

    if not rows:
        return jsonify({"error": f"No records found for {date}"}), 404

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Timestamp", "Name", "Status"])
    for r in rows:
        writer.writerow([r["timestamp"], r["name"], r["status"]])

    mem = io.BytesIO(buffer.getvalue().encode("utf-8"))
    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_records_{date}.csv"
    )


"""
=====================================================================
INTEGRATION NOTES - add these to backend.py
=====================================================================

1. At the top of backend.py:

    from auth import auth_bp, login_required, role_required
    app.secret_key = "change-this-to-a-real-random-secret-key"  # required for sessions
    app.register_blueprint(auth_bp)

2. Protect existing routes by adding decorators, e.g.:

    @app.route("/api/enroll", methods=["POST"])
    @role_required("admin", "teacher")
    def enroll():
        ...

    @app.route("/api/stats")
    @login_required
    def stats():
        ...

3. Remove/retire the old "/api/attendance/all" route (or keep it but
   protect it with @role_required("admin") only) - the new
   "/api/attendance/download" route replaces the CSV-download flow and
   already applies teacher/admin filtering server-side.

4. On the frontend, downloadCsv() in the dashboard HTML should be
   simplified to hit the new endpoint directly instead of fetching
   everything and filtering in JS:

    async function downloadCsv() {
        const selectedDate = document.getElementById('download-date').value
            || new Date().toISOString().slice(0, 10);
        window.location.href =
            `http://127.0.0.1:5000/api/attendance/download?date=${selectedDate}`;
    }

   The browser will handle the file download directly from the
   response headers - no more blob/URL.createObjectURL needed.

5. You'll also need a login.html page and a small JS guard at the top
   of the dashboard that redirects to /login if /api/session says
   logged_in: false. Ask me for that next if you want it.
"""