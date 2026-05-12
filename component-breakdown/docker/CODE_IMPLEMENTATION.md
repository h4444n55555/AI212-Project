# Docker Implementation - Code Snippets

## Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and YOLOv8
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Generate start script: 4 workers + 1 router
RUN echo '#!/bin/bash\n\
uvicorn main:app --port 8001 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8002 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8003 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8004 --host 127.0.0.1 --log-level critical &\n\
sleep 2\n\
uvicorn router:app --port 8000 --host 0.0.0.0\n\
' > start.sh && chmod +x start.sh

# Expose router port
EXPOSE 8000 8001 8002 8003 8004

# Run startup script
CMD ["./start.sh"]
```

## Frontend Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Build with Node.js
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build with Vite
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built artifacts from Stage 1
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx config (includes API proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
```

## Nginx Configuration (`frontend/nginx.conf`)

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Serve static files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Docker Compose Configuration

```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"    # Router
      - "8001:8001"    # Worker 1
      - "8002:8002"    # Worker 2
      - "8003:8003"    # Worker 3
      - "8004:8004"    # Worker 4
    volumes:
      - custom-weights:/app/weights
    environment:
      - PYTHONUNBUFFERED=1

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "5173:80"      # Maps to Nginx port 80
    depends_on:
      - backend
    environment:
      - BACKEND_URL=http://backend:8000

volumes:
  custom-weights:
    driver: local
```

## Common Commands

```bash
# Build and start all containers (background mode)
docker compose up -d --build

# View logs from all services
docker compose logs -f

# View logs from specific service
docker compose logs -f backend

# Stop all containers
docker compose stop

# Remove containers (keep volumes)
docker compose down

# Remove everything including volumes
docker compose down -v

# Rebuild specific service
docker compose build --no-cache backend

# Run shell in running container
docker compose exec backend /bin/bash
```

## Build Pipeline

```
Push Code → Docker Build → Layer Caching → Image Push → Compose Pull/Run
```
