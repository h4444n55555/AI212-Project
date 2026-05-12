# OR-Tools Implementation - Code Snippets

## Dynamic Worker Assignment with OR-Tools (`backend/router.py`)

```python
import logging
from fastapi import FastAPI, UploadFile, File
from ortools.linear_solver import pywraplp
from typing import Dict
import httpx

app = FastAPI(title="Edge Router / OR-Tools Proxy")

# Track worker queue depths
WORKER_PORTS = [8001, 8002, 8003, 8004]
worker_loads: Dict[int, int] = {p: 0 for p in WORKER_PORTS}

def get_optimal_worker_ortools() -> int:
    """
    Uses Google OR-Tools to solve for the lowest-latency worker allocation.
    
    Formulation:
    - Variables: x_i ∈ {0, 1} for each worker i (binary assignment)
    - Constraint: Σx_i = 1 (exactly 1 worker selected)
    - Objective: Minimize Σ(load_i * x_i) (choose least loaded worker)
    
    Returns:
        port (int): The optimal worker port to route request to
    """
    
    # Create solver instance with SCIP (open-source solver)
    solver = pywraplp.Solver.CreateSolver('SCIP')
    
    if not solver:
        # Fallback: if SCIP unavailable, use simple min
        logging.warning("OR-Tools solver failed to init. Using greedy fallback.")
        return min(worker_loads, key=worker_loads.get)
    
    # Create binary decision variables: one per worker
    x = {}
    for port in WORKER_PORTS:
        x[port] = solver.IntVar(0, 1, f"assign_worker_{port}")
    
    # Constraint: Exactly one worker must be chosen
    solver.Add(solver.Sum([x[port] for port in WORKER_PORTS]) == 1)
    
    # Objective: Minimize total cost = sum of (load * assignment)
    # High-load workers have high cost, so solver avoids them
    objective = solver.Objective()
    for port in WORKER_PORTS:
        cost = float(worker_loads[port])
        objective.SetCoefficient(x[port], cost)
    objective.SetMinimization()
    
    # Solve the optimization problem
    status = solver.Solve()
    
    # Check if solution was found
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        # Extract solution: find which worker was assigned (value > 0.5)
        for port in WORKER_PORTS:
            if x[port].solution_value() > 0.5:
                logging.info(f"OR-Tools selected worker {port} (load: {worker_loads[port]})")
                return port
    
    # Ultimate fallback: return first worker
    logging.error("OR-Tools solver failed. Using port 8001.")
    return WORKER_PORTS[0]

# Main proxy endpoint with OR-Tools routing
@app.post("/api/detect")
async def proxy_detect(file: UploadFile = File(...)):
    """
    Route incoming detection request to optimal worker using OR-Tools.
    
    Steps:
    1. Solve optimization to find best worker
    2. Track request in queue
    3. Proxy request to selected worker
    4. Return worker response
    5. Decrement queue counter
    """
    
    # Step 1: Use OR-Tools to compute optimal worker assignment
    target_port = get_optimal_worker_ortools()
    
    # Step 2: Increment worker load
    worker_loads[target_port] += 1
    logging.info(f"Request routed to {target_port}. Current loads: {worker_loads}")
    
    try:
        # Step 3: Read file and build proxy request
        file_bytes = await file.read()
        target_url = f"http://127.0.0.1:{target_port}/api/detect"
        
        # Reconstruct multipart payload for proxy
        files = {"file": (file.filename, file_bytes, file.content_type)}
        
        # Step 4: Make HTTP request to worker
        client = httpx.AsyncClient(timeout=30.0)
        response = await client.post(target_url, files=files)
        response.raise_for_status()
        
        # Step 5: Return worker's response directly to frontend
        return response.json()
        
    except httpx.RequestError as e:
        logging.error(f"Worker {target_port} error: {e}")
        return {"error": f"Failed to reach worker {target_port}"}
    
    finally:
        # Step 6: Decrement load regardless of success/failure
        worker_loads[target_port] -= 1
        logging.info(f"Request completed. Updated loads: {worker_loads}")
```

## Custom OR-Tools Problem (Alternative)

```python
from ortools.linear_solver import pywraplp

def solve_assignment_problem(worker_loads: Dict[int, int]) -> int:
    """
    Advanced: Solve a more complex cost function.
    
    Instead of simple load, we can add:
    - Historical latency of each worker
    - Current CPU usage
    - Memory pressure
    """
    
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return list(worker_loads.keys())[0]
    
    workers = list(worker_loads.keys())
    num_workers = len(workers)
    
    # Binary variables
    assignments = [
        solver.IntVar(0, 1, f'assign_{w}') for w in workers
    ]
    
    # Constraint: exactly one assignment
    solver.Add(solver.Sum(assignments) == 1)
    
    # Multi-factor objective
    objective = solver.Objective()
    
    for i, worker in enumerate(workers):
        # Weight 1: Current load (most important)
        load_cost = float(worker_loads[worker])
        
        # Weight 2: Could add historical latency
        latency_cost = 10.0  # Example multiplier
        
        # Weight 3: Could add worker availability
        availability_penalty = 0.0  # 0 = available, 5 = struggling
        
        total_cost = (load_cost * 2.0) + (latency_cost * 0.5) + availability_penalty
        objective.SetCoefficient(assignments[i], total_cost)
    
    objective.SetMinimization()
    
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        for i, worker in enumerate(workers):
            if assignments[i].solution_value() > 0.5:
                return worker
    
    return workers[0]
```

## Load Monitoring

```python
@app.get("/api/router/status")
def router_status():
    """Monitor current load across workers"""
    return {
        "workers": worker_loads,
        "total_queued": sum(worker_loads.values()),
        "average_load": sum(worker_loads.values()) / len(WORKER_PORTS),
        "max_load": max(worker_loads.values()),
        "min_load": min(worker_loads.values()),
        "imbalance": max(worker_loads.values()) - min(worker_loads.values())
    }

# Response example:
# {
#   "workers": {"8001": 2, "8002": 1, "8003": 3, "8004": 0},
#   "total_queued": 6,
#   "average_load": 1.5,
#   "max_load": 3,
#   "min_load": 0,
#   "imbalance": 3
# }
```

## Installation & Configuration

```bash
# Install OR-Tools
pip install ortools

# Verify installation
python -c "from ortools.linear_solver import pywraplp; print('OR-Tools ready!')"

# Check available solvers
python -c "from ortools.linear_solver import pywraplp; print(pywraplp.Solver.SupportedSolvers())"
```

## Performance Tuning

```python
# Set solver time limit (milliseconds)
solver.SetTimeLimit(100)  # Solve in max 100ms

# Set log output
solver.EnableOutput()  # Print solver progress

# Check solution quality
print(f"Solver status: {status}")
print(f"Objective value: {solver.Objective().Value()}")
print(f"Wall time: {solver.wall_time()} ms")
```
