# Docker

## Overview
Docker containerizes the entire application stack (backend + frontend) for consistent deployment across environments.

## How It's Used in the Project

### 1. **Backend Container** (`backend/Dockerfile`)
- Python 3.11 slim base image
- Installs system dependencies (libgl1, libglib2.0-0 for OpenCV/PyYOLO)
- Installs Python packages from requirements.txt
- Starts 4 worker processes (ports 8001-8004) + 1 router (port 8000)
- Exposes port 8000 for external traffic

### 2. **Frontend Container** (`frontend/Dockerfile`)
- Multi-stage build: Node.js builder stage → Nginx server stage
- Stage 1: Builds React + Vite app, outputs to /dist
- Stage 2: Serves static assets via Nginx with proxy to backend
- Exposes port 80 (mapped to 5173 externally)

### 3. **Docker Compose** (`docker-compose.yml`)
- Orchestrates backend + frontend services
- Frontend depends on backend (waits for startup)
- Mounts shared volumes for YOLO weights persistence
- Maps ports: Frontend 5173→80, Backend 8000-8004→8000-8004

## Container Lifecycle

```
docker compose up -d --build
├── Build and start backend (Python/FastAPI)
├── Build and start frontend (Node/React/Nginx)
└── Create custom-weights volume for model persistence

docker compose down
└── Stop and remove all containers (volumes persist)

docker compose down -v
└── Remove containers AND volumes
```

## Key Benefits

- **Consistency** - Runs identically across dev, CI/CD, production
- **Isolation** - Backend and frontend run in separate containers
- **Persistence** - YOLO weights cached in Docker volumes
- **Easy Deployment** - One command startup with all dependencies

## Multi-Container Networking

- Services communicate via service names (backend:8000)
- Frontend proxy forwards /api/* to backend:8000
- All exposed to host machine on defined ports
