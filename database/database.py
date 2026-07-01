import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "nova.db"


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self._init_tables()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                response TEXT,
                success INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        conn.close()

    # ── Notes ────────────────────────────────────────────────────────────────
    def add_note(self, content: str) -> int:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (content, created_at) VALUES (?, ?)",
            (content, datetime.now().isoformat()),
        )
        conn.commit()
        note_id = cur.lastrowid
        conn.close()
        return note_id

    def get_notes(self) -> list[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM notes ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_note(self, note_id: int) -> bool:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_latest_note_id(self) -> int | None:
        notes = self.get_notes()
        return notes[0]["id"] if notes else None

    # ── Command history ──────────────────────────────────────────────────────
    def save_history(self, command: str, response: str, success: bool):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO command_history (command, response, success, created_at) VALUES (?, ?, ?, ?)",
            (command, response, int(success), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_history(self, limit: int = 20) -> list[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM command_history ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_setting(self, key: str, default=None):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
        conn.close()


# single shared instance used across the app
db = Database()
