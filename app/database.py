"""SQLite connection helpers."""
import os
import sqlite3

DB_PATH = os.environ.get("STUDYROOM_DB", "studyrooms.db")


def connect(path=None):
    # check_same_thread=False because FastAPI can use different threads for one request
    conn = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL UNIQUE,
            capacity INTEGER NOT NULL CHECK (capacity > 0)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id    INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            booked_by  TEXT NOT NULL,
            date       TEXT NOT NULL,      -- YYYY-MM-DD
            start_time TEXT NOT NULL,      -- HH:MM (24h)
            end_time   TEXT NOT NULL
        );
        """
    )
    conn.commit()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
