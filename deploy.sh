#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DOCKER_IMAGE="${DOCKER_IMAGE:-yourusername/er-wait-time-api}"
DOCKER_TAG="${DOCKER_TAG:-v1.0}"
DEPLOYMENT_NAME="er-wait-time-api"
SERVICE_NAME="er-wait-time-service"

print_header() {
    echo -e "${BLUE}${1}${NC}"
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

show_help() {
    cat << EOF
ER Wait Time API - Deployment Helper

Usage: ./deploy.sh [COMMAND]

Commands:
  local           - Run the API locally (without Docker)
  docker-build    - Build Docker image
  docker-run      - Run Docker container locally
  docker-push     - Push Docker image to registry
  docker-all      - Build, run, and push Docker image
  
  k8s-deploy      - Deploy to Kubernetes (creates all resources)
  k8s-update      - Update Kubernetes deployment with new image
  k8s-status      - Show Kubernetes deployment status
  k8s-logs        - Show pod logs
  k8s-test        - Test the API on Kubernetes
  k8s-scale       - Manually scale deployment
  k8s-delete      - Delete all Kubernetes resources
  
  test-local      - Test API on localhost
  test-k8s        - Test API on Kubernetes
  
  export-yamls    - Export Kubernetes YAMLs for GitHub
  
  help            - Show this help message

Environment Variables:
  DOCKER_IMAGE    - Docker image name (default: yourusername/er-wait-time-api)
  DOCKER_TAG      - Docker image tag (default: v1.0)

Examples:
  ./deploy.sh docker-all
  ./deploy.sh k8s-deploy
  DOCKER_IMAGE=myrepo/api ./deploy.sh docker-build

EOF
}

run_local() {
    print_header "Running API Locally"
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found. Are you in the correct directory?"
        exit 1
    fi
    echo "Installing dependencies..."
    pip install -r requirements.txt
    print_success "Starting API server..."
    python main.py
}

docker_build() {
    print_header "Building Docker Image"
    echo "Image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
    print_success "Docker image built successfully"
    docker images | grep $(basename ${DOCKER_IMAGE})
}

docker_run() {
    print_header "Running Docker Container"
    echo "Stopping any existing container..."
    docker stop er-api 2>/dev/null || true
    docker rm er-api 2>/dev/null || true
    echo "Starting container..."
    docker run -d -p 8000:8000 --name er-api ${DOCKER_IMAGE}:${DOCKER_TAG}
    print_success "Container started"
    echo "API available at: http://localhost:8000"
    echo "Logs: docker logs -f er-api"
    sleep 2
    echo ""
    echo "Testing health endpoint..."
    curl -s http://localhost:8000/healthz || print_warning "API not ready yet, wait a few seconds"
}

docker_push() {
    print_header "Pushing Docker Image to Registry"
    echo "Image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
    print_success "Docker image pushed successfully"
}

docker_all() {
    docker_build
    docker_run
    echo ""
    read -p "Test the API, then press Enter to push to registry..."
    docker_push
}

k8s_deploy() {
    print_header "Deploying to Kubernetes"
    echo "Creating deployment..."
    kubectl create deployment ${DEPLOYMENT_NAME} \
        --image=${DOCKER_IMAGE}:${DOCKER_TAG} \
        --replicas=1 \
        --port=8000
    echo "Adding liveness probe..."
    kubectl set probe deployment/${DEPLOYMENT_NAME} \
        --liveness \
        --get-url=http://:8000/healthz \
        --initial-delay-seconds=10 \
        --period-seconds=30 \
        --timeout-seconds=5 \
        --failure-threshold=3
    echo "Adding readiness probe..."
    kubectl set probe deployment/${DEPLOYMENT_NAME} \
        --readiness \
        --get-url=http://:8000/ready \
        --initial-delay-seconds=5 \
        --period-seconds=10 \
        --timeout-seconds=3 \
        --failure-threshold=3
    echo "Creating service..."
    kubectl expose deployment ${DEPLOYMENT_NAME} \
        --type=LoadBalancer \
        --port=80 \
        --target-port=8000 \
        --name=${SERVICE_NAME}
    echo "Configuring autoscaling..."
    kubectl autoscale deployment ${DEPLOYMENT_NAME} \
        --min=1 \
        --max=5 \
        --cpu-percent=50
    print_success "Deployment complete!"
    echo ""
    k8s_status
}

k8s_update() {
    print_header "Updating Kubernetes Deployment"
    echo "Updating image to ${DOCKER_IMAGE}:${DOCKER_TAG}"
    kubectl set image deployment/${DEPLOYMENT_NAME} \
        ${DEPLOYMENT_NAME}=${DOCKER_IMAGE}:${DOCKER_TAG}
    echo "Monitoring rollout..."
    kubectl rollout status deployment/${DEPLOYMENT_NAME}
    print_success "Deployment updated successfully"
}

k8s_status() {
    print_header "Kubernetes Status"
    echo "All resources:"
    kubectl get all | grep er-wait-time || echo "No resources found"
    echo ""
    echo "HPA status:"
    kubectl get hpa ${DEPLOYMENT_NAME} 2>/dev/null || echo "HPA not configured"
    echo ""
    echo "Service URL:"
    kubectl get service ${SERVICE_NAME} 2>/dev/null || echo "Service not found"
}

k8s_logs() {
    print_header "Pod Logs"
    kubectl logs -f deployment/${DEPLOYMENT_NAME}
}

k8s_test() {
    print_header "Testing Kubernetes Deployment"
    SERVICE_URL=$(kubectl get service ${SERVICE_NAME} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -z "$SERVICE_URL" ]; then
        print_warning "LoadBalancer IP not assigned yet. For Minikube, use:"
        echo "  minikube service ${SERVICE_NAME} --url"
        return
    fi
    echo "Service URL: http://${SERVICE_URL}"
    echo ""
    echo "Testing health endpoint..."
    curl -s http://${SERVICE_URL}/healthz | jq .
    echo ""
    echo "To test prediction:"
    echo "  python test_api.py http://${SERVICE_URL}"
}

k8s_scale() {
    print_header "Manually Scale Deployment"
    read -p "Enter number of replicas: " replicas
    kubectl scale deployment ${DEPLOYMENT_NAME} --replicas=${replicas}
    print_success "Scaled to ${replicas} replicas"
    kubectl get pods
}

k8s_delete() {
    print_header "Deleting Kubernetes Resources"
    print_warning "This will delete all resources!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        return
    fi
    kubectl delete hpa ${DEPLOYMENT_NAME} 2>/dev/null || true
    kubectl delete service ${SERVICE_NAME} 2>/dev/null || true
    kubectl delete deployment ${DEPLOYMENT_NAME} 2>/dev/null || true
    print_success "All resources deleted"
}

test_local() {
    print_header "Testing Local API"
    if [ ! -f "test_api.py" ]; then
        print_error "test_api.py not found"
        exit 1
    fi
    python test_api.py http://localhost:8000
}

test_k8s() {
    print_header "Testing Kubernetes API"
    SERVICE_URL=$(kubectl get service ${SERVICE_NAME} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -z "$SERVICE_URL" ]; then
        print_error "Service URL not available. For Minikube:"
        echo "  SERVICE_URL=\$(minikube service ${SERVICE_NAME} --url)"
        echo "  python test_api.py \$SERVICE_URL"
        return
    fi
    python test_api.py http://${SERVICE_URL}
}

export_yamls() {
    print_header "Exporting Kubernetes YAMLs"
    mkdir -p kubernetes
    echo "Exporting deployment..."
    kubectl get deployment ${DEPLOYMENT_NAME} -o yaml > kubernetes/deployment.yaml
    echo "Exporting service..."
    kubectl get service ${SERVICE_NAME} -o yaml > kubernetes/service.yaml
    echo "Exporting HPA..."
    kubectl get hpa ${DEPLOYMENT_NAME} -o yaml > kubernetes/hpa.yaml
    print_success "YAMLs exported to kubernetes/ directory"
    ls -lh kubernetes/
}

main() {
    case "${1:-help}" in
        local)
            run_local
            ;;
        docker-build)
            docker_build
            ;;
        docker-run)
            docker_run
            ;;
        docker-push)
            docker_push
            ;;
        docker-all)
            docker_all
            ;;
        k8s-deploy)
            k8s_deploy
            ;;
        k8s-update)
            k8s_update
            ;;
        k8s-status)
            k8s_status
            ;;
        k8s-logs)
            k8s_logs
            ;;
        k8s-test)
            k8s_test
            ;;
        k8s-scale)
            k8s_scale
            ;;
        k8s-delete)
            k8s_delete
            ;;
        test-local)
            test_local
            ;;
        test-k8s)
            test_k8s
            ;;
        export-yamls)
            export_yamls
            ;;
        help|*)
            show_help
            ;;
    esac
}

main "$@"
