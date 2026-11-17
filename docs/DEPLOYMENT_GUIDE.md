# ER Wait Time Prediction System - Complete Deployment Guide

A production-ready machine learning system for predicting emergency room wait times with Docker, Kubernetes, and interactive Streamlit interfaces.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Access Points](#access-points)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Usage Examples](#usage-examples)

---

## Overview

This system provides real-time ER wait time predictions using XGBoost machine learning models with:
- **FastAPI** backend for REST API
- **Docker** containerization
- **Kubernetes** orchestration with auto-scaling
- **Streamlit** web interfaces for predictions, monitoring, and analysis

### What It Predicts
- **Wait Time:** Expected wait in minutes
- **Risk Level:** LOW/MEDIUM/HIGH classification (based on wait time thresholds)
- **Long Wait Probability:** Likelihood of wait > 15 minutes
- **Prediction Intervals:** 25th, 50th, 75th percentile bounds for uncertainty quantification

---

## Features

### Machine Learning
- XGBoost regression for wait time prediction
- Quantile regression for uncertainty quantification
- 7 trained models loaded (regressor, classifier, 3 quantile models, scaler, metadata)
- Real-time feature engineering

### Deployment
- Multi-stage Docker builds for optimized images
- Kubernetes deployment with auto-scaling (2-5 replicas)
- Horizontal Pod Autoscaling (HPA)
- Health checks and readiness probes
- LoadBalancer service

### User Interfaces
- **Main Prediction GUI** - Interactive wait time predictions
- **Kubernetes Dashboard** - Real-time cluster monitoring and management
- **Scenario Comparison** - Side-by-side predictions analysis

---

## Architecture

```
User Interfaces (Streamlit)
  Prediction GUI :8501
  K8s Dashboard :8502
  Scenario Comparison :8503
         |
         v
API Layer (FastAPI)
  Docker Container localhost:8000
  Kubernetes Cluster localhost:80
         |
         v
ML Models & Data Processing
  XGBoost Regressor, Feature Scaler
  Quantile Models, Model Metadata
```

---

## Prerequisites

### Required Software
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
  - Includes Kubernetes
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **kubectl** (usually included with Docker Desktop)

### System Requirements
- **RAM:** 4GB minimum, 8GB recommended
- **Disk Space:** 5GB free space
- **OS:** macOS, Linux, or Windows with WSL2

---

## Quick Start

### Step 1: Navigate to Project Directory
```bash
cd "/Users/abdelrahmannabil/Downloads/cloud project ML/version 2 docker/final_version/trained_models"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Start Docker Container
```bash
docker build -t er-wait-time-api:v1.0 .

docker run -d --name er-api-test -p 8000:8000 er-wait-time-api:v1.0

docker ps
curl http://localhost:8000/healthz
```

### Step 4: Deploy to Kubernetes
```bash
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml
kubectl apply -f k8s-hpa.yaml

kubectl get pods
kubectl get services
```

### Step 5: Start Streamlit Interfaces

**Option A: Run in Separate Terminals**
```bash
streamlit run streamlit_app.py --server.port 8501

streamlit run k8s_dashboard.py --server.port 8502

streamlit run scenario_comparison.py --server.port 8503
```

**Option B: Run in Background**
```bash
streamlit run streamlit_app.py --server.port 8501 &
streamlit run k8s_dashboard.py --server.port 8502 &
streamlit run scenario_comparison.py --server.port 8503 &
```

### Step 6: Access the Applications
Open your browser and navigate to:
- Main GUI: http://localhost:8501
- K8s Dashboard: http://localhost:8502
- Scenario Comparison: http://localhost:8503

---

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Prediction GUI** | http://localhost:8501 | Main interface for ER wait time predictions |
| **K8s Dashboard** | http://localhost:8502 | Kubernetes cluster monitoring & management |
| **Scenario Comparison** | http://localhost:8503 | Multi-scenario analysis tool |
| **Docker API** | http://localhost:8000 | FastAPI backend (Docker container) |
| **Kubernetes API** | http://localhost:80 | FastAPI backend (K8s service) |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive API documentation |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative API documentation |

---

## API Documentation

### Health Check Endpoints

#### GET /healthz
Kubernetes liveness probe - Basic health check
```bash
curl http://localhost:8000/healthz
```

#### GET /health
Detailed health status with model availability
```bash
curl http://localhost:8000/health
```

#### GET /ready
Kubernetes readiness probe
```bash
curl http://localhost:8000/ready
```

### Prediction Endpoint

#### POST /predict
Get wait time prediction for a patient

**Request:**
```bash
curl -X POST http://localhost:8000/predict \
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

### Input Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `arrival_time` | string | ISO datetime | Patient arrival timestamp |
| `triage_level` | integer | 1-5 | Urgency level (1=most urgent, 5=least urgent) |
| `age` | integer | 0-120 | Patient age in years |
| `department` | string | - | ER department (General, Cardiac, Pediatric, Trauma) |
| `num_doctors_available` | integer | 1-20 | Number of doctors currently on duty |
| `queue_length` | integer | 0-300 | Current number of patients in queue |
| `is_weekend` | integer | 0 or 1 | Weekend indicator (0=weekday, 1=weekend) |

### Output Fields

| Field | Type | Description |
|-------|------|-------------|
| `predicted_wait_time` | float | Expected wait time in minutes |
| `is_long_wait` | boolean | True if wait > 15 minutes |
| `long_wait_probability` | float | Probability (0-1) of experiencing a long wait |
| `risk_level` | string | LOW/MEDIUM/HIGH classification |
| `prediction_interval` | object | Uncertainty bounds (25th, 50th, 75th percentiles) |

### Risk Level Thresholds

- **LOW:** Wait time < 10 minutes
- **MEDIUM:** Wait time 10-20 minutes
- **HIGH:** Wait time > 20 minutes

**Long Wait Definition:** Any wait time > 15 minutes

---

## Troubleshooting

### Common Issues

#### 1. Docker Container Won't Start

**Check logs:**
```bash
docker logs er-api-test
```

**Rebuild and restart:**
```bash
docker stop er-api-test && docker rm er-api-test
docker build -t er-wait-time-api:v1.0 .
docker run -d --name er-api-test -p 8000:8000 er-wait-time-api:v1.0
```

#### 2. Port Already in Use

**Find and kill process:**
```bash
lsof -i :8000
kill -9 <PID>
```

#### 3. Kubernetes Pods Not Starting

**Check pod status:**
```bash
kubectl get pods
kubectl describe pod <pod-name>
```

**Restart deployment:**
```bash
kubectl rollout restart deployment/er-wait-time-api
```

#### 4. NumPy Compatibility Error in Streamlit

**Install compatible version:**
```bash
pip install "numpy==1.26.4"
```

#### 5. Streamlit Can't Connect to API

**Verify API is running:**
```bash
curl http://localhost:8000/healthz
```

#### 6. Models Not Loading

**Verify model files exist:**
```bash
ls -lh *.pkl
```

### Complete System Reset

```bash
docker stop er-api-test && docker rm er-api-test
kubectl delete -f k8s-deployment.yaml
kubectl delete -f k8s-service.yaml
pkill -f streamlit

sleep 5
```

---

## Project Structure

```
final_version/trained_models/
├── main.py                      # FastAPI application
├── streamlit_app.py             # Main prediction GUI
├── k8s_dashboard.py             # Kubernetes monitoring dashboard
├── scenario_comparison.py       # Multi-scenario analysis tool
│
├── Dockerfile                   # Docker image configuration
├── requirements.txt             # Python dependencies
│
├── k8s-deployment.yaml          # Kubernetes deployment config
├── k8s-service.yaml             # Kubernetes service (LoadBalancer)
├── k8s-hpa.yaml                 # Horizontal Pod Autoscaler
│
├── xgboost_regressor.pkl        # Main regression model (898KB)
├── xgboost_classifier.pkl       # Classification model (507KB)
├── xgboost_quantile_25.pkl      # 25th percentile quantile model (391KB)
├── xgboost_quantile_50.pkl      # 50th percentile quantile model (378KB)
├── xgboost_quantile_75.pkl      # 75th percentile quantile model (371KB)
├── feature_scaler.pkl           # Feature scaling transformer (1.5KB)
├── model_metadata.json          # Model information and metrics
│
├── start_app.sh                 # Startup script (Mac/Linux)
├── start_app.bat                # Startup script (Windows)
│
└── README.md                    # This file
```

---

## Quick Reference

### Start Everything
```bash
docker run -d --name er-api-test -p 8000:8000 er-wait-time-api:v1.0

kubectl apply -f k8s-deployment.yaml -f k8s-service.yaml -f k8s-hpa.yaml

streamlit run streamlit_app.py --server.port 8501 &
streamlit run k8s_dashboard.py --server.port 8502 &
streamlit run scenario_comparison.py --server.port 8503 &
```

### Stop Everything
```bash
docker stop er-api-test && docker rm er-api-test
kubectl delete -f k8s-deployment.yaml -f k8s-service.yaml
pkill -f streamlit
```

### Quick Health Check
```bash
curl http://localhost:8000/healthz && \
curl http://localhost:80/healthz && \
echo "All APIs healthy"
```

---

**Version:** 1.0.0  
**Last Updated:** December 18, 2025  
**Author:** Cloud ML Team  
**License:** MIT
