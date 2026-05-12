"""
model.py — Lazy-loaded YOLOv8x singleton with inference optimizations.

First call to `get_model()` downloads yolov8x.pt (~131 MB) from the
Ultralytics CDN if it isn't cached locally.  Subsequent calls reuse
the already-loaded model, so there is zero overhead after warmup.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import List

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

# ── Config ───────────────────────────────────────────────────────────────────

# YOLOv8x is the most accurate model in the v8 family.
# Fall back to "yolov8l.pt" or "yolov8m.pt" if memory is tight.
MODEL_NAME = "yolov8x.pt"

# Inference resolution — higher = more accurate but slower.
# 640 is the standard; bump to 1280 for small-object tasks.
INFER_SIZE = 640

# Confidence & NMS thresholds
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45  # IoU threshold for Non-Max Suppression

# Where to cache the weights (inside the backend folder)
WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# ── Singleton ─────────────────────────────────────────────────────────────────

_lock:  threading.Lock = threading.Lock()
_model: YOLO | None = None
_use_half: bool = False  # cached FP16 decision


def get_model() -> YOLO:
    """Return the shared YOLO model, loading it on first call."""
    global _model, _use_half
    if _model is None:
        with _lock:
            if _model is None:  # double-checked locking
                torch.set_num_threads(1)  # Fix contention: 1 internal thread per process
                weights_path = WEIGHTS_DIR / MODEL_NAME
                _model = YOLO(str(weights_path) if weights_path.exists() else MODEL_NAME)

                # Ensure we aggressively use CUDA if it is available
                if torch.cuda.is_available():
                    print(f"✅ YOLO is using GPU: {torch.cuda.get_device_name(0)}")
                    _model.to("cuda")
                    # FP16 is safe on Compute Capability >= 7.0 (Tensor Cores)
                    _use_half = torch.cuda.get_device_capability(0)[0] >= 7
                else:
                    print("⚠️ YOLO is falling back to CPU. (CUDA not detected)")
                    _use_half = False

                # If downloaded to cwd, move into our weights/ dir
                cwd_weights = Path(MODEL_NAME)
                if cwd_weights.exists() and not weights_path.exists():
                    cwd_weights.rename(weights_path)

                # Warmup: run a dummy inference to JIT-compile CUDA kernels & allocate
                # buffers so the first real request doesn't pay the cold-start penalty.
                _warmup(_model)

    return _model


def _warmup(model: YOLO) -> None:
    """Run one dummy forward pass to prime CUDA graphs and memory pools."""
    dummy = np.zeros((INFER_SIZE, INFER_SIZE, 3), dtype=np.uint8)
    try:
        model(dummy, imgsz=INFER_SIZE, verbose=False, half=_use_half)
        print(f"🔥 Model warmup complete (size={INFER_SIZE}, half={_use_half})")
    except Exception as exc:
        print(f"⚠️ Warmup failed (non-fatal): {exc}")


# ── Inference ─────────────────────────────────────────────────────────────────

Detection = dict  # { label: str, confidence: float, bbox: [x, y, w, h] }


@torch.inference_mode()
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
    results = model(
        image,
        imgsz=INFER_SIZE,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        half=_use_half,
        verbose=False,
        agnostic_nms=True,  # class-agnostic NMS removes more overlapping boxes
    )
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
