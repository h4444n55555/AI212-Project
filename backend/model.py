"""
model.py — Lazy-loaded YOLOv8 singleton.

First call to `get_model()` downloads yolov8n.pt (~6 MB) from the
Ultralytics CDN if it isn't cached locally.  Subsequent calls reuse
the already-loaded model, so there is zero overhead after warmup.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import List

import torch
from PIL import Image
from ultralytics import YOLO

# ── Config ───────────────────────────────────────────────────────────────────

# Change to "yolov8s.pt" / "yolov8m.pt" for higher accuracy at the cost
# of speed.  The nano model is the best default for a local dev setup.
MODEL_NAME = "yolov8m.pt"

# Where to cache the weights (inside the backend folder)
WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# ── Singleton ─────────────────────────────────────────────────────────────────

_lock:  threading.Lock = threading.Lock()
_model: YOLO | None = None


def get_model() -> YOLO:
    """Return the shared YOLO model, loading it on first call."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:  # double-checked locking
                torch.set_num_threads(1)  # Fix contention: 1 internal thread per process
                weights_path = WEIGHTS_DIR / MODEL_NAME
                _model = YOLO(str(weights_path) if weights_path.exists() else MODEL_NAME)
                # Ensure we aggressively use CUDA if it is available
                if torch.cuda.is_available():
                    print(f"✅ YOLO is using GPU: {torch.cuda.get_device_name(0)}")
                    _model.to('cuda')
                else:
                    print("⚠️ YOLO is falling back to CPU. (CUDA not detected)")

                # If downloaded to cwd, move into our weights/ dir
                cwd_weights = Path(MODEL_NAME)
                if cwd_weights.exists() and not weights_path.exists():
                    cwd_weights.rename(weights_path)
    return _model


# ── Inference ─────────────────────────────────────────────────────────────────

Detection = dict  # { label: str, confidence: float, bbox: [x, y, w, h] }


def run_inference(image: Image.Image) -> tuple[List[Detection], float]:
    """
    Run YOLOv8 on a PIL Image.

    Returns
    -------
    detections : list of dicts  { label, confidence, bbox: [x, y, w, h] }
    latency_ms : float          wall-clock inference time in milliseconds

    The bbox format is [x, y, width, height] in **pixel coordinates**
    relative to the original image size, matching what the frontend
    expects for canvas rendering.
    """
    model = get_model()

    t0 = time.perf_counter()
    
    # Safely determine if FP16 is heavily supported (Compute Capability >= 7.0 for Tensor Cores)
    use_half = False
    if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 7:
        use_half = True
        
    results = model(image, verbose=False, half=use_half)
    latency_ms = (time.perf_counter() - t0) * 1000

    detections: List[Detection] = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue
        names = result.names  # {class_id: label_string}
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls  = int(box.cls[0])
            detections.append({
                "label":      names[cls],
                "confidence": round(conf, 4),
                "bbox":       [
                    round(x1, 1),
                    round(y1, 1),
                    round(x2 - x1, 1),  # width
                    round(y2 - y1, 1),  # height
                ],
            })

    # Sort by confidence descending for nicer token ordering
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return detections, latency_ms
