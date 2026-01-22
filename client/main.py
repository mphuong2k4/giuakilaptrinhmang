from __future__ import annotations

import argparse
import socket
import json
from typing import Any, Dict, Optional

from common.protocol import Message
 
 
class Client:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.f = None
        self.token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port))
        self.f = self.sock.makefile("rwb")

    def close(self) -> None:
        try:
            if self.f:
                self.f.close()
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

    def request(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.f:
            raise RuntimeError("Not connected")
        # attach token for auth-required actions (server ignores if not needed)
        if self.token and "token" not in data:
            data = dict(data)
            data["token"] = self.token
        msg = Message(action=action, data=data).to_json_line()
        self.f.write(msg.encode("utf-8"))
        self.f.flush()
        line = self.f.readline()
        if not line:
            raise RuntimeError("Server disconnected")
        return json.loads(line.decode("utf-8"))

    def ensure_ok(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error") or "Unknown error")
        return resp.get("data") or {}


def prompt(msg: str) -> str:
    return input(msg).strip()


def print_movies(movies):
    if not movies:
        print("Chưa có phim nào.")
        return
    print("\n=== DANH SÁCH PHIM ===")
    for m in movies:
        print(f"[{m['id']}] {m['title']} ({m.get('duration_min') or '?'} phút)")
        if m.get("description"):
            print(f"    {m['description']}")


def print_showtimes(showtimes):
    if not showtimes:
        print("Chưa có suất chiếu.")
        return
    print("\n=== SUẤT CHIẾU ===")
    for s in showtimes:
        print(f"[{s['id']}] {s['start_time']} | Phòng: {s['hall']} | Giá: {s['price']} | Phim: {s['movie_title']}")

 
def print_seats(seats):
    # show as grid A-E, 1-8
    status = {x["seat_code"]: x["status"] for x in seats}
    rows = sorted(set(code[0] for code in status.keys()))
    cols = sorted(set(int(code[1:]) for code in status.keys()))
    print("\n=== GHẾ (O=trống, X=đã đặt) ===")
    header = "    " + " ".join(f"{c:>2}" for c in cols)
    print(header)
    for r in rows:
        line = [r + " :"]
        for c in cols:
            code = f"{r}{c}"
            line.append(" O" if status.get(code) == "available" else " X")
        print(" ".join(line))
    print("Ví dụ nhập ghế: A1, B5, E8 ...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cinema Booking Socket Client (CLI)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5555)
    args = parser.parse_args()

    c = Client(args.host, args.port)
    c.connect()
    print("Kết nối server OK.\n")

    try:
        while True:
            if not c.token:
                print("=== MENU ===")
                print("1) Đăng ký")
                print("2) Đăng nhập")
                print("0) Thoát")
                choice = prompt("> ")
                if choice == "1":
                    u = prompt("Username: ")
                    p = prompt("Password: ")
                    data = c.ensure_ok(c.request("register", {"username": u, "password": p}))
                    print("✅", data.get("message"))
                elif choice == "2":
                    u = prompt("Username: ")
                    p = prompt("Password: ")
                    data = c.ensure_ok(c.request("login", {"username": u, "password": p}))
                    c.token = data["token"]
                    c.user = data["user"]
                    print(f"✅ Xin chào {c.user['username']} (role={c.user['role']})")
                elif choice == "0":
                    break
                else:
                    print("Lựa chọn không hợp lệ.")
                continue

            # logged in
            role = (c.user or {}).get("role", "user")
            print("\n=== MENU (đã đăng nhập) ===")
            print("1) Xem danh sách phim")
            print("2) Xem suất chiếu theo phim")
            print("3) Xem ghế theo suất chiếu")
            print("4) Đặt vé")
            print("5) Vé của tôi")
            print("6) Huỷ vé")
            if role == "admin":
                print("7) (Admin) Thêm phim")
                print("8) (Admin) Thêm suất chiếu")
            print("9) Đăng xuất")
            choice = prompt("> ")

            if choice == "1":
                data = c.ensure_ok(c.request("list_movies", {}))
                print_movies(data.get("movies", []))

            elif choice == "2":
                movie_id = int(prompt("Nhập movie_id: "))
                data = c.ensure_ok(c.request("list_showtimes", {"movie_id": movie_id}))
                print_showtimes(data.get("showtimes", []))

            elif choice == "3":
                showtime_id = int(prompt("Nhập showtime_id: "))
                data = c.ensure_ok(c.request("get_seats", {"showtime_id": showtime_id}))
                print_seats(data.get("seats", []))

            elif choice == "4":
                showtime_id = int(prompt("Nhập showtime_id: "))
                seat_code = prompt("Nhập seat_code (VD A1): ").upper()
                data = c.ensure_ok(c.request("book", {"showtime_id": showtime_id, "seat_code": seat_code}))
                print("✅", data.get("message"), "| ticket_id:", data.get("ticket_id"))

            elif choice == "5":
                data = c.ensure_ok(c.request("my_tickets", {}))
                tickets = data.get("tickets", [])
                if not tickets:
                    print("Bạn chưa có vé.")
                else:
                    print("\n=== VÉ CỦA TÔI ===")
                    for t in tickets:
                        print(f"[{t['id']}] {t['movie_title']} | {t['start_time']} | {t['hall']} | Ghế {t['seat_code']} | {t['price']} | {t['status']}")

            elif choice == "6":
                ticket_id = int(prompt("Nhập ticket_id muốn huỷ: "))
                data = c.ensure_ok(c.request("cancel", {"ticket_id": ticket_id}))
                print("✅", data.get("message"))

            elif choice == "7" and role == "admin":
                title = prompt("Tiêu đề phim: ")
                description = prompt("Mô tả: ")
                duration = int(prompt("Thời lượng (phút): ") or "0")
                data = c.ensure_ok(c.request("admin_add_movie", {"title": title, "description": description, "duration_min": duration}))
                print("✅ movie_id:", data.get("movie_id"))

            elif choice == "8" and role == "admin":
                movie_id = int(prompt("movie_id: "))
                start_time = prompt("start_time ISO (VD 2026-01-12T19:30:00): ")
                hall = prompt("hall (VD P1): ")
                price = int(prompt("price: ") or "0")
                data = c.ensure_ok(c.request("admin_add_showtime", {"movie_id": movie_id, "start_time": start_time, "hall": hall, "price": price}))
                print("✅ showtime_id:", data.get("showtime_id"))

            elif choice == "9":
                c.ensure_ok(c.request("logout", {}))
                c.token = None
                c.user = None
                print("✅ Đã đăng xuất.")

            else:
                print("Lựa chọn không hợp lệ.")

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("❌ Lỗi:", e)
    finally:
        c.close()


if __name__ == "__main__":
    main()
    


