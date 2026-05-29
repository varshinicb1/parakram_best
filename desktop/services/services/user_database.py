"""
User Signup Database — SQLite-backed user registration for Parakram downloads.

Stores: name, email, phone, signup timestamp, download status.
No Google auth — simple email/phone registration.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib
import re

DB_PATH = Path("./storage/users.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class UserDatabase:
    """SQLite database for user signups."""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT DEFAULT '',
                organization TEXT DEFAULT '',
                use_case TEXT DEFAULT '',
                signup_at TEXT NOT NULL,
                download_count INTEGER DEFAULT 0,
                last_download_at TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                referrer TEXT DEFAULT '',
                plan TEXT DEFAULT 'free',
                verified INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS download_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                version TEXT,
                platform TEXT,
                downloaded_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        conn.close()

    def signup(self, name: str, email: str, phone: str = "",
               organization: str = "", use_case: str = "",
               ip_address: str = "", referrer: str = "") -> dict:
        """Register a new user."""
        # Validate
        if not name or len(name.strip()) < 2:
            return {"error": "Name must be at least 2 characters"}
        if not self._validate_email(email):
            return {"error": "Invalid email address"}
        if phone and not self._validate_phone(phone):
            return {"error": "Invalid phone number"}

        email = email.lower().strip()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO users (name, email, phone, organization, use_case,
                   signup_at, ip_address, referrer)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name.strip(), email, phone.strip(), organization.strip(),
                 use_case.strip(), datetime.now().isoformat(),
                 ip_address, referrer)
            )
            conn.commit()
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.close()

            # Generate download token
            token = hashlib.sha256(f"{user_id}{email}{datetime.now().isoformat()}".encode()).hexdigest()[:24]

            return {
                "success": True,
                "user_id": user_id,
                "download_token": token,
                "message": f"Welcome to Parakram, {name.strip()}! Your download is ready.",
            }
        except sqlite3.IntegrityError:
            return {"error": "Email already registered. Check your inbox for download link."}
        except Exception as e:
            return {"error": f"Registration failed: {str(e)}"}

    def log_download(self, user_id: int, version: str = "2.0.0", platform: str = "desktop"):
        """Log a download event."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO download_logs (user_id, version, platform, downloaded_at) VALUES (?, ?, ?, ?)",
            (user_id, version, platform, datetime.now().isoformat())
        )
        conn.execute(
            "UPDATE users SET download_count = download_count + 1, last_download_at = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        conn.close()

    def get_user(self, email: str) -> Optional[dict]:
        """Get user by email."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self, limit: int = 100, offset: int = 0) -> dict:
        """Get all users for admin dashboard."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        users = conn.execute(
            "SELECT * FROM users ORDER BY signup_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return {
            "users": [dict(u) for u in users],
            "total": total,
            "page_size": limit,
            "offset": offset,
        }

    def get_stats(self) -> dict:
        """Get signup statistics."""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM users WHERE signup_at LIKE ?",
            (f"{datetime.now().strftime('%Y-%m-%d')}%",)
        ).fetchone()[0]
        downloads = conn.execute("SELECT COUNT(*) FROM download_logs").fetchone()[0]
        conn.close()
        return {"total_users": total, "signups_today": today, "total_downloads": downloads}

    def _validate_email(self, email: str) -> bool:
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

    def _validate_phone(self, phone: str) -> bool:
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        return len(cleaned) >= 10 and cleaned.isdigit()


_db: Optional[UserDatabase] = None

def get_user_db() -> UserDatabase:
    global _db
    if _db is None:
        _db = UserDatabase()
    return _db
