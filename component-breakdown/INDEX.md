# Component Breakdown Index

## Project Technology Stack Documentation

This folder contains detailed documentation for each major technology and framework used in the **AI212 Object Detection Project**.

---

## 📁 Component Folders

### ✅ Documented Components

1. **[FastAPI & RestAPI](./fastapi-restapi/)**
   - Backend REST API framework
   - Worker and Router implementations
   - Pydantic models and async handling
   - Status: FULLY USED

2. **[React & Node.js](./react-nodejs/)**
   - Frontend UI framework
   - Component-based architecture
   - Vite build tool pipeline
   - Hot reload development server
   - Status: FULLY USED

3. **[Docker](./docker/)**
   - Container images for backend & frontend
   - Multi-stage builds for optimization
   - Docker Compose orchestration
   - Volume management for model weights
   - Status: FULLY USED

4. **[Kubernetes](./kubernetes/)**
   - Production deployment manifests
   - Backend & Frontend deployments
   - Persistent volume claims
   - Service discovery and load balancing
   - Status: CONFIGURED (optional deployment)

5. **[ML Model - YOLOv8](./ml-model-yolov8/)**
   - YOLO object detection model
   - Lazy-loading and caching mechanism
   - GPU acceleration support
   - Inference pipeline
   - Status: CORE COMPONENT

6. **[Optimization - OR-Tools](./optimization-ortools/)**
   - Google OR-Tools linear solver
   - Intelligent request routing
   - Load balancing across workers
   - Optimization algorithms
   - Status: CORE COMPONENT

7. **[Ray - Distributed Computing](./ray-distributed-computing/)** ⭐ NEW
   - Distributed computing framework
   - Ray Actors for YOLOv8 workers
   - Automatic GPU scheduling
   - Fault tolerance and scaling
   - Integrated with OR-Tools routing (optional execution path)
   - Status: INTEGRATED (Python 3.11/3.12 runtime)

---

## ❌ Not Used Components

The following components were mentioned but are **NOT** used in this project:

- **Express** - Node.js web framework (not used; FastAPI for backend instead)

---

## 📊 Updated Architecture Overview (Tested Mode + Optional Ray)

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Port 5173)              │
│                 (Vite Dev Server + Node.js)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                    HTTP /api/
                         │
┌────────────────────────▼────────────────────────────────────┐
│            FastAPI Router (Port 8000)                        │
│        ┌─────────────────────────────────────────┐          │
│        │   OR-Tools Optimization Layer           │          │
│        │   (Select least-loaded worker)          │          │
│        └─────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────┘
                         │
         HTTP to worker ports (tested mode)
                         │
         ┌───────────────▼───────────────┐
         │ FastAPI Worker Pool           │
         │ Ports: 8001, 8002, 8003, 8004 │
         └───────────────┬───────────────┘
                         │
                       YOLOv8m
                    (FP16 inference)

Optional path (Python 3.11/3.12):
Router -> Ray Driver -> Ray Actors -> YOLOv8m
```

---

## 🎯 Key Architecture Updates

### Current tested mode (HTTP + OR-Tools):
- 4 FastAPI processes on ports 8001-8004
- OR-Tools ILP selects least-loaded worker
- Router returns `worker_id` and `routing_mode`
- Verified end-to-end with frontend + backend

### Optional Ray mode (Python 3.11/3.12):
- Ray Cluster with Actor instances
- Automatic GPU scheduling (fractional GPU)
- Same OR-Tools routing concept for actor selection
- Fault tolerance and actor restart support


---

## 🚀 Quick Start References

### Local Development
```bash
# Terminal 1: Backend
cd backend
./start.bat  # Starts 4 workers + router

# Terminal 2: Frontend
cd frontend
npm install
npm run dev  # Starts Vite on port 5173
```

### Docker Deployment
```bash
docker compose up -d --build
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/api/health
```

### Kubernetes Deployment
```bash
kubectl apply -f k8s/
# Check status: kubectl get deployments
```

---

## 📚 Each Component Contains

Each component folder has:

1. **README.md** - High-level overview and use cases
2. **CODE_IMPLEMENTATION.md** - Code snippets and examples

---

## 🔗 Key Technologies Summary

| Technology | Purpose | Version |
|-----------|---------|---------|
| **FastAPI** | Backend REST API | ≥0.115.0 |
| **Uvicorn** | ASGI Server | ≥0.30.0 |
| **React** | Frontend UI | ^19.2.4 |
| **Vite** | Build tool | ^8.0.4 |
| **Node.js** | JavaScript runtime | 20+ |
| **YOLOv8** | Object Detection | Ultralytics ≥8.3.0 |
| **Ray** | Distributed Computing | ≥2.0.0 ⭐ NEW |
| **OR-Tools** | Optimization | ≥9.10.0 |
| **Docker** | Containerization | Latest |
| **Kubernetes** | Orchestration | 1.24+ |
| **Nginx** | Web server | Alpine |
| **Python** | Backend language | 3.11+ (Ray optional on 3.11/3.12) |

---

## 🎯 Your Next Steps

1. **Review each component** - Start with README.md in folders
2. **Study code implementation** - Check CODE_IMPLEMENTATION.md for actual code
3. **Test locally** - Use start.bat / npm run dev
4. **Deploy to Docker** - Use docker-compose up
5. **Scale with Kubernetes** - Deploy manifests in k8s/

---

## 📝 Notes

- **Not included**: Actual model weights (downloaded on first run)
- **Size**: YOLOv8n (~6MB), YOLOv8m (~49MB)
- **GPU Support**: Automatic detection & usage if CUDA available
- **Scalability**: Easily add more workers by extending router configuration

---

Generated: May 2, 2026
