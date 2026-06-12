# Lab 12 — Complete Production Agent

Kết hợp TẤT CẢ những gì đã học trong 1 project hoàn chỉnh.

## Checklist Deliverable

- [x] Dockerfile (multi-stage, < 500 MB)
- [x] docker-compose.yml (agent + redis + nginx)
- [x] .dockerignore
- [x] Health check endpoint (`GET /health`)
- [x] Readiness endpoint (`GET /ready`)
- [x] API Key authentication
- [x] Rate limiting
- [x] Cost guard
- [x] Config từ environment variables
- [x] Structured logging
- [x] Graceful shutdown
- [x] Public URL ready (Railway / Render config)

---

## Public API URL

Railway deployment:

```text
https://agent-api-production-3d7b.up.railway.app
```

Verification summary:

- `GET /health`: `200 OK`
- `GET /ready`: `200 OK`, Redis connected
- `POST /ask` without `X-API-Key`: `401 Unauthorized`
- `POST /ask` with valid `X-API-Key`: `200 OK`
- Rate limiting: first 10 requests/minute succeed, later requests return `429`
- Production readiness checker: `20/20` checks passed

Use the API key provided separately by the submitter/instructor channel.

```bash
curl https://agent-api-production-3d7b.up.railway.app/health
curl https://agent-api-production-3d7b.up.railway.app/ready

curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello"}'
```

---

## Cấu Trúc

```
06-lab-complete/
├── app/
│   ├── main.py         # Entry point — kết hợp tất cả
│   ├── config.py       # 12-factor config
│   ├── auth.py         # API Key authentication
│   ├── rate_limiter.py # Rate limiting
│   └── cost_guard.py   # Budget protection
├── Dockerfile          # Multi-stage, production-ready
├── docker-compose.yml  # Full stack: Nginx + agent + Redis
├── railway.toml        # Deploy Railway
├── render.yaml         # Deploy Render
├── .env.example        # Template
├── .dockerignore
└── requirements.txt
```

---

## Chạy Local

```bash
# 1. Setup
cp .env.example .env.local

# 2. Chạy với Docker Compose
docker compose up

# 3. Test
curl http://localhost/health

# 4. Lấy API key từ .env, test endpoint
API_KEY=dev-key-change-me-in-production
curl -H "X-API-Key: $API_KEY" \
     -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"user_id": "student-1", "question": "What is deployment?"}'
```

---

## Deploy Railway (< 5 phút)

```bash
# Cài Railway CLI
npm i -g @railway/cli

# Login và deploy
railway login
railway init
railway variables set AGENT_API_KEY=your-secret-key
railway variables set JWT_SECRET=your-jwt-secret
railway variables set REDIS_URL=redis://your-redis-url
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10
railway up

# Nhận public URL!
railway domain
```

---

## Deploy Render

1. Push repo lên GitHub
2. Render Dashboard → New → Blueprint
3. Connect repo → Render đọc `render.yaml`
4. Set secrets: `OPENAI_API_KEY` nếu dùng LLM thật, `AGENT_API_KEY`, `JWT_SECRET`
5. Deploy → Nhận URL!

---

## Kiểm Tra Production Readiness

```bash
python check_production_ready.py
```

Script này kiểm tra tất cả items trong checklist và báo cáo những gì còn thiếu.
