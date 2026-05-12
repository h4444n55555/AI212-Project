# Kubernetes

## Overview
Kubernetes manifests define how to deploy and manage the application in a Kubernetes cluster for production-grade orchestration and scaling.

## How It's Used in the Project

### 1. **Backend Deployment** (`k8s/backend-deployment.yaml`)
- Runs single replica of backend container
- Exposes port 8000 via ClusterIP service (internal communication only)
- Mounts persistent volume for YOLO model weights
- Uses `imagePullPolicy: IfNotPresent` to avoid unnecessary registry pulls

### 2. **Frontend Deployment** (`k8s/frontend-deployment.yaml`)
- Runs single replica of frontend (Nginx serving React)
- Exposes port 80 via LoadBalancer service (external access)
- Maps LoadBalancer port 5173 to internal port 80

### 3. **Persistent Volume Claim** (`k8s/weights-pvc.yaml`)
- Persistent storage for YOLO model weights (yolov8n.pt, yolov8m.pt)
- Shared between backend init and worker containers
- Survives pod restarts and deletions

## Kubernetes Architecture

```
                    Internet
                        ↓
                 [LoadBalancer Service]
                      :5173
                        ↓
            ┌───────────────────────┐
            │  Frontend Pod         │
            │  (Nginx + React)      │
            └───────────────────────┘
                        ↓
                [Backend Service]
                   :8000 (ClusterIP)
                        ↓
            ┌───────────────────────┐
            │  Backend Pod          │
            │  (FastAPI Router +    │
            │   4 Workers)          │
            └───────────────────────┘
                        ↓
                [PersistentVolume]
                  (YOLO Weights)
```

## Deployment Process

```bash
# Create namespace (optional)
kubectl create namespace detection-system

# Apply manifests
kubectl apply -f k8s/

# Scale replicas (if needed)
kubectl scale deployment backend-deployment --replicas=3

# Monitor rollout
kubectl rollout status deployment/backend-deployment
```

## Key Features

- **Service Discovery** - Services auto-registered in cluster DNS
- **Persistent Storage** - Weights survive pod restarts
- **Load Balancing** - Distributes external traffic
- **Rolling Updates** - Zero-downtime deployments
- **Resource Management** - Can set CPU/memory limits
- **Auto-Restart** - Failed pods automatically redeployed
