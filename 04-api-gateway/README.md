# Section 4 — API Gateway & Security

## Mục tiêu học
- Hiểu tại sao cần lớp bảo vệ trước agent
- Implement API Key authentication
- Implement JWT authentication (nâng cao)
- Rate limiting và cost protection

---

## Ví dụ Basic — API Key Authentication

```
develop/
├── app.py              # Agent với API Key auth
├── test_auth.py        # Test script
└── requirements.txt
```

### Chạy thử
```bash
cd develop
pip install -r requirements.txt
AGENT_API_KEY=my-secret-key python app.py

# Test với key hợp lệ
curl -H "X-API-Key: my-secret-key" http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "hello"}'

# Test không có key → 401
curl http://localhost:8000/ask -X POST \
     -H "Content-Type: application/json" \
     -d '{"question": "hello"}'
```

---

## Ví dụ Advanced — JWT + Rate Limiting + Cost Guard

```
production/
├── app.py              # Full security stack
├── auth.py             # JWT token logic
├── rate_limiter.py     # In-memory rate limiter
├── cost_guard.py       # Token budget và spending alerts
├── test_advanced.py    # Test suite
└── requirements.txt
```

### Chạy thử
```bash
cd production
pip install -r requirements.txt
python app.py

# Lấy JWT token
curl -X POST http://localhost:8000/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "student", "password": "demo123"}'

# Dùng token
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "what is docker?"}'

# Test rate limit: spam 20 requests liên tiếp
python test_advanced.py --test rate-limit
```

---

## Luồng bảo vệ

```
Request
  → Auth Check (401 nếu fail)
  → Rate Limit (429 nếu vượt quota)
  → Input Validation (422 nếu invalid)
  → Cost Check (402 nếu hết budget)
  → Agent (200 nếu mọi thứ OK)
```

---

## Câu hỏi thảo luận

1. Khi nào nên dùng API Key vs JWT vs OAuth2?
2. Rate limit nên đặt bao nhiêu request/phút cho một AI agent?
3. Nếu API key bị lộ, bạn phát hiện và xử lý như thế nào?

## Đáp án câu hỏi thảo luận

1. API Key phù hợp cho service-to-service, demo, internal tools hoặc client ít phức tạp, nơi chỉ cần xác thực một secret cố định. JWT phù hợp khi cần danh tính user, role/claim, token hết hạn và auth flow nhẹ cho app riêng. OAuth2 phù hợp cho hệ thống nhiều người dùng/third-party integrations, delegated access, SSO, scopes và quản trị quyền chuẩn hơn.

2. Rate limit phụ thuộc chi phí model, latency và loại user. Với lab này đặt `10 req/min/user` để dễ quan sát và bảo vệ chi phí. Với production thật có thể tách tier: free 5-10 req/min, authenticated paid 30-120 req/min, admin/internal cao hơn; đồng thời giới hạn thêm theo ngày/tháng và theo token/cost chứ không chỉ request count.

3. Nếu API key bị lộ: revoke/rotate key ngay, cập nhật secret trong Railway/Render/secret manager, redeploy service, kiểm tra logs để tìm request bất thường, reset quota/budget nếu cần, thông báo người liên quan, và quét Git history/build logs để xóa secret. Sau đó thêm guardrail: không commit `.env`, secret scanning, short-lived tokens, rate limit và cost guard.
