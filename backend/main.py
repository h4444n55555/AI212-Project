import io
import asyncio
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil
from PIL import Image

from model import run_inference

app = FastAPI(title="Detect API")

# Allow the Vite dev server to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: list[float]  # [x, y, w, h]

class DetectResponse(BaseModel):
    latency_ms: float
    detections: list[DetectionOut]

@app.post("/api/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)):
    """
    Accepts an uploaded image file, runs YOLOv8 object detection,
    and returns a list of bounding boxes + latencies.
    """
    # Read the uploaded file bytes
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # Run YOLOv8 inference concurrently in a background thread to prevent blocking the FastAPI event loop
    detections, latency_ms = await asyncio.to_thread(run_inference, image)
    
    return DetectResponse(
        latency_ms=latency_ms,
        detections=detections
    )

class HealthResponse(BaseModel):
    cpu_percent: float
    mem_used_gb: float
    mem_total_gb: float
    status: str

@app.get("/api/health", response_model=HealthResponse)
def health_metrics():
    """Returns current system metrics for the Analytics dashboard."""
    # psutil uses percentages directly; memory uses bytes -> GB
    mem_info = psutil.virtual_memory()
    return HealthResponse(
        cpu_percent=psutil.cpu_percent(interval=0.0),
        mem_used_gb=round(mem_info.used / (1024**3), 2),
        mem_total_gb=round(mem_info.total / (1024**3), 2),
        status="ok"
    )
