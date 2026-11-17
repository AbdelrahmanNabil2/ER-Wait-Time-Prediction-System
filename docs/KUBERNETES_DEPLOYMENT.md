# Kubernetes Deployment Guide for ER Wait Time Prediction API

This guide shows how to deploy the ML model to Kubernetes following the project requirements:
- No manual YAML writing (generate from kubectl commands)
- Health checks (liveness & readiness probes)
- Horizontal Pod Autoscaler (HPA)
- Production-ready configuration

---

## Prerequisites

```bash
docker --version

kubectl version --client

docker login
```

---

## Step 1: Build and Push Docker Image

```bash
cd "final_version/trained_models"

docker build -t your-dockerhub-username/er-wait-time-api:v1.0 .

docker run -p 8000:8000 your-dockerhub-username/er-wait-time-api:v1.0

curl http://localhost:8000/healthz
curl http://localhost:8000/

docker push your-dockerhub-username/er-wait-time-api:v1.0
```

**Checkpoint**: Your Docker image is now available in Docker Hub!

---

## Step 2: Create Kubernetes Deployment (No Manual YAML!)

### Option A: Using kubectl create (Recommended for this project)

```bash
kubectl create deployment er-wait-time-api \
  --image=your-dockerhub-username/er-wait-time-api:v1.0 \
  --replicas=1 \
  --port=8000

kubectl get deployments
kubectl get pods
```

### Generate the YAML for your GitHub repo

```bash
kubectl get deployment er-wait-time-api -o yaml > deployment.yaml
```

---

## Step 3: Add Health Checks Using kubectl

**IMPORTANT**: As per project requirements, we use `kubectl` commands to add probes, not manual YAML editing.

```bash
kubectl set probe deployment/er-wait-time-api \
  --liveness \
  --get-url=http://:8000/healthz \
  --initial-delay-seconds=10 \
  --period-seconds=30 \
  --timeout-seconds=5 \
  --failure-threshold=3

kubectl set probe deployment/er-wait-time-api \
  --readiness \
  --get-url=http://:8000/ready \
  --initial-delay-seconds=5 \
  --period-seconds=10 \
  --timeout-seconds=3 \
  --failure-threshold=3

kubectl describe deployment er-wait-time-api
```

### Export Updated Deployment YAML

```bash
kubectl get deployment er-wait-time-api -o yaml > kubernetes/deployment.yaml
```

---

## Step 4: Expose the Deployment as a Service

```bash
kubectl expose deployment er-wait-time-api \
  --type=LoadBalancer \
  --port=80 \
  --target-port=8000 \
  --name=er-wait-time-service

minikube service er-wait-time-service --url

kubectl get service er-wait-time-service
```

### Export Service YAML

```bash
kubectl get service er-wait-time-service -o yaml > kubernetes/service.yaml
```

**Alternative**: Use NodePort for local testing

```bash
kubectl expose deployment er-wait-time-api \
  --type=NodePort \
  --port=8000 \
  --name=er-wait-time-service
```

---

## Step 5: Configure Horizontal Pod Autoscaler (HPA)

```bash
kubectl autoscale deployment er-wait-time-api \
  --min=1 \
  --max=5 \
  --cpu-percent=50

kubectl get hpa

kubectl get hpa er-wait-time-api -o yaml > kubernetes/hpa.yaml
```

**HPA Configuration Explanation**:
- **Minimum pods**: 1 (always at least 1 pod running)
- **Maximum pods**: 5 (scale up to 5 pods under high load)
- **CPU threshold**: 50% (scale up when CPU > 50%)

### Enable Metrics Server (Required for HPA)

```bash
minikube addons enable metrics-server

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

kubectl get deployment metrics-server -n kube-system
```

---

## Step 6: Verify Everything Works

