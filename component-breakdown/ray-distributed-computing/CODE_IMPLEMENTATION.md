# Ray Implementation - Code Snippets

## Ray Actor Definition (`backend/ray_worker.py`)

```python
import ray
from PIL import Image
from ultralytics import YOLO
import torch

@ray.remote(num_gpus=0.25)  # Each actor gets 0.25 GPU (4 actors per GPU)
class YOLOWorkerActor:
    """
    A Ray actor that encapsulates a YOLOv8 model.
    Ray handles placement, scheduling, and resource management.
    """
    
    def __init__(self, model_name: str = "yolov8m.pt"):
        """Initialize actor with model."""
        self.model_name = model_name
        self.model = None  # Lazy load on first inference
        
    def _get_model(self) -> YOLO:
        """Lazy-load model on first call."""
        if self.model is None:
            torch.set_num_threads(1)
            self.model = YOLO(self.model_name)
            
            if torch.cuda.is_available():
                self.model.to('cuda')
                print(f"✅ Actor running on GPU")
            else:
                print(f"⚠️ Actor running on CPU")
        
        return self.model
    
    def run_inference(self, image: Image.Image, conf: float = 0.25):
        """
        Run YOLO inference.
        
        Ray automatically:
        - Serializes the image to send to worker
        - Schedules on GPU if available
        - Handles task failures
        """
        import time
        start = time.time()
        
        model = self._get_model()
        results = model(image, conf=conf, verbose=False)
        
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append({
                    "label": result.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "bbox": [x1, y1, x2 - x1, y2 - y1]
                })
        
        latency_ms = (time.time() - start) * 1000
        
        return {
            "detections": detections,
            "latency_ms": latency_ms,
            "model": self.model_name
        }
    
    def get_status(self):
        """Return actor status."""
        model = self._get_model()
        return {
            "model_loaded": True,
            "device": str(next(model.model.parameters()).device)
        }
```

## Ray Cluster Initialization

```python
import ray
import torch

def initialize_ray_cluster(num_workers: int = 4, num_gpus: float = 1.0):
    """
    Initialize Ray cluster with worker pool.
    
    Args:
        num_workers: Number of YOLO actors
        num_gpus: Total GPUs to allocate (auto-detected if available)
    """
    
    if not ray.is_initialized():
        # Initialize Ray with resource specification
        ray.init(
            num_cpus=4,
            num_gpus=num_gpus if torch.cuda.is_available() else 0,
            include_dashboard=False,  # Disable web UI for production
            log_to_driver=False
        )
    
    # Create pool of workers
    workers = []
    for i in range(num_workers):
        # Ray automatically schedules actors on available GPUs
        worker = YOLOWorkerActor.remote(model_name="yolov8m.pt")
        workers.append(worker)
    
    print(f"✅ Ray cluster: {num_workers} actors, {num_gpus} GPUs")
    return workers
```

## Integration with FastAPI Router

```python
from fastapi import FastAPI, UploadFile, File
from PIL import Image
import ray
import asyncio
import io

app = FastAPI()

# Global reference to Ray workers
ray_workers = []

@app.on_event("startup")
async def startup():
    global ray_workers
    ray_workers = initialize_ray_cluster(num_workers=4)

@app.on_event("shutdown")
async def shutdown():
    if ray.is_initialized():
        ray.shutdown()

@app.post("/api/detect")
async def detect(file: UploadFile = File(...)):
    """Detect objects using Ray distributed workers."""
    
    if not ray_workers:
        return {"error": "Ray not initialized"}
    
    # 1. Read image
    file_bytes = await file.read()
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    
    # 2. Select a Ray actor (could use load-balancing logic here)
    worker = ray_workers[0]  # or select via OR-Tools
    
    # 3. Submit task to Ray (returns Future)
    future = worker.run_inference.remote(image, conf=0.25)
    
    # 4. Get result (asyncio-compatible)
    result = await asyncio.to_thread(ray.get, future)
    
    return {
        "latency_ms": result["latency_ms"],
        "detections": result["detections"]
    }
```

## Ray + OR-Tools Hybrid Routing

```python
from ortools.linear_solver import pywraplp

def get_optimal_actor_with_ortools(workers, loads: dict) -> int:
    """
    Use OR-Tools to select best Ray actor based on load.
    
    OR-Tools solves: minimize max(worker_load[i])
    subject to: exactly one worker selected
    """
    
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return min(loads, key=loads.get)
    
    # Binary selection variables
    x = {i: solver.IntVar(0, 1, f"select_{i}") for i in range(len(workers))}
    
    # Constraint: select exactly one
    solver.Add(solver.Sum(x.values()) == 1)
    
    # Objective: minimize max load selected
    objective = solver.Objective()
    for i in range(len(workers)):
        objective.SetCoefficient(x[i], float(loads[i]))
    objective.SetMinimization()
    
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL:
        for i in range(len(workers)):
            if x[i].solution_value() > 0.5:
                return i
    
    return 0

@app.post("/api/detect")
async def detect_with_hybrid_routing(file: UploadFile):
    """Detect using Ray workers + OR-Tools routing."""
    
    # 1. OR-Tools selects best actor
    worker_loads = {i: 0 for i in range(len(ray_workers))}  # Would track real loads
    actor_idx = get_optimal_actor_with_ortools(ray_workers, worker_loads)
    
    # 2. Get selected Ray actor
    selected_actor = ray_workers[actor_idx]
    
    # 3. Submit to Ray
    file_bytes = await file.read()
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    
    future = selected_actor.run_inference.remote(image, conf=0.25)
    result = await asyncio.to_thread(ray.get, future)
    
    return result
```

## Ray Status Monitoring

```python
@app.get("/api/ray/status")
def ray_status():
    """Get Ray cluster status."""
    
    if not ray.is_initialized():
        return {"status": "not initialized"}
    
    # Get Ray cluster info
    info = ray.cluster_resources()
    
    # Check actor status
    actor_statuses = []
    for i, actor in enumerate(ray_workers):
        try:
            status = ray.get(actor.get_status.remote(), timeout=1)
            actor_statuses.append({
                "actor_id": i,
                "status": "healthy",
                "info": status
            })
        except:
            actor_statuses.append({
                "actor_id": i,
                "status": "unhealthy"
            })
    
    return {
        "cluster_resources": info,
        "actors": actor_statuses,
        "total_actors": len(ray_workers)
    }
```

## Quick Start Commands

```bash
# Install Ray with all dependencies
pip install ray[default]

# Or for GPU support
pip install ray[default]
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Start server with Ray backend
chmod +x backend/start.bat
# or on Windows
cd backend
python -m uvicorn router:app --port 8000 --reload

# Check Ray dashboard (if enabled)
# http://localhost:8265
```

## Configuration Options

```python
# Initialize Ray with custom settings
ray.init(
    num_cpus=4,              # CPU cores
    num_gpus=1.0,            # GPU count (can be fractional)
    memory=4e9,              # 4GB heap memory
    object_store_memory=2e9, # 2GB object store
    include_dashboard=False, # Disable web UI
    dashboard_host="0.0.0.0",
    dashboard_port=8265,
    log_to_driver=False,
    ignore_reinit_error=True
)

# Actor resource constraints
@ray.remote(
    num_cpus=1,     # 1 CPU per actor
    num_gpus=0.25,  # 0.25 GPU per actor (4 actors per GPU)
    resources={"custom": 1}  # Custom resource type
)
class MyActor:
    pass
```
