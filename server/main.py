from __future__ import annotations

import argparse
import socket
import threading
from typing import Tuple

from common.protocol import loads_line, response_error
from .db import connect, init_db
from .handlers import SessionStore, handle


def client_thread(
    conn_sock: socket.socket,
    addr: Tuple[str, int],
    db_conn,
    sessions: SessionStore
) -> None:
    """
    Mỗi client chạy trên một thread riêng.
    Giao tiếp request/response theo từng dòng JSON.
    """
    try:
        with conn_sock:
            file_obj = conn_sock.makefile("rwb")

            while True:
                line = file_obj.readline()
                if not line:
                    break

                try:
                    msg = loads_line(line.decode("utf-8").strip())
                    resp = handle(db_conn, sessions, msg)
                except Exception as exc:
                    resp = response_error(f"Bad request: {exc}")

                file_obj.write(resp.encode("utf-8"))
                file_obj.flush()

    except Exception:
        # Không cho lỗi của 1 client làm sập server
        return


def run_server(host: str, port: int, db_path: str) -> None:
    db_conn = connect(db_path)
    init_db(db_conn)

    sessions = SessionStore()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen()

        print(f"[SERVER] Listening on {host}:{port} (db={db_path})")

        while True:
            client_sock, client_addr = server_sock.accept()
            thread = threading.Thread(
                target=client_thread,
                args=(client_sock, client_addr, db_conn, sessions),
                daemon=True,
            )
            thread.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cinema Booking Socket Server"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5555)
    parser.add_argument("--db", default=None, help="Path to sqlite db file")
    args = parser.parse_args()

    from .db import DB_PATH_DEFAULT

    db_path = args.db or DB_PATH_DEFAULT
    run_server(args.host, args.port, db_path)


if __name__ == "__main__":
    main()
