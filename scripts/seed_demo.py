"""
Seed demo data (movies + showtimes) into the server sqlite DB.

Usage:
  python -m scripts.seed_demo --db server/cinema.db
"""
from __future__ import annotations

import argparse
import datetime as dt

from server.db import connect, init_db, add_movie, add_showtime


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="server/cinema.db")
    args = p.parse_args()

    conn = connect(args.db)
    init_db(conn)

    # Create some demo movies
    m1 = add_movie(conn, "The Socket Adventure", "Phim demo về lập trình socket.", 110)
    m2 = add_movie(conn, "Python & Friends", "Hành trình xây hệ thống đặt vé.", 95)

    # Create showtimes
    now = dt.datetime.now().replace(second=0, microsecond=0)
    add_showtime(conn, m1, (now + dt.timedelta(hours=2)).isoformat(), "P1", 75000)
    add_showtime(conn, m1, (now + dt.timedelta(days=1, hours=3)).isoformat(), "P2", 80000)
    add_showtime(conn, m2, (now + dt.timedelta(hours=4)).isoformat(), "P1", 70000)

    print("Seed demo OK. Admin account: admin / admin123")


if __name__ == "__main__":
    main()
