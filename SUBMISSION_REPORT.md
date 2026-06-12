# Báo Cáo Nộp Bài Day 12

Sinh viên: Đỗ Trung Đức  
Mã sinh viên: 2A202600918  
Ngày nộp: 12/06/2026  

Tên bài: Day 12 - Deployment: Đưa Agent Lên Cloud  
URL API public: `https://agent-api-production-3d7b.up.railway.app`  
Nền tảng triển khai: Railway  
Runtime: Docker image dựa trên `python:3.11-slim`  
Backing service: Railway Redis  
API key: được cung cấp riêng, trong báo cáo được ẩn thành `<AGENT_API_KEY>`.

## 1. Các File Nộp Bài

- `Solution.md`: trả lời các bài Code Lab từ Part 1 đến Part 5.
- `REQUIREMENTS_COMPLETION_MATRIX.md`: ma trận đối chiếu toàn bộ yêu cầu/câu hỏi/checklist trong repo với bằng chứng hoàn thành.
- `06-lab-complete/`: project final production-ready agent.
- `06-lab-complete/Dockerfile`: Dockerfile multi-stage, chạy bằng non-root user.
- `06-lab-complete/docker-compose.yml`: stack local gồm Nginx, nhiều agent replicas và Redis.
- `06-lab-complete/railway.toml`: cấu hình deploy Railway.
- `06-lab-complete/render.yaml`: cấu hình deploy Render.
- Public Railway URL: `https://agent-api-production-3d7b.up.railway.app`.

## 2. Các Yêu Cầu Đã Hoàn Thành

### Functional

- Agent trả lời câu hỏi qua REST API: `POST /ask`.
- Conversation history được lưu trong Redis theo `user_id`.
- Input validation được xử lý bằng Pydantic/FastAPI.
- Có response lỗi rõ ràng cho thiếu API key, vượt rate limit, Redis chưa sẵn sàng và request body không hợp lệ.

### Non-functional

- Dockerized bằng multi-stage build.
- Config được đọc từ environment variables.
- API key authentication qua header `X-API-Key`.
- Rate limiting dùng Redis: 10 requests/phút/user.
- Cost guard dùng Redis: 10 USD/tháng/user.
- Liveness endpoint: `GET /health`.
- Readiness endpoint: `GET /ready`.
- Graceful shutdown với SIGTERM/SIGINT.
- Stateless design: history, budget và rate data đều nằm trong Redis.
- Structured JSON logging.
- Đã deploy lên Railway và có public URL hoạt động.

## 3. Kết Quả Production Readiness Check

Lệnh chạy:

```bash
python 06-lab-complete/check_production_ready.py
```

Kết quả:

```text
Production Readiness Check - Day 12 Lab

Required Files:
  PASS Dockerfile exists
  PASS docker-compose.yml exists
  PASS .dockerignore exists
  PASS .env.example exists
  PASS requirements.txt exists
  PASS railway.toml or render.yaml exists

Security:
  PASS .env in .gitignore
  PASS No hardcoded secrets in code

API Endpoints:
  PASS /health endpoint defined
  PASS /ready endpoint defined
  PASS Authentication implemented
  PASS Rate limiting implemented
  PASS Graceful shutdown (SIGTERM)
  PASS Structured logging (JSON)

Docker:
  PASS Multi-stage build
  PASS Non-root user
  PASS HEALTHCHECK instruction
  PASS Slim base image
  PASS .dockerignore covers .env
  PASS .dockerignore covers __pycache__

Result: 20/20 checks passed (100%)
```

## 4. Ghi Chú Triển Khai Railway

Ứng dụng được deploy vào Railway service `agent-api`.

Các service quan trọng:

- `agent-api`: FastAPI production agent.
- `Redis`: Railway Redis database service.

Trong quá trình deploy có gặp lỗi Redis:

- Ban đầu gọi `/ready` trả về: `Redis not ready: Timeout connecting to server`.
- Nguyên nhân: Redis service trên Railway đã bị dừng/exited.
- Cách xử lý: redeploy Redis service.

Lệnh đã dùng:

```bash
railway redeploy --service Redis --yes
```

Sau khi redeploy Redis, readiness check đã thành công:

```bash
curl https://agent-api-production-3d7b.up.railway.app/ready
```

Kết quả:

```json
{"ready":true,"redis":"ok"}
```

## 5. Bằng Chứng Test Public Endpoint

### 5.1. Health Check

Lệnh chạy:

```bash
curl -v --max-time 10 https://agent-api-production-3d7b.up.railway.app/health
```

Kết quả HTTP:

```http
HTTP/1.1 200 OK
```

Response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "uptime_seconds": 71.4,
  "total_requests": 2,
  "timestamp": "2026-06-12T10:34:28.280246+00:00"
}
```

### 5.2. Readiness Check

Lệnh chạy:

```bash
curl https://agent-api-production-3d7b.up.railway.app/ready
```

Kết quả cuối cùng:

```json
{"ready":true,"redis":"ok"}
```

### 5.3. Gọi `/ask` Với API Key Hợp Lệ

Lệnh chạy:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello from Railway"}'
```

Kết quả:

```json
{
  "user_id": "student-1",
  "question": "Hello from Railway",
  "answer": "The agent received your question and answered through the production API path.",
  "model": "gpt-4o-mini",
  "history_length": 1,
  "budget_used_usd": 0.000015,
  "timestamp": "2026-06-12T10:37:42.444917+00:00"
}
```

### 5.4. Test Thiếu API Key

Lệnh chạy:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello"}'
```

Kết quả:

```json
{"detail":"Invalid or missing API key. Include header: X-API-Key."}
```

Kết luận: API chặn request không có key, đúng yêu cầu authentication.

### 5.5. Test Có API Key Hợp Lệ

Lệnh chạy:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello"}'
```

Kết quả:

```json
{
  "user_id": "student-1",
  "question": "Hello",
  "answer": "This is a mock production agent response. Replace this adapter with a real LLM client when an API key is available.",
  "model": "gpt-4o-mini",
  "history_length": 3,
  "budget_used_usd": 0.000071,
  "timestamp": "2026-06-12T10:40:25.808143+00:00"
}
```

Kết luận: API nhận key hợp lệ và trả lời thành công.

### 5.6. Test Rate Limit

Lệnh chạy:

```bash
for i in {1..15}; do
  curl -s -w "\nHTTP %{http_code}\n" -X POST https://agent-api-production-3d7b.up.railway.app/ask \
    -H "X-API-Key: <AGENT_API_KEY>" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rate-test","question":"test"}'
done
```

Kết quả quan sát:

- Request 1-10 trả về `HTTP 200`.
- Request 11-15 trả về `HTTP 429`.

Response đại diện khi vượt rate limit:

```json
{"detail":"Rate limit exceeded: 10 req/min"}
```

Kết luận: rate limiting hoạt động đúng yêu cầu 10 requests/phút/user.

## 6. Trạng Thái Hoàn Thành

Repo đã đáp ứng các yêu cầu chính của Day 12:

- Đáp án Code Lab được ghi trong `Solution.md`.
- Tất cả câu hỏi thảo luận trong các README section đã được trả lời trực tiếp trong từng README.
- Toàn bộ yêu cầu cấp repo được đối chiếu trong `REQUIREMENTS_COMPLETION_MATRIX.md`.
- Final project đã được productionize trong `06-lab-complete`.
- Đã deploy lên Railway và có public URL hoạt động.
- Đã test thành công health, readiness, authentication, ask endpoint, Redis integration và rate limiting.

## 7. Ghi Chú Vận Hành

- Bản hiện tại dùng mock LLM offline để không cần OpenAI API key, đúng với yêu cầu lab cho phép dùng mock LLM.
- Nếu muốn dùng LLM thật, cần thay `06-lab-complete/app/mock_llm.py` bằng adapter gọi provider thật và set `OPENAI_API_KEY`.
- API key thật không được ghi trực tiếp trong báo cáo để tránh lộ secret. Khi chấm bài, API key có thể được cung cấp riêng cho giảng viên.
