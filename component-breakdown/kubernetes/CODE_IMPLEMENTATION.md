# Kubernetes Implementation - Code Snippets

## Backend Deployment (`k8s/backend-deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
  labels:
    app: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend-container
          image: ai212project-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          # Resource limits (optional but recommended)
          resources:
            limits:
              memory: "2Gi"
              cpu: "1000m"
            requests:
              memory: "1Gi"
              cpu: "500m"
          # Volume mount for YOLO weights
          volumeMounts:
            - name: weights-storage
              mountPath: /app/weights
      # Define volumes for the pod
      volumes:
        - name: weights-storage
          persistentVolumeClaim:
            claimName: backend-weights-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: backend
  labels:
    app: backend
spec:
  type: ClusterIP  # Internal service, not exposed externally
  selector:
    app: backend
  ports:
    - protocol: TCP
      port: 8000
      targetPort: 8000
```

## Frontend Deployment (`k8s/frontend-deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-deployment
  labels:
    app: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend-container
          image: ai212project-frontend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 80
          # Resource limits
          resources:
            limits:
              memory: "512Mi"
              cpu: "500m"
            requests:
              memory: "256Mi"
              cpu: "250m"

---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  type: LoadBalancer  # Exposed externally
  selector:
    app: frontend
  ports:
    - protocol: TCP
      port: 5173      # External port
      targetPort: 80  # Internal container port
```

## Persistent Volume Claim (`k8s/weights-pvc.yaml`)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-weights-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard  # or your cluster's default
  resources:
    requests:
      storage: 5Gi  # Enough for multiple YOLO models
```

## Deployment & Management Commands

```bash
# Deploy all manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/backend-deployment
kubectl logs -f deployment/frontend-deployment

# Scale backend to 3 replicas
kubectl scale deployment backend-deployment --replicas=3

# Update image version
kubectl set image deployment/backend-deployment \
  backend-container=ai212project-backend:v1.1

# Monitor rollout progress
kubectl rollout status deployment/backend-deployment

# Describe pod for troubleshooting
kubectl describe pod <pod-name>

# Delete all resources
kubectl delete -f k8s/

# Forward local port to service (for debugging)
kubectl port-forward service/backend 8000:8000
```

## Production Best Practices

```yaml
# Add liveness & readiness probes
livenessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5

# Add environment variables
env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: MODEL_NAME
    value: "yolov8m.pt"
```
