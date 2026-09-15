"""
FaceAttend AI - Change Username / Password
=============================================
Run this to update login credentials for an existing user
(e.g. the default admin account).

USAGE:
    python change_credentials.py
"""

import sqlite3
import getpass
from werkzeug.security import generate_password_hash

DB_PATH = "faceattend.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    users = conn.execute("SELECT id, username, role FROM users").fetchall()
    if not users:
        print("No users found in the database.")
        return

    print("Existing users:")
    for u in users:
        print(f"  [{u['id']}] {u['username']} ({u['role']})")

    current_username = input("\nEnter the CURRENT username to update: ").strip()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (current_username,)).fetchone()

    if not user:
        print(f"No user found with username '{current_username}'.")
        conn.close()
        return

    new_username = input(f"New username (leave blank to keep '{user['username']}'): ").strip()
    new_password = getpass.getpass("New password (leave blank to keep current password): ").strip()

    updates = {}
    if new_username:
        updates["username"] = new_username
    if new_password:
        updates["password_hash"] = generate_password_hash(new_password)

    if not updates:
        print("Nothing to change.")
        conn.close()
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user["id"]]

    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

    print("\nUpdated successfully.")
    if "username" in updates:
        print(f"  New username: {updates['username']}")
    if "password_hash" in updates:
        print("  Password changed.")


if __name__ == "__main__":
    main()