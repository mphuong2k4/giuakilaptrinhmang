# Hệ thống đặt vé xem phim (Socket Multi Client-Server)

Dự án mini: **Cinema Ticket Booking** dùng **TCP socket** theo mô hình **Multi client – Server**, giao tiếp bằng **JSON line protocol** (mỗi message là 1 JSON + ký tự xuống dòng).

## Tính năng
- Đăng ký / Đăng nhập (token session đơn giản)
- Xem danh sách phim
- Xem suất chiếu theo phim
- Xem sơ đồ ghế theo suất chiếu (O=trống, X=đã đặt)
- Đặt vé (giữ ghế theo giao dịch SQLite)
- Xem vé của tôi
- Huỷ vé (trả ghế về available)
- Admin: thêm phim, thêm suất chiếu
- Dữ liệu lưu bằng SQLite (`server/cinema.db`)

> Tài khoản admin seed sẵn: `admin / admin123`

## Cấu trúc thư mục
```
cinema_booking_socket/
  server/
    main.py        # chạy server
    db.py          # sqlite + nghiệp vụ
    handlers.py    # xử lý action
    cinema.db      # sinh ra khi chạy
  client/
    main.py        # client CLI
  common/
    protocol.py    # message/response helpers
  scripts/
    seed_demo.py   # seed dữ liệu demo
  tests/
    test_protocol.py
```

## Yêu cầu
- Python 3.10+ (khuyến nghị 3.11)

Không cần thư viện ngoài (toàn bộ dùng standard library).

## Cách chạy nhanh (demo)
**1) Mở terminal 1 – chạy server**
```bash
cd cinema_booking_socket
python -m server.main --host 127.0.0.1 --port 5555
```

**2) (Tuỳ chọn) Seed dữ liệu demo**
```bash
python -m scripts.seed_demo --db server/cinema.db
```

**3) Mở terminal 2 – chạy client**
```bash
python -m client.main --host 127.0.0.1 --port 5555
```

## Gợi ý test nhiều client
Mở 2-3 terminal chạy `client.main` song song và thử đặt cùng 1 ghế để thấy cơ chế khoá giao dịch.

## Giao thức (protocol)
- Client gửi:
  ```json
  {"action":"login","data":{"username":"u","password":"p"}}
  ```
- Server trả:
  ```json
  {"ok":true,"data":{"token":"...","user":{...}},"error":null}
  ```

Mọi action khác gửi kèm `token` trong `data`.

## Checklist để giảng viên chấm (gợi ý)
- Có README rõ ràng
- Có lịch sử commit đều
- Có phân chia vai trò + issue/PR
- Có demo multi client

---
Nếu muốn nâng cấp:
- GUI (Tkinter) thay vì CLI
- Phân quyền admin quản lý phòng chiếu/giá vé
- Thêm giữ chỗ tạm thời (timeout) thay vì book ngay
