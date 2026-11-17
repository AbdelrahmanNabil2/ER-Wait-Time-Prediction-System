#!/bin/bash

set -e

echo "=============================================="
echo "ER Wait Time Prediction System"
echo "Complete System Startup"
echo "=============================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}Docker found${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}kubectl not found. Kubernetes deployment will be skipped.${NC}"
    SKIP_K8S=true
else
    echo -e "${GREEN}kubectl found${NC}"
    SKIP_K8S=false
fi

if ! command -v minikube &> /dev/null; then
    echo -e "${YELLOW}minikube not found. Will use kubectl only.${NC}"
    USE_MINIKUBE=false
else
    echo -e "${GREEN}minikube found${NC}"
    USE_MINIKUBE=true
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found. Please install Python 3.9+${NC}"
    exit 1
fi
echo -e "${GREEN}Python3 found${NC}"

if ! docker ps &> /dev/null; then
    echo -e "${RED}Docker daemon is not running. Please start Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}Docker daemon running${NC}"

echo ""
echo "Installing Python dependencies..."
pip install -q -r requirements.txt 2>/dev/null || {
    echo -e "${YELLOW}Some dependencies may already be installed${NC}"
}

echo ""
echo "=============================================="
echo "Starting Docker Container"
echo "=============================================="

if docker ps -a | grep -q er-api-test; then
    docker rm er-api-test 2>/dev/null || true
fi

if docker images | grep -q "er-wait-time-api.*v1.0"; then
    echo -e "${YELLOW}Docker image already exists (using cached image)${NC}"
    REBUILD_IMAGE=false
else
    echo "Building Docker image..."
    docker build -q -t er-wait-time-api:v1.0 . || {
        echo -e "${RED}Docker build failed${NC}"
        exit 1
    }
    echo -e "${GREEN}Docker image built successfully${NC}"
    REBUILD_IMAGE=true
fi

echo "Starting Docker container..."
docker run -d \
    --name er-api-test \
    -p 8000:8000 \
    er-wait-time-api:v1.0 || {
    echo -e "${RED}Failed to start Docker container${NC}"
    exit 1
}

echo "Waiting for container to be ready..."
sleep 5

if curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}Docker API is healthy on port 8000${NC}"
else
    echo -e "${RED}Docker API health check failed${NC}"
    echo "Checking logs..."
    docker logs er-api-test
    exit 1
fi

echo ""
echo "=============================================="
echo "Deploying to Kubernetes"
echo "=============================================="

if [ "$SKIP_K8S" = false ]; then
    if [ "$USE_MINIKUBE" = true ]; then
        if ! minikube status | grep -q "Running"; then
            echo "Minikube is not running. Starting..."
            minikube start --driver=docker --cpus=4 --memory=2048
            minikube addons enable metrics-server
            sleep 30
        else
            echo -e "${GREEN}Minikube is running${NC}"
        fi
    fi
    
    if [ "$USE_MINIKUBE" = true ]; then
        echo ""
        echo "Loading Docker image into Minikube..."
        minikube image load er-wait-time-api:v1.0
        echo -e "${GREEN}Docker image loaded into Minikube${NC}"
        sleep 5
    fi
    
    if kubectl cluster-info &> /dev/null; then
        echo "Auto-generating Kubernetes YAML files..."
        
        echo "Cleaning up existing resources..."
        kubectl delete deployment er-wait-time-api 2>/dev/null || true
        kubectl delete service er-wait-time-api 2>/dev/null || true
        kubectl delete hpa er-wait-time-api 2>/dev/null || true
        sleep 5
        
        echo "  Generating k8s-deployment.yaml..."
        kubectl create deployment er-wait-time-api \
            --image=er-wait-time-api:v1.0 \
            --replicas=1 \
            --port=8000 \
            --dry-run=client -o yaml > k8s-deployment.yaml.tmp
        
        cat > k8s-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: er-wait-time-api
  labels:
    app: er-wait-time-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: er-wait-time-api
  template:
    metadata:
      labels:
        app: er-wait-time-api
    spec:
      containers:
      - name: er-wait-time-api
        image: er-wait-time-api:v1.0
        imagePullPolicy: Never
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
EOF
        rm -f k8s-deployment.yaml.tmp
        
        echo "  Generating k8s-service.yaml..."
        kubectl create service nodeport er-wait-time-api \
            --tcp=80:8000 \
            --node-port=30080 \
            --dry-run=client -o yaml > k8s-service.yaml
        
        echo -e "${GREEN}Kubernetes YAMLs auto-generated${NC}"
        echo ""
        
        echo "Applying Kubernetes Deployment and Service..."
        kubectl apply -f k8s-deployment.yaml
        kubectl apply -f k8s-service.yaml
        
        echo "Waiting for deployment to be ready..."
        sleep 15
        
        echo "  Generating k8s-hpa.yaml..."
        kubectl autoscale deployment er-wait-time-api \
            --cpu=50% \
            --min=1 \
            --max=5 \
            --dry-run=client -o yaml > k8s-hpa.yaml
        
        echo "Applying HPA configuration..."
        kubectl apply -f k8s-hpa.yaml
        
        echo "Waiting for pods to be ready..."
        sleep 15
        
        if kubectl get pods -l app=er-wait-time-api | grep -q "Running"; then
            echo -e "${GREEN}Kubernetes pods are running${NC}"
            kubectl get pods -l app=er-wait-time-api
            
            echo ""
            echo "Testing Kubernetes API health..."
            sleep 5
            if curl -sf http://localhost:30080/healthz > /dev/null 2>&1; then
                echo -e "${GREEN}Kubernetes API is healthy on port 30080${NC}"
            else
                echo -e "${YELLOW}Kubernetes API not ready yet (check with: kubectl get pods)${NC}"
            fi
        else
            echo -e "${YELLOW}Pods are starting (check with: kubectl get pods)${NC}"
            kubectl describe pod -l app=er-wait-time-api | tail -20
        fi
    else
        echo -e "${YELLOW}Kubernetes cluster not running. Skipping K8s deployment.${NC}"
    fi
