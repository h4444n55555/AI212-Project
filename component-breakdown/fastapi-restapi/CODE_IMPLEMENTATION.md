# FastAPI Implementation - Code Snippets

## Worker API (`backend/main.py`)

```python
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Detect API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models with type validation
class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: list[float]  # [x, y, w, h]

class DetectResponse(BaseModel):
    latency_ms: float
    detections: list[DetectionOut]

# Main detection endpoint
@app.post("/api/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)):
    """Accepts image file, runs YOLO detection, returns results"""
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # Run inference in background thread to avoid blocking event loop
    detections, latency_ms = await asyncio.to_thread(run_inference, image)
    
    return DetectResponse(
        latency_ms=latency_ms,
        detections=detections
    )

# Health check endpoint
@app.get("/api/health", response_model=HealthResponse)
def health_metrics():
    """Returns system metrics for monitoring"""
    mem_info = psutil.virtual_memory()
    return HealthResponse(
        cpu_percent=psutil.cpu_percent(interval=0.0),
        mem_used_gb=round(mem_info.used / (1024**3), 2),
        mem_total_gb=round(mem_info.total / (1024**3), 2),
        status="ok"
    )
```

## Router API (`backend/router.py`)

```python
from fastapi import FastAPI, UploadFile, File
import httpx

app = FastAPI(title="Edge Router / OR-Tools Proxy")

WORKER_PORTS = [8001, 8002, 8003, 8004]
worker_loads: Dict[int, int] = {p: 0 for p in WORKER_PORTS}

# Main proxy endpoint with OR-Tools routing
@app.post("/api/detect")
async def proxy_detect(file: UploadFile = File(...)):
    # 1. Use OR-Tools to find optimal worker
    target_port = get_optimal_worker_ortools()
    
    # 2. Track request queue
    worker_loads[target_port] += 1
    
    try:
        file_bytes = await file.read()
        target_url = f"http://127.0.0.1:{target_port}/api/detect"
        
        # 3. Proxy request to worker
        files = {"file": (file.filename, file_bytes, file.content_type)}
        response = await client.post(target_url, files=files)
        
        return response.json()
        
    finally:
        # 4. Decrement queue tracking
        worker_loads[target_port] -= 1
```

## Launch Commands

```bash
# Start single worker on port 8001
uvicorn main:app --port 8001 --host 127.0.0.1

# Start router on port 8000
uvicorn router:app --port 8000 --host 0.0.0.0
```
