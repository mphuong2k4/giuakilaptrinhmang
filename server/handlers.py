from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Tuple

from common.protocol import response_ok, response_error
from . import db


class SessionStore:
    def __init__(self) -> None:
        self._token_to_user: Dict[str, Dict[str, Any]] = {}

    def create(self, user: Dict[str, Any]) -> str:
        token = uuid.uuid4().hex
        self._token_to_user[token] = user
        return token

    def get(self, token: str) -> Optional[Dict[str, Any]]:
        return self._token_to_user.get(token)

    def delete(self, token: str) -> None:
        self._token_to_user.pop(token, None)


def require_auth(sessions: SessionStore, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not token:
        return None, response_error("Missing token")
    user = sessions.get(token)
    if not user:
        return None, response_error("Invalid/expired token")
    return user, None


def handle(conn, sessions: SessionStore, msg: Dict[str, Any]) -> str:
    """
    Return a JSON line response string.
    """
    action = (msg or {}).get("action")
    data = (msg or {}).get("data") or {}

    try:
        if action == "ping":
            return response_ok({"pong": True})

        if action == "register":
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", "")).strip()
            if not username or not password:
                return response_error("username/password required")
            ok, m = db.create_user(conn, username, password)
            return response_ok({"message": m}) if ok else response_error(m)

        if action == "login":
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", "")).strip()
            user = db.authenticate(conn, username, password)
            if not user:
                return response_error("Invalid credentials")
            token = sessions.create(user)
            return response_ok({"token": token, "user": user})

        # Auth-required actions
        token = str(data.get("token", "")).strip()
        user, err = require_auth(sessions, token)
        if err:
            return err

        if action == "logout":
            sessions.delete(token)
            return response_ok({"message": "Logged out"})

        if action == "list_movies":
            return response_ok({"movies": db.list_movies(conn)})

        if action == "list_showtimes":
            movie_id = int(data.get("movie_id"))
            return response_ok({"showtimes": db.list_showtimes(conn, movie_id)})

        if action == "get_seats":
            showtime_id = int(data.get("showtime_id"))
            return response_ok({"seats": db.get_seats(conn, showtime_id)})

        if action == "book":
            showtime_id = int(data.get("showtime_id"))
            seat_code = str(data.get("seat_code", "")).strip().upper()
            if not seat_code:
                return response_error("seat_code required")
            ok, m, ticket_id = db.book_seat(conn, int(user["id"]), showtime_id, seat_code)
            return response_ok({"message": m, "ticket_id": ticket_id}) if ok else response_error(m)

        if action == "my_tickets":
            return response_ok({"tickets": db.my_tickets(conn, int(user["id"]))})

        if action == "cancel":
            ticket_id = int(data.get("ticket_id"))
            ok, m = db.cancel_ticket(conn, int(user["id"]), ticket_id)
            return response_ok({"message": m}) if ok else response_error(m)

        # Admin actions
        if action in ("admin_add_movie", "admin_add_showtime"):
            if user.get("role") != "admin":
                return response_error("Admin only")

        if action == "admin_add_movie":
            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            duration_min = int(data.get("duration_min", 0))
            if not title:
                return response_error("title required")
            movie_id = db.add_movie(conn, title, description, duration_min)
            return response_ok({"movie_id": movie_id})

        if action == "admin_add_showtime":
            movie_id = int(data.get("movie_id"))
            start_time = str(data.get("start_time", "")).strip()  # ISO string
            hall = str(data.get("hall", "")).strip()
            price = int(data.get("price", 0))
            if not start_time or not hall or price <= 0:
                return response_error("start_time, hall, price required")
            showtime_id = db.add_showtime(conn, movie_id, start_time, hall, price)
            return response_ok({"showtime_id": showtime_id})

        return response_error(f"Unknown action: {action}")

    except Exception as e:
        return response_error(f"Server error: {e}")
