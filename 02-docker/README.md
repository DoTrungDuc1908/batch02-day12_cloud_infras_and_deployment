# Section 2 — Docker: Đóng Gói Agent Thành Container

## Mục tiêu học
- Hiểu container là gì và tại sao cần nó
- Viết Dockerfile đúng cách (single vs multi-stage)
- Dùng Docker Compose để chạy multi-service stack
- Tối ưu image size xuống dưới 500 MB

---

## Ví dụ Basic — Dockerfile Đơn Giản

```
develop/
├── app.py
├── Dockerfile          # Single-stage, dễ hiểu
├── .dockerignore
└── requirements.txt
```

### Chạy thử
```bash
# IMPORTANT: Build from project root!
cd ../..  # Go to project root

# Build image
docker build -f 02-docker/develop/Dockerfile -t agent-develop .

# Xem size
docker images agent-develop

# Chạy container
docker run -p 8000:8000 agent-develop

# Test
curl http://localhost:8000/health
```

---

## Ví dụ Advanced — Multi-Stage + Docker Compose

```
production/
├── app.py
├── Dockerfile              # Multi-stage build → image nhỏ hơn nhiều
├── docker-compose.yml      # Full stack: agent + vector store + redis
├── nginx/
│   └── nginx.conf          # Reverse proxy
├── .dockerignore
└── requirements.txt
```

### Chạy thử
```bash
# From project root
cd ../..  # if not already there

# Khởi động toàn bộ stack (1 lệnh!)
docker compose -f 02-docker/production/docker-compose.yml up

# Xem các service đang chạy
docker compose -f 02-docker/production/docker-compose.yml ps

# Test agent qua Nginx
curl http://localhost/health

# Dừng toàn bộ
docker compose -f 02-docker/production/docker-compose.yml down
```

### So sánh image size:

```bash
# Basic vs Advanced
docker images | grep agent
# agent-basic    ~  800 MB  ← python:3.11 base
# agent-advanced ~  160 MB  ← python:3.11-slim + multi-stage
```

---

## Lý thuyết: Tại Sao Multi-Stage?

```dockerfile
# Stage 1: Builder — có đầy đủ tools để compile deps
FROM python:3.11 AS builder   # 1 GB
RUN pip install ...            # thêm deps vào layer này

# Stage 2: Runtime — chỉ copy những gì cần chạy
FROM python:3.11-slim          # 150 MB ← bắt đầu từ image sạch
COPY --from=builder ...        # copy chỉ /site-packages
```

**Kết quả:** Final image chỉ có runtime, không có pip, không có build tools → nhỏ và an toàn hơn.

---

## Câu hỏi thảo luận

1. Tại sao `COPY requirements.txt .` rồi `RUN pip install` TRƯỚC khi `COPY . .`?
2. `.dockerignore` nên chứa những gì? Tại sao `venv/` và `.env` quan trọng?
3. Nếu agent cần đọc file từ disk, làm sao mount volume vào container?

## Đáp án câu hỏi thảo luận

1. `COPY requirements.txt .` trước rồi mới `RUN pip install` giúp Docker cache layer cài dependencies. Khi chỉ sửa code app, layer dependencies không đổi nên build nhanh hơn. Nếu `COPY . .` trước, mọi thay đổi nhỏ trong source đều làm invalid cache và phải cài lại packages.

2. `.dockerignore` nên chứa các file/thư mục không cần đưa vào image: `.git/`, `__pycache__/`, `*.pyc`, `venv/`, `.venv/`, `.env`, `.env.*`, log files, IDE files, test/cache artifacts. `venv/` quan trọng vì virtualenv local thường lớn, phụ thuộc OS và làm image phình to. `.env` quan trọng vì chứa secret như API key/password, tuyệt đối không được copy vào image hoặc gửi lên build context.

3. Nếu agent cần đọc file từ disk, mount volume khi chạy container. Ví dụ Docker CLI: `docker run -v $(pwd)/data:/app/data -p 8000:8000 my-agent`. Với Docker Compose: thêm `volumes: - ./data:/app/data:ro` nếu chỉ đọc, hoặc bỏ `:ro` nếu cần ghi. Trong production nên dùng managed storage/object storage hoặc volume được platform hỗ trợ.
