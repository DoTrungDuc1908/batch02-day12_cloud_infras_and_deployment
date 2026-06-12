# Solution.md - Day 12 Code Lab Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns in `01-localhost-vs-production/develop/app.py`

1. Secrets/config are hardcoded in source code, which can leak when pushed to Git.
2. Port is fixed in code instead of being read from `PORT`.
3. Debug/development behavior is coupled to runtime code.
4. No `/health` endpoint, so a platform cannot know whether the app is alive.
5. No readiness endpoint, so traffic may be routed before dependencies are ready.
6. Logging uses simple development output instead of structured logs.
7. No graceful shutdown path for SIGTERM from containers or cloud platforms.
8. Local state/config assumptions make dev and production environments drift.

### Exercise 1.2: Basic version

Run:

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
curl -X POST "http://localhost:8000/ask?question=hello"
```

Observation: the app can answer locally, but it is not production-ready because config, health, logging, and shutdown behavior are not cloud-friendly.

### Exercise 1.3: Basic vs Advanced

| Feature | Basic | Advanced | Why it matters |
|---|---|---|---|
| Config | Hardcoded | Environment variables | Same code can run across local, staging, and production. |
| Secrets | In source code | Read from env | Prevents accidental secret leaks in Git. |
| Port | Fixed `8000` | Uses `PORT` | Cloud platforms assign ports dynamically. |
| Health check | Missing | `GET /health` | Load balancers and platforms can restart unhealthy containers. |
| Logging | `print()` style | Structured JSON | Logs are searchable and machine-readable. |
| Shutdown | Abrupt | Graceful SIGTERM handling | In-flight requests can finish before the process exits. |

Checkpoint: hardcoded secrets are dangerous, env vars keep config portable, health checks enable platform automation, and graceful shutdown improves reliability.

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile basics

1. Base image: a Python image such as `python:3.11-slim`, which provides the OS layer and Python runtime.
2. Working directory: usually `/app`, the directory where application code is copied and run.
3. `COPY requirements.txt .` happens before copying source code so Docker can cache dependency installation when only app code changes.
4. `CMD` provides the default command and can be overridden; `ENTRYPOINT` defines the executable that is harder to override and is useful for fixed container behavior.

### Exercise 2.2: Build and run

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8000:8000 my-agent:develop
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
docker images my-agent:develop
```

The container gives a reproducible runtime independent of the host Python setup.

### Exercise 2.3: Multi-stage build

Stage 1 installs/builds dependencies with build tools. Stage 2 starts from a smaller runtime image and copies only the installed packages and app files. The final image is smaller and safer because it excludes compilers, caches, and build-only files.

### Exercise 2.4: Docker Compose architecture

Architecture:

```text
Client -> Nginx/load balancer -> Agent service(s) -> Redis
```

Run:

```bash
docker compose -f 02-docker/production/docker-compose.yml up
curl http://localhost/health
curl http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain microservices"}'
```

Checkpoint: Docker gives parity, multi-stage builds reduce image size, Compose runs multi-service stacks, and logs/exec are the main debugging tools.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway

Expected workflow:

```bash
cd 03-cloud-deployment/railway
npm i -g @railway/cli
railway login
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key
railway up
railway domain
```

Validation:

```bash
curl https://your-agent.railway.app/health
curl https://your-agent.railway.app/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Am I on the cloud?"}'
```

### Exercise 3.2: Render

Render uses `render.yaml` as infrastructure as code. The platform reads build/start commands, service type, health path, and environment variable definitions from the YAML file. Railway uses `railway.toml` plus CLI/project configuration. Render is more explicit in the repo; Railway is faster for prototypes.

### Exercise 3.3: GCP Cloud Run

`cloudbuild.yaml` describes CI/CD build and deploy steps. `service.yaml` describes the Cloud Run service: container image, env vars, port, scaling, and health/service settings. Cloud Run is more production-oriented than Railway/Render but requires more cloud setup.

