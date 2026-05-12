# Real-Time Object Detection Analytics System

Full-stack object detection app with:

- Frontend: React + Vite
- Backend: FastAPI + Ultralytics YOLOv8
- Router: OR-Tools-based request routing across 4 backend worker ports
- Ray support: optional distributed worker layer for Python 3.11/3.12 environments

This README is written from a tested run on Windows (April 18, 2026).

## Project Structure

- `frontend/`: React dashboard
- `backend/`: FastAPI API, YOLO model loading/inference, OR-Tools router
- `docker-compose.yml`: one-command Docker startup
- `k8s/`: Kubernetes manifests

## Quick Start (Recommended: Docker)

### Prerequisites

- Docker Desktop installed and running
- Git

### 1. Clone and open

```powershell
git clone <your-repo-url>
cd "AI212 Project"
```

### 2. Build and start

```powershell
docker compose up -d --build
```

First build can take several minutes because Python dependencies and model tooling are heavy.

### 3. Open the app

- Frontend UI: http://localhost:5173
- Backend health: http://localhost:8000/api/health

### 4. Stop containers

```powershell
docker compose down
```

To also remove volumes:

```powershell
docker compose down -v
```

## Local Run (Without Docker)

Use this if you want easier debugging in VS Code.

### Prerequisites
- Python 3.14 works for the HTTP fallback path (router will use HTTP workers)
- Python 3.11 or 3.12 is required if you want Ray enabled locally (recommended for Ray)
	- Use the helper scripts in `backend/` to create a 3.11 virtualenv and install packages.
		- Windows (PowerShell): `backend\setup_py311.ps1`
		- Linux / WSL: `backend/setup_py311.sh`
- Node.js 20+

### Terminal 1: Start backend cluster

```powershell
cd backend
# If you created a Python 3.11 venv and want Ray enabled, activate it first.
# PowerShell (3.11):
#   .\\venv311\\Scripts\\Activate.ps1
# Then run the start wrapper:
./start.bat
```

This starts:

- Worker APIs on ports `8001`, `8002`, `8003`, `8004`
- Router API on port `8000`
- Ray is optional; if your local Python is not 3.11/3.12, the router keeps using the HTTP worker path

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

### Terminal 2: Start frontend dev server

```powershell
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

The Vite config proxies `/api/*` calls to `http://localhost:8000`.

## How to Use

1. Open the UI.
2. Choose `Upload image` or `Webcam`.
3. Run detection.
4. View detections and latency.
5. Use the Analytics tab for health and performance trends.

## Common Issues

### Port already in use

If `8000` or `5173` is busy, stop existing processes/containers, then retry.

### Docker build is slow

First build is expected to be slow due to dependency downloads.

### First inference is slow

Expected behavior. The YOLO model is loaded and warmed up on first request.

## API

- `POST /api/detect` (multipart form field: `file`)
- `GET /api/health`

## Notes

- Model weights are loaded from `backend/weights/` when available.
- Kubernetes manifests are available in `k8s/` for deployment experiments.
