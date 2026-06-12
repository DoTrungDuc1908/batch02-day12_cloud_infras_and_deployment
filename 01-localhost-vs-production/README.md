# Section 1 — Từ Localhost Đến Production

## Mục tiêu học
- Hiểu tại sao "it works on my machine" là vấn đề
- Nhận ra sự khác biệt giữa dev và production environment
- Áp dụng 4 nguyên tắc 12-factor cơ bản

---

## Ví dụ Basic — Agent "Kiểu Localhost"

```
develop/
├── app.py          # ❌ Anti-patterns: hardcode secrets, no config, no health check
├── .env.example
└── requirements.txt
```

### Chạy thử
```bash
cd develop
pip install -r requirements.txt
python app.py
# Truy cập: http://localhost:8000
```

### Những vấn đề trong code này:
1. API key hardcode trong code
2. Không có health check endpoint
3. Debug mode bật cứng
4. Không xử lý SIGTERM gracefully
5. Config không đến từ environment

---

## Ví dụ Advanced — 12-Factor Compliant Agent

```
production/
├── app.py          # ✅ Clean: config from env, health check, graceful shutdown
├── config.py       # ✅ Centralized config management
├── .env.example    # ✅ Template — không commit .env thật
└── requirements.txt
```

### Chạy thử
```bash
cd production
pip install -r requirements.txt
cp .env.example .env
# Sửa .env nếu cần
python app.py
```

### So sánh với Basic:

| | Basic (❌) | Advanced (✅) |
|--|-----------|--------------|
| Config | Hardcode trong code | Đọc từ env vars |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")` |
| Port | Cố định `8000` | Từ `PORT` env var |
| Health check | Không có | `GET /health` |
| Shutdown | Tắt đột ngột | Graceful — hoàn thành request hiện tại |
| Logging | `print()` | Structured JSON logging |

---

## Câu hỏi thảo luận

1. Điều gì xảy ra nếu bạn push code với API key hardcode lên GitHub public?
2. Tại sao stateless quan trọng khi scale?
3. 12-factor nói "dev/prod parity" — nghĩa là gì trong thực tế?

## Đáp án câu hỏi thảo luận

1. Nếu push API key hardcode lên GitHub public, key có thể bị crawler/bot quét chỉ trong vài phút. Người khác có thể dùng key đó để gọi API, gây phát sinh chi phí, vượt quota, khóa tài khoản, hoặc truy cập dữ liệu/hệ thống không được phép. Cách xử lý đúng là revoke/rotate key ngay, xóa secret khỏi lịch sử Git nếu cần, và chuyển sang dùng environment variables hoặc secret manager.

2. Stateless quan trọng khi scale vì nhiều instance không chia sẻ memory với nhau. Nếu conversation/session nằm trong RAM của một process, request sau có thể rơi vào instance khác và mất context. Khi state được đưa ra backing service như Redis/database, mọi instance đều đọc/ghi cùng một nguồn dữ liệu, có thể scale ngang, restart, rolling deploy mà không mất trạng thái.

3. Dev/prod parity nghĩa là môi trường development, staging và production càng giống nhau càng tốt: cùng Python version, dependency, Docker image, config style, backing services và cách chạy. Trong thực tế, ta dùng Docker, `requirements.txt`, env vars, mock/managed services tương đương và quy trình deploy nhất quán để giảm lỗi kiểu "works on my machine".
