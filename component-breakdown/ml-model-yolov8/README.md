# ML Model Implementation - YOLOv8

## Overview
YOLOv8 (You Only Look Once v8) by Ultralytics is the core deep learning model that performs real-time object detection on images.

## How It's Used in the Project

### 1. **Model Loading** (`backend/model.py`)
- Lazy-loads YOLO model on first inference request
- Downloads pre-trained weights (yolov8n.pt ~6MB nano, yolov8m.pt ~49MB medium)
- Caches weights in `backend/weights/` directory for reuse
- Thread-safe singleton pattern to prevent duplicate loading

### 2. **GPU Acceleration**
- Automatically detects and uses CUDA GPU if available
- Falls back to CPU inference if GPU not present
- Significantly faster inference on NVIDIA/AMD/Intel GPUs

### 3. **Inference Pipeline** (`backend/model.py`)
- Accepts PIL Image as input
- Runs YOLOv8 detection model
- Returns:
  - Detected objects with class labels
  - Confidence scores (0-1 probability)
  - Bounding box coordinates [x, y, w, h]
  - Inference latency in milliseconds

## Model Variants Available

| Model | Size | Speed (CPU) | Speed (GPU) | Accuracy | Use Case |
|-------|------|-----------|-----------|----------|----------|
| nano (n) | 6 MB | ~45ms | ~7ms | Lower | Mobile/Real-time |
| small (s) | 22 MB | ~90ms | ~12ms | Medium | Balanced |
| medium (m) | 49 MB | ~180ms | ~18ms | High | Production |
| large (l) | 94 MB | ~350ms | ~28ms | Very High | Accuracy-critical |

Current project uses **yolov8m.pt** (medium) for good balance of speed and accuracy.

## Detection Classes

YOLOv8 is trained on COCO dataset with 80 object classes:
- Person, bicycle, car, motorcycle, bus, train, truck
- Airplane, boat, traffic light, parking meter, bench
- Cat, dog, horse, sheep, cow, elephant, bear
- And 72 more categories...

## Performance Metrics

- **Inference Latency**: ~18-50ms per image (GPU/CPU)
- **Input Resolution**: Configurable (default 640×640)
- **Batch Processing**: Supports multiple images per batch
- **Model Format**: PyTorch (.pt) files, exportable to ONNX/TensorRT
