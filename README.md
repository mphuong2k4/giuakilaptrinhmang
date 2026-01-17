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

