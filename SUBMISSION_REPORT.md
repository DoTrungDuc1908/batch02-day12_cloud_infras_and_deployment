# Day 12 Submission Report

Project: Day 12 - Deployment: Dua Agent Len Cloud  
Public API URL: `https://agent-api-production-3d7b.up.railway.app`  
Deployment platform: Railway  
Runtime: Docker image based on `python:3.11-slim`  
Storage/backing service: Railway Redis  
API key: provided separately. It is redacted as `<AGENT_API_KEY>` in this report.

## Deliverables

- `Solution.md`: answers for Code Lab Parts 1-5.
- `06-lab-complete/`: final production-ready agent.
- `06-lab-complete/Dockerfile`: multi-stage build, non-root runtime user.
- `06-lab-complete/docker-compose.yml`: local stack with Nginx, agent replicas, and Redis.
- `06-lab-complete/railway.toml`: Railway deployment config.
- `06-lab-complete/render.yaml`: Render deployment config.
- Public Railway URL: `https://agent-api-production-3d7b.up.railway.app`.

## Implemented Requirements

Functional:

- Agent answers questions through REST API: `POST /ask`.
- Conversation history is stored in Redis by `user_id`.
- Input validation is handled by Pydantic/FastAPI.

Non-functional:

- Dockerized with multi-stage build.
- Config loaded from environment variables.
- API key authentication through `X-API-Key`.
- Redis-backed rate limiting: 10 requests/minute/user.
- Redis-backed monthly cost guard: 10 USD/month/user.
- Liveness endpoint: `GET /health`.
- Readiness endpoint: `GET /ready`.
- Graceful shutdown handling with SIGTERM/SIGINT.
- Stateless design: history, budget, and rate data are stored in Redis.
- Structured JSON logging.
- Railway deployment with public URL.

## Production Readiness Check

Command:

```bash
python 06-lab-complete/check_production_ready.py
```

Result:

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

## Railway Deployment Notes

The application was deployed to the Railway service `agent-api`.

Important services:

- `agent-api`: FastAPI production agent
- `Redis`: Railway Redis database service

Redis issue encountered during deployment:

- Initial `/ready` call returned `Redis not ready: Timeout connecting to server`.
- Root cause: Redis service deployment was stopped/exited.
- Fix applied: redeployed Redis service with:

```bash
railway redeploy --service Redis --yes
```

After Redis redeploy, readiness passed:

```bash
curl https://agent-api-production-3d7b.up.railway.app/ready
```

```json
{"ready":true,"redis":"ok"}
```

## Public Endpoint Test Evidence

### Health Check

Command:

```bash
curl -v --max-time 10 https://agent-api-production-3d7b.up.railway.app/health
```

Observed result:

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

### Readiness Check

Command:

```bash
curl https://agent-api-production-3d7b.up.railway.app/ready
```

Final observed result:

```json
{"ready":true,"redis":"ok"}
```

### Ask Endpoint With Authentication

Command:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello from Railway"}'
```

Observed result:

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

### Authentication Failure

Command:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello"}'
```

Observed result:

```json
{"detail":"Invalid or missing API key. Include header: X-API-Key."}
```

### Authentication Success

Command:

```bash
curl -X POST https://agent-api-production-3d7b.up.railway.app/ask \
  -H "X-API-Key: <AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"student-1","question":"Hello"}'
```

Observed result:

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

### Rate Limit Test

Command:

```bash
for i in {1..15}; do
  curl -s -w "\nHTTP %{http_code}\n" -X POST https://agent-api-production-3d7b.up.railway.app/ask \
    -H "X-API-Key: <AGENT_API_KEY>" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"rate-test","question":"test"}'
done
```

Observed result:

- Requests 1-10 returned `HTTP 200`.
- Requests 11-15 returned `HTTP 429`.

Representative rate-limit response:

```json
{"detail":"Rate limit exceeded: 10 req/min"}
```

## Final Status

The repository satisfies the main Day 12 requirements:

- Code lab answers are documented in `Solution.md`.
- Final project is productionized in `06-lab-complete`.
- Public Railway deployment is available.
- Health, readiness, authentication, ask endpoint, Redis integration, and rate limiting were tested successfully.

Remaining operational note:

- The current implementation uses an offline mock LLM adapter to avoid requiring an OpenAI API key, as allowed by the lab. To use a real LLM, replace `06-lab-complete/app/mock_llm.py` with a real provider adapter and set `OPENAI_API_KEY`.