Checkpoint: deploy to at least one platform, verify a public URL, set env vars in the platform dashboard/CLI, and inspect cloud logs when it fails.

## Part 4: API Security

### Exercise 4.1: API key authentication

The API checks the `X-API-Key` header before serving `/ask`. Missing or invalid keys return `401 Unauthorized`. Key rotation is done by changing `AGENT_API_KEY` in the environment and redeploying/restarting the service.

Test:

```bash
cd 04-api-gateway/develop
set AGENT_API_KEY=secret-key-123
python app.py
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

### Exercise 4.2: JWT authentication

JWT flow:

1. Client sends username/password to token endpoint.
2. Server validates credentials.
3. Server signs a token with a secret and expiration.
4. Client sends `Authorization: Bearer <token>`.
5. Server verifies signature and expiry before allowing access.

### Exercise 4.3: Rate limiting

The production pattern should use Redis with a sliding window or token bucket. This lab uses a sliding window in the final project: old timestamps are removed, current requests are counted, and requests over the limit receive `429 Too Many Requests`.

### Exercise 4.4: Cost guard

Correct logic:

```python
month_key = datetime.now().strftime("%Y-%m")
key = f"budget:{user_id}:{month_key}"
current = float(redis.get(key) or 0)
if current + estimated_cost > 10:
    raise HTTPException(status_code=402, detail="Monthly budget exceeded")
redis.incrbyfloat(key, estimated_cost)
redis.expire(key, 32 * 24 * 3600)
```

Checkpoint: public APIs need auth, rate limiting protects capacity, and cost guard protects paid LLM usage.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness

Expected implementation:

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        redis_client.ping()
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
```

`/health` is a liveness check. `/ready` confirms dependencies are available before the load balancer sends traffic.

### Exercise 5.2: Graceful shutdown

The app should handle SIGTERM/SIGINT, stop accepting new work through the server lifecycle, finish in-flight requests when possible, close external connections, and log shutdown.

### Exercise 5.3: Stateless design

Incorrect:

```python
conversation_history = {}
```

Correct:

```python
redis_client.lpush(f"history:{user_id}", json.dumps(exchange))
redis_client.ltrim(f"history:{user_id}", 0, history_limit - 1)
```

State belongs in Redis or another backing service so any instance can answer the next request.

### Exercise 5.4: Load balancing

Run:

```bash
docker compose up --scale agent=3
```

Expected architecture:

```text
Client -> Nginx -> Agent replica 1
                -> Agent replica 2
                -> Agent replica 3
All replicas -> Redis
```

### Exercise 5.5: Stateless test

Create conversation history, kill one agent instance, then continue the same conversation. The next request should still see history because the state is in Redis, not process memory.

Checkpoint: health checks, graceful shutdown, stateless Redis storage, and load balancing are the core reliability/scaling requirements.

## Final Project Summary

The completed implementation in `06-lab-complete` includes:

- Multi-stage Dockerfile using `python:3.11-slim`
- Non-root container user
- Docker Compose stack with agent, Redis, and Nginx
- API key authentication
- Redis sliding-window rate limiting at 10 requests/minute/user
- Redis monthly budget guard at $10/user/month
- Redis-backed conversation history
- `/health`, `/ready`, and protected `/metrics`
- Structured JSON logging
- Graceful SIGTERM/SIGINT logging and FastAPI lifespan cleanup
- Railway and Render deployment config

Deployment result:

- Public API URL: `https://agent-api-production-3d7b.up.railway.app`
- `GET /health`: passed with `200 OK`
- `GET /ready`: passed with Redis status `ok`
- `POST /ask` without API key: returned `401`
- `POST /ask` with API key: returned `200`
- Rate limit test: returned `429` after 10 requests/minute for the same `user_id`
- Production readiness checker: `20/20` checks passed

See `SUBMISSION_REPORT.md` for the final deployment and test evidence.

For the full cross-check of every repository requirement source, see `REQUIREMENTS_COMPLETION_MATRIX.md`.
