# Kubernetes Configuration Files

This directory contains Kubernetes YAML files that were **auto-generated** using `kubectl` commands, following the project requirement of not writing YAML files manually.

## Files

- **deployment.yaml** - Deployment configuration with health probes
- **service.yaml** - LoadBalancer service configuration
- **hpa.yaml** - Horizontal Pod Autoscaler configuration

## How These Files Were Generated

These files were created using the following kubectl commands:

### 1. Deployment with Health Probes
```bash
kubectl create deployment er-wait-time-api --image=YOUR_IMAGE --replicas=1 --port=8000
kubectl set probe deployment/er-wait-time-api --liveness --get-url=http://:8000/healthz
kubectl set probe deployment/er-wait-time-api --readiness --get-url=http://:8000/ready
kubectl get deployment er-wait-time-api -o yaml > deployment.yaml
```

### 2. Service
```bash
kubectl expose deployment er-wait-time-api --type=LoadBalancer --port=80 --target-port=8000
kubectl get service er-wait-time-service -o yaml > service.yaml
```

### 3. HPA
```bash
kubectl autoscale deployment er-wait-time-api --min=1 --max=5 --cpu-percent=50
kubectl get hpa er-wait-time-api -o yaml > hpa.yaml
```

## Usage

To apply these configurations to your Kubernetes cluster:

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml
```

Or apply all at once:

```bash
kubectl apply -f kubernetes/
```

## Important Notes

**Replace placeholders** in deployment.yaml:
- `your-dockerhub-username/er-wait-time-api:v1.0` with your actual Docker image

**Prerequisites**:
- Kubernetes cluster running
- Metrics server installed (for HPA)
- Docker image pushed to registry

For complete deployment instructions, see [KUBERNETES_DEPLOYMENT.md](../KUBERNETES_DEPLOYMENT.md)
