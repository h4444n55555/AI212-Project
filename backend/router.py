import httpx
import logging
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from ortools.linear_solver import pywraplp
from pydantic import BaseModel
import psutil

app = FastAPI(title="Edge Router / OR-Tools Proxy")

# Allow the Vite dev server to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKER_PORTS = [8001, 8002, 8003, 8004]
worker_loads: Dict[int, int] = {p: 0 for p in WORKER_PORTS}

client = httpx.AsyncClient(timeout=30.0)

def get_optimal_worker_ortools() -> int:
    """
    Uses Google OR-Tools to solve for the lowest-latency worker allocation.
    We frame it as a dynamic assignment formulation where cost coefficient
    is the current simulated queue backlog.
    """
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        # Fallback if solver fails to init
        return min(worker_loads, key=worker_loads.get)
        
    x = {} # assignment boolean variables
    for port in WORKER_PORTS:
        x[port] = solver.IntVar(0, 1, f"assign_{port}")
        
    # Constraint: Exactly one worker must be chosen for this incoming request
    solver.Add(solver.Sum([x[port] for port in WORKER_PORTS]) == 1)
    
    # Objective: Minimize the max bottleneck (cost = load depth)
    objective = solver.Objective()
    for port in WORKER_PORTS:
        # Heavily loaded workers cost more to assign
        objective.SetCoefficient(x[port], float(worker_loads[port]))
    objective.SetMinimization()
    
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        for port in WORKER_PORTS:
            if x[port].solution_value() > 0.5:
                return port
                
    return WORKER_PORTS[0]

@app.post("/api/detect")
async def proxy_detect(file: UploadFile = File(...)):
    # 1. OR-Tools dynamic assignment
    target_port = get_optimal_worker_ortools()
    
    # 2. Add to tracked queue
    worker_loads[target_port] += 1
    logging.info(f"OR-Tools routing request to port {target_port}. Load: {worker_loads}")
    
    try:
        # 3. Read fully into RAM to avoid async IO hanging
        file_bytes = await file.read()
        target_url = f"http://127.0.0.1:{target_port}/api/detect"
        
        # Proxy standard multipart encoding payload
        files = {"file": (file.filename, file_bytes, file.content_type)}
        response = await client.post(target_url, files=files)
        
        # 4. Return the YOLO response natively to React
        response.raise_for_status()
        return response.json()
        
    except httpx.RequestError as e:
        return {"error": f"Failed to reach worker on {target_port}: {str(e)}"}
    finally:
        # 5. Decrement tracking queue regardless of success/fail
        worker_loads[target_port] -= 1


class HealthResponse(BaseModel):
    cpu_percent: float
    mem_used_gb: float
    mem_total_gb: float
    status: str

@app.get("/api/health", response_model=HealthResponse)
def health_metrics():
    """Returns cluster edge metrics for the Analytics dashboard."""
    mem_info = psutil.virtual_memory()
    return HealthResponse(
        cpu_percent=psutil.cpu_percent(interval=0.0),
        mem_used_gb=round(mem_info.used / (1024**3), 2),
        mem_total_gb=round(mem_info.total / (1024**3), 2),
        status="ok (Cluster Router up)"
    )
