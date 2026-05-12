"""Optional Ray actor wrapper for distributed YOLOv8x inference."""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

try:
    import ray
except ImportError:  # pragma: no cover - Ray is optional in this environment
    ray = None

# ── Shared constants (mirrors model.py) ──────────────────────────────────────

MODEL_NAME = "yolov8x.pt"
INFER_SIZE = 640
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45


class YOLOWorkerActor:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.weights_dir = Path(__file__).parent / "weights"
        self.weights_dir.mkdir(exist_ok=True)
        self._use_half = False

    def _get_model(self) -> YOLO:
        if self.model is None:
            torch.set_num_threads(1)
            weights_path = self.weights_dir / self.model_name
            self.model = YOLO(str(weights_path) if weights_path.exists() else self.model_name)
            if torch.cuda.is_available():
                self.model.to("cuda")
                self._use_half = torch.cuda.get_device_capability(0)[0] >= 7
            # Warmup with a dummy frame
            dummy = np.zeros((INFER_SIZE, INFER_SIZE, 3), dtype=np.uint8)
            try:
                self.model(dummy, imgsz=INFER_SIZE, verbose=False, half=self._use_half)
            except Exception:
                pass
        return self.model

    @torch.inference_mode()
    def run_inference(self, image_bytes: bytes, conf: float = CONF_THRESHOLD) -> Dict[str, Any]:
        start_time = time.perf_counter()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        model = self._get_model()

        results = model(
            image,
            imgsz=INFER_SIZE,
            conf=conf,
            iou=IOU_THRESHOLD,
            half=self._use_half,
            verbose=False,
            agnostic_nms=True,
        )
        detections: List[Dict[str, Any]] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                detections.append(
                    {
                        "label": result.names[class_id],
                        "confidence": round(float(box.conf[0]), 4),
                        "bbox": [
                            round(x1, 1),
                            round(y1, 1),
                            round(x2 - x1, 1),
                            round(y2 - y1, 1),
                        ],
                    }
                )

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return {
            "detections": detections,
            "latency_ms": (time.perf_counter() - start_time) * 1000,
            "model_name": self.model_name,
        }

    def get_status(self) -> Dict[str, Any]:
        model = self._get_model()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        return {
            "model_loaded": self.model is not None,
            "model_name": self.model_name,
            "device": device,
        }


if ray is not None:
    YOLOWorkerActor = ray.remote(num_gpus=0.25 if torch.cuda.is_available() else 0)(YOLOWorkerActor)


def initialize_ray_cluster(num_workers: int = 4, num_gpus: float = 1.0):
    if ray is None:
        raise RuntimeError("Ray is not installed in this environment")

    if not ray.is_initialized():
        ray.init(
            num_cpus=max(num_workers, 1),
            num_gpus=num_gpus if torch.cuda.is_available() else 0,
            include_dashboard=False,
            log_to_driver=False,
            ignore_reinit_error=True,
        )

    return [YOLOWorkerActor.remote(model_name=MODEL_NAME) for _ in range(num_workers)]