# ER Wait Time Prediction

Cloud-native ML system that predicts Emergency Room wait times, serves them via FastAPI, and deploys with Docker + Kubernetes (HPA).

## Features

- **Regression** — predict wait time in minutes (XGBoost, R² ? 0.71)
- **Risk levels** — LOW / MEDIUM / HIGH based on predicted wait
- **Uncertainty** — 25th / 50th / 75th percentile prediction intervals
- **FastAPI** — REST API with health / readiness probes
- **Streamlit UIs** — prediction, scenario comparison, K8s dashboard
- **Docker + Kubernetes** — multi-stage image, NodePort service, HPA (1–5 pods)

## Project structure

```
.
??? main.py                 # FastAPI app
??? streamlit_app.py        # Prediction UI (:8501)
??? k8s_dashboard.py        # Kubernetes monitor (:8502)
??? scenario_comparison.py  # Scenario compare (:8503)
??? Dockerfile
??? requirements.txt
??? *.pkl / model_metadata.json
??? k8s-*.yaml              # Deployment, Service, HPA
??? data/                   # ER Wait Time dataset
??? notebook/               # Training notebook
??? figures/                # EDA & model plots
??? docs/                   # Full documentation
```

## Quick start

### Prerequisites

- Python 3.9+
- Docker Desktop (optional, for containers / Kubernetes)
- `kubectl` (optional)

### Local API + UI

```bash
pip install -r requirements.txt

# Terminal 1 — API
python main.py
# ? http://localhost:8000  |  docs: /docs

# Terminal 2 — Prediction UI
streamlit run streamlit_app.py
# ? http://localhost:8501
```

Or use the helper script:

```bash
./start_app.sh
```

### Docker

```bash
docker build -t er-wait-time-api:v1.0 .
docker run -d --name er-api -p 8000:8000 er-wait-time-api:v1.0
```

### Kubernetes

```bash
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml
kubectl apply -f k8s-hpa.yaml
# API via NodePort: http://localhost:30080
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness |
| GET | `/ready` | Readiness |
| GET | `/models` | Model metadata & metrics |
| POST | `/predict` | Wait time + risk + interval |

**Example request body:**

```json
{
  "arrival_time": "2024-06-15 14:30:00",
  "triage_level": 3,
  "age": 45,
  "department": "General",
  "num_doctors_available": 5,
  "queue_length": 12,
  "is_weekend": 0
}
```

## Model performance

| Task | Metric | Value |
|------|--------|-------|
| Regression | MAE | 23.3 min |
| Regression | RMSE | 35.6 min |
| Regression | R² | 0.714 |
| Classification | Accuracy | 0.883 |
| Classification | ROC-AUC | 0.968 |

Trained: 2025-12-14 · version 1.0

## Access points

| Service | URL |
|---------|-----|
| Prediction UI | http://localhost:8501 |
| K8s Dashboard | http://localhost:8502 |
| Scenario Comparison | http://localhost:8503 |
| FastAPI | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

## Documentation

- [Deployment guide](docs/DEPLOYMENT_GUIDE.md)
- [Project documentation](docs/PROJECT_DOCUMENTATION.md)
- [Kubernetes deployment](docs/KUBERNETES_DEPLOYMENT.md)
- [Training notebook](notebook/cloud-project-v2.ipynb)

## Author

Abdelrahman Nabil