```bash
kubectl get all

kubectl get pods
kubectl describe pod <pod-name>

kubectl logs -f deployment/er-wait-time-api

kubectl get service er-wait-time-service

curl http://<EXTERNAL-IP>/healthz

curl -X POST http://<EXTERNAL-IP>/predict \
  -H "Content-Type: application/json" \
  -d '{
    "arrival_time": "2024-03-15 14:30:00",
    "triage_level": 3,
    "age": 45,
    "department": "General",
    "num_doctors_available": 5,
    "queue_length": 12,
    "is_weekend": 0
  }'
```

---

## Step 7: Test Autoscaling

```bash
kubectl run -i --tty load-generator --rm --image=busybox --restart=Never -- /bin/sh

while true; do wget -q -O- http://er-wait-time-service/healthz; done

kubectl get hpa er-wait-time-api --watch

kubectl get pods --watch
```

---

## Export All YAML Files for GitHub

```bash
mkdir -p kubernetes

kubectl get deployment er-wait-time-api -o yaml > kubernetes/deployment.yaml
kubectl get service er-wait-time-service -o yaml > kubernetes/service.yaml  
kubectl get hpa er-wait-time-api -o yaml > kubernetes/hpa.yaml
```

---

## Final Project Structure

```
final_version/trained_models/
├── main.py                    # FastAPI application
├── Dockerfile                 # Container configuration
├── .dockerignore             # Docker ignore file
├── requirements.txt          # Python dependencies
├── *.pkl                     # Trained models
├── model_metadata.json       # Model metadata
└── kubernetes/               # Auto-generated YAML files
    ├── deployment.yaml       # Deployment with health probes
    ├── service.yaml          # Service configuration
    └── hpa.yaml             # Autoscaler configuration
```

---

## Update and Redeploy

```bash
docker build -t your-dockerhub-username/er-wait-time-api:v1.1 .
docker push your-dockerhub-username/er-wait-time-api:v1.1

kubectl set image deployment/er-wait-time-api \
  er-wait-time-api=your-dockerhub-username/er-wait-time-api:v1.1

kubectl rollout status deployment/er-wait-time-api

kubectl rollout undo deployment/er-wait-time-api
```

---

## Cleanup

```bash
kubectl delete hpa er-wait-time-api
kubectl delete service er-wait-time-service
kubectl delete deployment er-wait-time-api

kubectl get all
```

---

## Summary of kubectl Commands Used

### Creation Commands (No Manual YAML!)
```bash
kubectl create deployment er-wait-time-api --image=... --replicas=1 --port=8000

kubectl set probe deployment/er-wait-time-api --liveness --get-url=http://:8000/healthz ...

kubectl set probe deployment/er-wait-time-api --readiness --get-url=http://:8000/ready ...

kubectl expose deployment er-wait-time-api --type=LoadBalancer --port=80 --target-port=8000

kubectl autoscale deployment er-wait-time-api --min=1 --max=5 --cpu-percent=50

kubectl get deployment er-wait-time-api -o yaml > kubernetes/deployment.yaml
kubectl get service er-wait-time-service -o yaml > kubernetes/service.yaml
kubectl get hpa er-wait-time-api -o yaml > kubernetes/hpa.yaml
```

---

## Project Requirements Checklist

- **Docker Image**: Built and pushed to Docker Hub
- **Dockerfile**: Created with multi-stage build
- **API Endpoints**: `/predict` and `/healthz` implemented
- **Kubernetes Deployment**: Created using kubectl commands
- **Kubernetes Service**: Created using kubectl expose
- **Liveness Probe**: Added using kubectl set probe
- **Readiness Probe**: Added using kubectl set probe
- **HPA**: Configured for CPU-based autoscaling (min=1, max=5, 50%)
- **YAML Files**: Auto-generated from kubectl commands
- **GitHub Ready**: All files ready for version control

---

## What You Learned

1. Building production-ready Docker images
2. Deploying ML models to Kubernetes
3. Implementing health checks for reliability
4. Configuring autoscaling for performance
5. Using kubectl commands instead of manual YAML
6. Real-world cloud-native ML deployment patterns

---

**Congratulations! Your ML model is now running in Kubernetes with health checks and autoscaling!**
