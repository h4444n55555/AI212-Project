# YOLOv8 Implementation - Code Snippets

## Model Loading & Singleton Pattern (`backend/model.py`)

```python
"""
model.py — Lazy-loaded YOLOv8 singleton.

First call to `get_model()` downloads yolov8n.pt (~6 MB) from the
Ultralytics CDN if it isn't cached locally.  Subsequent calls reuse
the already-loaded model with zero overhead after warmup.
"""

import threading
import torch
from pathlib import Path
from ultralytics import YOLO

# Configuration
MODEL_NAME = "yolov8m.pt"  # Change to yolov8n.pt for faster inference
WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# Singleton pattern with thread safety
_lock = threading.Lock()
_model = None

def get_model() -> YOLO:
    """Return the shared YOLO model, loading it on first call."""
    global _model
    
    if _model is None:
        with _lock:
            if _model is None:  # Double-checked locking
                torch.set_num_threads(1)  # Prevent thread contention
                
                weights_path = WEIGHTS_DIR / MODEL_NAME
                
                # Load from local cache or download
                _model = YOLO(
                    str(weights_path) if weights_path.exists() else MODEL_NAME
                )
                
                # Use GPU if available
                if torch.cuda.is_available():
                    print(f"✅ YOLO is using GPU: {torch.cuda.get_device_name(0)}")
                    _model.to('cuda')
                else:
                    print("⚠️ YOLO is falling back to CPU")
    
    return _model
```

## Inference Function

```python
import time
from typing import List, Tuple
from PIL import Image

class DetectionOut:
    def __init__(self, label: str, confidence: float, bbox: List[float]):
        self.label = label
        self.confidence = confidence
        self.bbox = bbox  # [x, y, width, height]

def run_inference(image: Image.Image) -> Tuple[List[DetectionOut], float]:
    """
    Run YOLO detection on an image.
    
    Args:
        image: PIL Image object (RGB mode)
        
    Returns:
        (detections, latency_ms): List of DetectionOut and time taken
    """
    start_time = time.time()
    
    model = get_model()
    
    # Run YOLO inference
    results = model(image, conf=0.25, verbose=False)
    
    detections = []
    
    # Parse results
    for result in results:
        for box in result.boxes:
            # Get bounding box in [x, y, width, height] format
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            x = x1
            y = y1
            width = x2 - x1
            height = y2 - y1
            
            # Get class label and confidence
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            confidence = float(box.conf[0])
            
            detections.append(DetectionOut(
                label=class_name,
                confidence=confidence,
                bbox=[x, y, width, height]
            ))
    
    latency_ms = (time.time() - start_time) * 1000
    
    return detections, latency_ms
```

## Integration in FastAPI Endpoint

```python
@app.post("/api/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)):
    """Accepts image file, runs YOLO detection, returns results"""
    
    # Read uploaded image
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    # Run inference in background thread to prevent blocking event loop
    detections, latency_ms = await asyncio.to_thread(run_inference, image)
    
    # Convert to Pydantic response model
    detection_outs = [
        DetectionOut(
            label=d.label,
            confidence=d.confidence,
            bbox=d.bbox
        )
        for d in detections
    ]
    
    return DetectResponse(
        latency_ms=latency_ms,
        detections=detection_outs
    )
```

## Model Configuration Options

```python
# Adjust confidence threshold
results = model(image, conf=0.5)  # 50% confidence minimum

# Batch processing multiple images
results = model([image1, image2, image3], conf=0.5)

# Save annotated results
results[0].save('output.jpg')  # Saves with boxes drawn

# Export to other formats
model.export(format='onnx')    # ONNX format
model.export(format='torchscript')  # TorchScript format

# Custom inference parameters
results = model(
    image,
    conf=0.25,      # Confidence threshold
    iou=0.45,       # NMS IoU threshold
    imgsz=640,      # Inference size
    device=0        # GPU device ID (0 for first GPU)
)
```

## Monitoring & Logging

```python
# Check model info
model = get_model()
print(f"Model: {model.model_name}")
print(f"Parameters: {sum(p.numel() for p in model.model.parameters())} M")

# Benchmark inference speed
from ultralytics.utils.benchmarks import Results
results = model.benchmark(imgsz=640, half=True)

# Get device info
print(f"Device: {next(model.model.parameters()).device}")
print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.0f} GB")
```
