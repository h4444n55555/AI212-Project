# FastAPI & REST API

## Overview
FastAPI is used to build the backend REST API for the object detection system. It handles HTTP requests from the React frontend and serves inference results.

## How It's Used in the Project

### 1. **Worker APIs** (`backend/main.py`)
- Each of the 4 backend worker processes runs a FastAPI instance on ports 8001-8004
- Exposes `/api/detect` endpoint for object detection inference
- Exposes `/api/health` endpoint for system metrics

### 2. **Router API** (`backend/router.py`)
- Main FastAPI instance running on port 8000
- Acts as an intelligent load balancer using OR-Tools
- Receives requests from React frontend and routes them to optimal worker
- Proxies responses back to frontend

## Key Features Used

- **CORS Middleware** - Allows React frontend (localhost:5173) to communicate with backend
- **File Upload Handling** - Accepts multipart image uploads via `FastAPI.File`
- **Async/Await** - Runs inference in background threads to prevent event loop blocking
- **Pydantic Models** - Type-safe request/response validation

## Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/detect` | Upload image and run YOLO detection |
| GET | `/api/health` | Get CPU & memory metrics |

## Response Example

```json
{
  "latency_ms": 145.32,
  "detections": [
    {
      "label": "person",
      "confidence": 0.92,
      "bbox": [100, 50, 200, 300]
    }
  ]
}
```
