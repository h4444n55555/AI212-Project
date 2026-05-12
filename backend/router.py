from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import httpx
import psutil
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ortools.linear_solver import pywraplp
from pydantic import BaseModel, Field

try:
    import ray
    from ray_worker import YOLOWorkerActor, initialize_ray_cluster

    RAY_AVAILABLE = True
except ImportError:
    ray = None
    YOLOWorkerActor = None
    initialize_ray_cluster = None
    RAY_AVAILABLE = False


WORKER_PORTS = [8001, 8002, 8003, 8004]
worker_loads: Dict[int, int] = {port: 0 for port in WORKER_PORTS}
ray_loads: Dict[int, int] = {}
ray_workers: List[Any] = []
client = httpx.AsyncClient(timeout=30.0)

app = FastAPI(title="Edge Router / OR-Tools + Ray Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DetectResponse(BaseModel):
    latency_ms: float | None = None
    detections: List[dict] = Field(default_factory=list)
    error: str | None = None
    worker_id: int | None = None
    routing_mode: str | None = None


class HealthResponse(BaseModel):
    cpu_percent: float
    mem_used_gb: float
    mem_total_gb: float
    status: str
    routing_mode: str


def _solve_min_load(loads: Dict[int, int]) -> int:
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        return min(loads, key=loads.get)

    assignment = {key: solver.IntVar(0, 1, f"assign_{key}") for key in loads}
    solver.Add(solver.Sum(assignment[key] for key in loads) == 1)

    objective = solver.Objective()
    for key, load in loads.items():
        objective.SetCoefficient(assignment[key], float(load))
    objective.SetMinimization()

    status = solver.Solve()
    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        for key in loads:
            if assignment[key].solution_value() > 0.5:
                return key

    return min(loads, key=loads.get)


def _routing_mode() -> str:
    if ray_workers:
        return "Ray Cluster + OR-Tools"
    return "HTTP Workers + OR-Tools"


@app.on_event("startup")
async def startup_event() -> None:
    global ray_workers, ray_loads

    if not RAY_AVAILABLE:
        return

    try:
        ray_workers = initialize_ray_cluster(num_workers=len(WORKER_PORTS), num_gpus=1.0)
        ray_loads = {index: 0 for index in range(len(ray_workers))}
    except Exception as exc:
        ray_workers = []
        ray_loads = {}
        print(f"Ray initialization skipped: {exc}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await client.aclose()
    if ray is not None and ray.is_initialized():
        ray.shutdown()


@app.post("/api/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)):
    file_bytes = await file.read()

    if ray_workers:
        worker_id = _solve_min_load(ray_loads)
        ray_loads[worker_id] += 1
        try:
            result = await asyncio.to_thread(
                ray.get,
                ray_workers[worker_id].run_inference.remote(file_bytes),
            )
            return DetectResponse(
                latency_ms=result.get("latency_ms"),
                detections=result.get("detections", []),
                worker_id=worker_id,
                routing_mode="Ray Cluster + OR-Tools",
            )
        except Exception as exc:
            return DetectResponse(
                error=f"Ray inference failed: {exc}",
                worker_id=worker_id,
                routing_mode="Ray Cluster + OR-Tools",
            )
        finally:
            ray_loads[worker_id] -= 1

    worker_port = _solve_min_load(worker_loads)
    worker_loads[worker_port] += 1
    try:
        response = await client.post(
            f"http://127.0.0.1:{worker_port}/api/detect",
            files={"file": (file.filename, file_bytes, file.content_type)},
        )
        response.raise_for_status()
        payload = response.json()
        return DetectResponse(
            latency_ms=payload.get("latency_ms"),
            detections=payload.get("detections", []),
            routing_mode="HTTP Workers + OR-Tools",
            worker_id=worker_port,
        )
    except Exception as exc:
        return DetectResponse(
            error=f"Failed to reach worker {worker_port}: {exc}",
            worker_id=worker_port,
            routing_mode="HTTP Workers + OR-Tools",
        )
    finally:
        worker_loads[worker_port] -= 1


@app.get("/api/health", response_model=HealthResponse)
def health_metrics():
    mem_info = psutil.virtual_memory()
    return HealthResponse(
        cpu_percent=psutil.cpu_percent(interval=0.0),
        mem_used_gb=round(mem_info.used / (1024**3), 2),
        mem_total_gb=round(mem_info.total / (1024**3), 2),
        status="ok",
        routing_mode=_routing_mode(),
    )


@app.get("/api/router/status")
def router_status():
    return {
        "routing_mode": _routing_mode(),
        "ray_available": RAY_AVAILABLE,
        "ray_workers": len(ray_workers),
        "worker_ports": WORKER_PORTS,
        "worker_loads": worker_loads,
        "ray_loads": ray_loads,
        "total_queued": sum(worker_loads.values()) + sum(ray_loads.values()),
    }