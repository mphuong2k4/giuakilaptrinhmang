"""
Seed demo data (movies + showtimes) into the server sqlite DB.

Usage:
  python -m scripts.seed_demo --db server/cinema.db
"""
from __future__ import annotations

import argparse
import datetime as dt

from server.db import connect, init_db, add_movie, add_showtime


def _movie_exists(conn, title: str) -> bool:
    row = conn.execute("SELECT id FROM movies WHERE title = ?", (title,)).fetchone()
    return row is not None


def _count_showtimes(conn) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM showtimes").fetchone()
    return int(row["c"]) if row else 0


def main() -> None:
    p = argparse.ArgumentParser(
    description="Seed demo movies & showtimes into cinema DB"
)
    p.add_argument("--db", default="server/cinema.db")
    args = p.parse_args()

    conn = connect(args.db)
    init_db(conn)

    # If already seeded, don't create duplicates.
    # (Still prints what is currently in DB so it's easy to demo.)
    if _count_showtimes(conn) > 0:
        print("DB already has showtimes. Skip seeding to avoid duplicates.")
    else:
        # Create some demo movies (only if missing)
        movies = [
            ("The Socket Adventure", "Phim demo về lập trình socket.", 110),
            ("Python & Friends", "Hành trình xây hệ thống đặt vé.", 95),
            ("Cinema Nights", "Đêm phim cuối tuần: đặt vé nhanh, chọn ghế chuẩn.", 105),
        ]

        movie_ids = []
        for title, desc, dur in movies:
            if not _movie_exists(conn, title):
                movie_ids.append(add_movie(conn, title, desc, dur))
            else:
                row = conn.execute("SELECT id FROM movies WHERE title = ?", (title,)).fetchone()
                movie_ids.append(int(row["id"]))

        m1, m2, m3 = movie_ids

        # Create showtimes (more variety for demo)
        now = dt.datetime.now().replace(second=0, microsecond=0)

        add_showtime(conn, m1, (now + dt.timedelta(hours=2)).isoformat(), "P1", 75000)
        add_showtime(conn, m1, (now + dt.timedelta(hours=5)).isoformat(), "P2", 80000)
        add_showtime(conn, m1, (now + dt.timedelta(days=1, hours=3)).isoformat(), "P1", 80000)

        add_showtime(conn, m2, (now + dt.timedelta(hours=4)).isoformat(), "P1", 70000)
        add_showtime(conn, m2, (now + dt.timedelta(days=1, hours=1)).isoformat(), "P2", 72000)

        add_showtime(conn, m3, (now + dt.timedelta(days=2, hours=2)).isoformat(), "P3", 90000)

        print("Seed demo OK. Admin account: admin / admin123")

    # Print a short summary for screenshot/demo
    movies = conn.execute("SELECT id, title, duration_min FROM movies ORDER BY id").fetchall()
    print("\nMovies in DB:")
    for r in movies:
        print(f"  - #{r['id']}: {r['title']} ({r['duration_min']} min)")

    showtimes = conn.execute(
        """
        SELECT s.id, s.start_time, s.hall, s.price, m.title AS movie_title
        FROM showtimes s
        JOIN movies m ON m.id = s.movie_id
        ORDER BY s.start_time ASC
        """
    ).fetchall()
    print("\nShowtimes in DB:")
    for r in showtimes:
        print(f"  - showtime #{r['id']}: {r['movie_title']} | {r['start_time']} | hall {r['hall']} | {r['price']}")

    conn.close()


if __name__ == "__main__":
    main()