else
    echo -e "${YELLOW}Skipping Kubernetes deployment (kubectl not found)${NC}"
fi

echo ""
echo "=============================================="
echo "Starting Streamlit Interfaces"
echo "=============================================="

pkill -f streamlit 2>/dev/null || true
sleep 2

echo "Starting Main Prediction GUI (port 8501)..."
nohup streamlit run streamlit_app.py --server.port 8501 > /dev/null 2>&1 &
STREAMLIT1_PID=$!

echo "Starting Kubernetes Dashboard (port 8502)..."
nohup streamlit run k8s_dashboard.py --server.port 8502 > /dev/null 2>&1 &
STREAMLIT2_PID=$!

echo "Starting Scenario Comparison (port 8503)..."
nohup streamlit run scenario_comparison.py --server.port 8503 > /dev/null 2>&1 &
STREAMLIT3_PID=$!

echo "Waiting for Streamlit apps to initialize..."
sleep 10

STREAMLIT_STATUS=0

if curl -sf http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}Prediction GUI running on port 8501${NC}"
else
    echo -e "${YELLOW}Prediction GUI may still be starting${NC}"
    STREAMLIT_STATUS=1
fi

if curl -sf http://localhost:8502 > /dev/null 2>&1; then
    echo -e "${GREEN}K8s Dashboard running on port 8502${NC}"
else
    echo -e "${YELLOW}K8s Dashboard may still be starting${NC}"
    STREAMLIT_STATUS=1
fi

if curl -sf http://localhost:8503 > /dev/null 2>&1; then
    echo -e "${GREEN}Scenario Comparison running on port 8503${NC}"
else
    echo -e "${YELLOW}Scenario Comparison may still be starting${NC}"
    STREAMLIT_STATUS=1
fi

echo ""
echo "=============================================="
echo "System Startup Complete!"
echo "=============================================="
echo ""
echo "Service Status:"
echo "  Docker API:           http://localhost:8000"
if [ "$USE_MINIKUBE" = true ]; then
    echo "  Kubernetes API:       $(minikube service er-wait-time-api --url 2>/dev/null || echo 'http://localhost:80')"
    echo "  Minikube Dashboard:   $(minikube dashboard --url 2>/dev/null || echo 'minikube dashboard')"
else
    echo "  Kubernetes API:       http://localhost:8080 (port-forward)"
fi
echo "  Prediction GUI:       http://localhost:8501"
echo "  K8s Dashboard:        http://localhost:8502"
echo "  Scenario Comparison:  http://localhost:8503"
echo "  API Documentation:    http://localhost:8000/docs"
echo ""
echo "Quick Commands:"
echo "  Check Docker:     docker ps | grep er-api"
echo "  Check K8s:        kubectl get pods"
echo "  Check HPA:        kubectl get hpa"
echo "  Check Streamlit:  ps aux | grep streamlit"
echo "  View logs:        docker logs -f er-api-test"
if [ "$USE_MINIKUBE" = true ]; then
    echo "  Minikube service: minikube service er-wait-time-api"
    echo "  Minikube IP:      $(minikube ip)"
fi
echo ""
echo "To stop everything:"
echo "  docker stop er-api-test && docker rm er-api-test"
echo "  kubectl delete -f k8s-deployment.yaml k8s-service.yaml k8s-hpa.yaml"
echo "  pkill -f streamlit"
if [ "$USE_MINIKUBE" = true ]; then
    echo "  minikube stop"
fi
echo ""

if [ $STREAMLIT_STATUS -eq 1 ]; then
    echo -e "${YELLOW}Some Streamlit apps may still be starting.${NC}"
    echo "   Wait 10-20 seconds and check the URLs above."
    echo ""
fi

echo "Press Ctrl+C to view this summary again, or close this terminal."
echo "The services will continue running in the background."
echo ""

wait