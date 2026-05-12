# Ray - Distributed Computing Framework

## Overview
Ray is an open-source distributed computing framework that manages the worker pool for YOLOv8 inference. It provides GPU scheduling, load balancing, fault tolerance, and automatic scaling.

## How It's Used in the Project

### 1. **Ray Actors** (`backend/ray_worker.py`)
- Each Ray Actor encapsulates a YOLOv8 model instance
- Actors are remote Python objects that run on Ray workers
- GPU resources automatically allocated: 0.25 GPU per actor (4 actors per GPU)
- Lazy initialization: models loaded only on first inference

### 2. **Hybrid Routing** (`backend/router.py`)
- FastAPI REST API receives requests from React frontend
- Router selects optimal Ray actor using OR-Tools optimization
- Request sent to Ray actor via remote task execution
- Ray handles:
  - Automatic GPU scheduling
  - Load balancing across actors
  - Fault recovery (restarts failed actors)
  - Resource management (GPU/CPU allocation)

### 3. **Architecture: Ray + OR-Tools Synergy**

```
React Frontend
       ↓
FastAPI Router :8000
       ↓
OR-Tools ILP Solver
(Select optimal actor by load)
       ↓
Ray Driver (scheduler)
       ↓
Ray Workers (GPU cluster)
├── Actor 0 (GPU 0.25)
├── Actor 1 (GPU 0.25)
├── Actor 2 (GPU 0.25)
└── Actor 3 (GPU 0.25)
       ↓
YOLOv8 Inference
```

## Key Features

- **Distributed Execution** - Tasks run on remote workers
- **Automatic GPU Scheduling** - Ray allocates fractional GPUs
- **Fault Tolerance** - Failed tasks automatically retried
- **Actor Model** - Stateful remote objects (encapsulate models)
- **Async Integration** - Works with FastAPI's async/await
- **Scalability** - Easily add more actors or machines

## Ray vs Traditional Worker Pool

| Feature | Ray | HTTP Workers |
|---------|-----|--------------|
| **Serialization** | Automatic | Manual (multipart/form-data) |
| **GPU Sharing** | Native (fractional GPU) | Manual setup |
| **Fault Tolerance** | Built-in | Manual |
| **Latency** | ~5ms per task | ~15-20ms (HTTP overhead) |
| **Scaling** | Automatic | Manual |
| **Debugging** | Ray Dashboard | Server logs |

## Performance Improvements

- **Reduced Latency**: No HTTP serialization overhead
- **Better GPU Utilization**: Multiple actors can share 1 GPU
- **Automatic Scaling**: Ray adds workers as needed
- **Fault Recovery**: Failed actors automatically restarted

## Components

- **Ray Head**: Central scheduler (runs on main machine)
- **Ray Workers**: Compute nodes (can be remote machines)
- **Actor Pool**: 4 YOLOv8 actors, each 0.25 GPU
- **OR-Tools Router**: Selects optimal actor per request
