from __future__ import annotations

import os
import sqlite3
import hashlib
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

DB_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), "cinema.db")


def connect(db_path: str = DB_PATH_DEFAULT) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','admin'))
        );

        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            duration_min INTEGER
        );

        CREATE TABLE IF NOT EXISTS showtimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,   -- ISO 8601 string
            hall TEXT NOT NULL,
            price INTEGER NOT NULL,
            FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            showtime_id INTEGER NOT NULL,
            seat_code TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('available','booked')),
            booked_by INTEGER,
            booked_at TEXT,
            UNIQUE(showtime_id, seat_code),
            FOREIGN KEY(showtime_id) REFERENCES showtimes(id) ON DELETE CASCADE,
            FOREIGN KEY(booked_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            showtime_id INTEGER NOT NULL,
            seat_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active','cancelled')),
            UNIQUE(showtime_id, seat_code),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(showtime_id) REFERENCES showtimes(id)
        );


        """
    )
    conn.commit()

    # Seed admin if missing
    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users(username, password_hash, role) VALUES(?,?,?)",
            ("admin", sha256_hex("admin123"), "admin"),
        )
        conn.commit()


def ensure_seats_for_showtime(conn: sqlite3.Connection, showtime_id: int, rows: int = 5, cols: int = 8) -> None:
    """
    Create seats for a showtime if not already created.
    Default: 5 rows (A-E) x 8 columns (1-8) = 40 seats.
    """
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM seats WHERE showtime_id = ?", (showtime_id,))
    if cur.fetchone()["c"] > 0:
        return
    for r in range(rows):
        row_letter = chr(ord("A") + r)
        for c in range(1, cols + 1):
            code = f"{row_letter}{c}"
            cur.execute(
                "INSERT INTO seats(showtime_id, seat_code, status, booked_by, booked_at) VALUES(?,?,?,?,?)",
                (showtime_id, code, "available", None, None),
            )
    conn.commit()


def create_user(conn: sqlite3.Connection, username: str, password: str) -> Tuple[bool, str]:
    try:
        conn.execute(
            "INSERT INTO users(username, password_hash, role) VALUES(?,?,?)",
            (username, sha256_hex(password), "user"),
        )
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError:
        return False, "Username already exists"


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password_hash=?",
        (username, sha256_hex(password)),
    ).fetchone()
    if not row:
        return None
    return dict(row)


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def list_movies(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM movies ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def add_movie(conn: sqlite3.Connection, title: str, description: str, duration_min: int) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO movies(title, description, duration_min) VALUES(?,?,?)",
        (title, description, duration_min),
    )
    conn.commit()
    return int(cur.lastrowid)


def add_showtime(conn: sqlite3.Connection, movie_id: int, start_time_iso: str, hall: str, price: int) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO showtimes(movie_id, start_time, hall, price) VALUES(?,?,?,?)",
        (movie_id, start_time_iso, hall, price),
    )
    conn.commit()
    showtime_id = int(cur.lastrowid)
    ensure_seats_for_showtime(conn, showtime_id)
    return showtime_id


def list_showtimes(conn: sqlite3.Connection, movie_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT s.*, m.title AS movie_title
        FROM showtimes s
        JOIN movies m ON m.id = s.movie_id
        WHERE s.movie_id = ?
        ORDER BY s.start_time ASC
        """,
        (movie_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_showtime(conn: sqlite3.Connection, showtime_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT s.*, m.title AS movie_title
        FROM showtimes s
        JOIN movies m ON m.id = s.movie_id
        WHERE s.id = ?
        """,
        (showtime_id,),
    ).fetchone()
    return dict(row) if row else None


def get_seats(conn: sqlite3.Connection, showtime_id: int) -> List[Dict[str, Any]]:
    ensure_seats_for_showtime(conn, showtime_id)
    rows = conn.execute(
        "SELECT seat_code, status FROM seats WHERE showtime_id=? ORDER BY seat_code",
        (showtime_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def book_seat(conn: sqlite3.Connection, user_id: int, showtime_id: int, seat_code: str) -> Tuple[bool, str, Optional[int]]:
    """
    Transactional seat booking.
    """
    ensure_seats_for_showtime(conn, showtime_id)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        row = cur.execute(
            "SELECT status FROM seats WHERE showtime_id=? AND seat_code=?",
            (showtime_id, seat_code),
        ).fetchone()
        if not row:
            cur.execute("ROLLBACK;")
            return False, "Seat not found", None
        if row["status"] != "available":
            cur.execute("ROLLBACK;")
            return False, "Seat already booked", None

        now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        cur.execute(
            "UPDATE seats SET status='booked', booked_by=?, booked_at=? WHERE showtime_id=? AND seat_code=?",
            (user_id, now, showtime_id, seat_code),
        )
        cur.execute(
            "INSERT INTO tickets(user_id, showtime_id, seat_code, created_at, status) VALUES(?,?,?,?,?)",
            (user_id, showtime_id, seat_code, now, "active"),
        )
        ticket_id = int(cur.lastrowid)
        cur.execute("COMMIT;")
        return True, "Booked", ticket_id
    except Exception as e:
        try:
            cur.execute("ROLLBACK;")
        except Exception:
            pass
        return False, f"Booking failed: {e}", None


def my_tickets(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.id, t.seat_code, t.created_at, t.status,
               s.start_time, s.hall, s.price,
               m.title AS movie_title
        FROM tickets t
        JOIN showtimes s ON s.id = t.showtime_id
        JOIN movies m ON m.id = s.movie_id
        WHERE t.user_id = ?
        ORDER BY t.id DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def cancel_ticket(conn: sqlite3.Connection, user_id: int, ticket_id: int) -> Tuple[bool, str]:
    cur = conn.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE;")
        row = cur.execute(
            "SELECT showtime_id, seat_code, status FROM tickets WHERE id=? AND user_id=?",
            (ticket_id, user_id),
        ).fetchone()
        if not row:
            cur.execute("ROLLBACK;")
            return False, "Ticket not found"
        if row["status"] != "active":
            cur.execute("ROLLBACK;")
            return False, "Ticket already cancelled"

        cur.execute("UPDATE tickets SET status='cancelled' WHERE id=?", (ticket_id,))
        cur.execute(
            "UPDATE seats SET status='available', booked_by=NULL, booked_at=NULL WHERE showtime_id=? AND seat_code=?",
            (row["showtime_id"], row["seat_code"]),
        )
        cur.execute("COMMIT;")
        return True, "Cancelled"
    except Exception as e:
        try:
            cur.execute("ROLLBACK;")
        except Exception:
            pass
        return False, f"Cancel failed: {e}"
