from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
import os
from typing import Dict, Any
from sklearn.base import BaseEstimator, RegressorMixin
from xgboost import XGBRegressor
import sys

class QuantileXGBoostRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, quantile=0.5, **kwargs):
        self.quantile = quantile
        self.kwargs = kwargs
        self.model = None
        
    def fit(self, X, y):
        params = {
            'objective': 'reg:quantileerror',
            'quantile_alpha': self.quantile,
            **self.kwargs
        }
        self.model = XGBRegressor(**params)
        self.model.fit(X, y)
        return self
    
    def predict(self, X):
        return self.model.predict(X)

sys.modules['__main__'].QuantileXGBoostRegressor = QuantileXGBoostRegressor

app = FastAPI(
    title="ER Wait Time Predictor API",
    description="Machine Learning API for predicting Emergency Room wait times with uncertainty quantification",
    version="1.0.0"
)

models = {}
scaler = None
metadata = None

FEATURE_COLUMNS = [
    "triage_level", "age", "num_doctors_available", "queue_length",
    "is_weekend", "arrival_hour", "arrival_day_of_week", "arrival_month",
    "arrival_day", "is_rush_hour", "doctor_patient_ratio",
    "dept_General", "tod_afternoon", "tod_evening", "tod_morning", "tod_night"
]


def load_models():
    global models, scaler, metadata
    
    success_count = 0
    total_models = 7
    
    try:
        models['xgb_regressor'] = joblib.load("xgboost_regressor.pkl")
        print("Loaded XGBoost regressor")
        success_count += 1
    except Exception as e:
        print(f"Failed to load XGBoost regressor: {e}")
    
    try:
        models['xgb_classifier'] = joblib.load("xgboost_classifier.pkl")
        print("Loaded XGBoost classifier")
        success_count += 1
    except Exception as e:
        print(f"Failed to load XGBoost classifier: {e}")
    
    try:
        models['quantile_25'] = joblib.load("xgboost_quantile_25.pkl")
        print("Loaded 25th percentile model")
        success_count += 1
    except Exception as e:
        print(f"Could not load 25th percentile model: {e}")
    
    try:
        models['quantile_50'] = joblib.load("xgboost_quantile_50.pkl")
        print("Loaded 50th percentile model")
        success_count += 1
    except Exception as e:
        print(f"Could not load 50th percentile model: {e}")
    
    try:
        models['quantile_75'] = joblib.load("xgboost_quantile_75.pkl")
        print("Loaded 75th percentile model")
        success_count += 1
    except Exception as e:
        print(f"Could not load 75th percentile model: {e}")
    
    try:
        scaler = joblib.load("feature_scaler.pkl")
        print("Loaded feature scaler")
        success_count += 1
    except Exception as e:
        print(f"Failed to load scaler: {e}")
    
    try:
        import json
        with open("model_metadata.json", "r") as f:
            metadata = json.load(f)
        print("Loaded model metadata")
        success_count += 1
    except Exception as e:
        print(f"Failed to load metadata: {e}")
    
    print(f"\nLoaded {success_count}/{total_models} components")
    
    return models.get('xgb_regressor') is not None and models.get('xgb_classifier') is not None


@app.on_event("startup")
async def startup_event():
    success = load_models()
    if not success:
        print("Warning: Some models failed to load")


class PatientInput(BaseModel):
    arrival_time: str = Field(..., example="2024-03-15 14:30:00")
    triage_level: int = Field(..., ge=1, le=5, example=3)
    age: int = Field(..., ge=0, le=120, example=45)
    department: str = Field(..., example="General")
    num_doctors_available: int = Field(..., ge=0, le=20, example=5)
    queue_length: int = Field(..., ge=0, le=300, example=12)
    is_weekend: int = Field(..., ge=0, le=1, example=0)
    
    class Config:
        schema_extra = {
            "example": {
                "arrival_time": "2024-03-15 14:30:00",
                "triage_level": 3,
                "age": 45,
                "department": "General",
                "num_doctors_available": 5,
                "queue_length": 12,
                "is_weekend": 0
            }
        }


def preprocess_input(data: Dict[str, Any]) -> pd.DataFrame:
    arrival_dt = pd.to_datetime(data['arrival_time'])
    
    arrival_hour = arrival_dt.hour
    arrival_day_of_week = arrival_dt.dayofweek
    arrival_month = arrival_dt.month
    arrival_day = arrival_dt.day
    
    if 6 <= arrival_hour < 12:
        time_of_day = 'morning'
    elif 12 <= arrival_hour < 18:
        time_of_day = 'afternoon'
    elif 18 <= arrival_hour < 22:
        time_of_day = 'evening'
    else:
        time_of_day = 'night'
    
    is_rush_hour = 1 if (9 <= arrival_hour < 11) or (18 <= arrival_hour < 20) else 0
    
    doctor_patient_ratio = data['num_doctors_available'] / (data['queue_length'] + 1)
    
    features = {
        'triage_level': data['triage_level'],
        'age': data['age'],
        'num_doctors_available': data['num_doctors_available'],
        'queue_length': data['queue_length'],
        'is_weekend': data['is_weekend'],
        'arrival_hour': arrival_hour,
        'arrival_day_of_week': arrival_day_of_week,
        'arrival_month': arrival_month,
        'arrival_day': arrival_day,
        'is_rush_hour': is_rush_hour,
        'doctor_patient_ratio': doctor_patient_ratio,
        'dept_General': 1 if data['department'] == 'General' else 0,
        'tod_afternoon': 1 if time_of_day == 'afternoon' else 0,
        'tod_evening': 1 if time_of_day == 'evening' else 0,
        'tod_morning': 1 if time_of_day == 'morning' else 0,
        'tod_night': 1 if time_of_day == 'night' else 0,
    }
    
    df = pd.DataFrame([features])
    df = df[FEATURE_COLUMNS]
    
    if scaler is not None:
        df_scaled = pd.DataFrame(
            scaler.transform(df),
            columns=df.columns
        )
        return df_scaled
    
    return df


@app.get("/")
def root():
    return {
        "message": "ER Wait Time Prediction API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "/": "API information",
            "/healthz": "Health check endpoint",
            "/health": "Detailed health status",
            "/predict": "Predict wait time with uncertainty",
            "/models": "Get model metadata and performance metrics"
        }
    }


@app.get("/healthz")
def health_check():
    return {"status": "healthy"}


@app.get("/health")
def detailed_health():
    model_status = {
        "xgb_regressor": models.get('xgb_regressor') is not None,
        "xgb_classifier": models.get('xgb_classifier') is not None,
        "quantile_models": all([
            models.get('quantile_25') is not None,
            models.get('quantile_50') is not None,
            models.get('quantile_75') is not None
        ]),
        "scaler": scaler is not None,
        "metadata": metadata is not None
    }
    
    all_healthy = all(model_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "models_loaded": model_status,
        "ready": all_healthy
    }


@app.get("/models")
def get_models_info():
    if metadata is None:
        return {"error": "Model metadata not available"}
    
    return {
        "model_version": metadata.get("model_version", "unknown"),
        "training_date": metadata.get("training_date", "unknown"),
        "feature_count": len(metadata.get("feature_columns", [])),
        "metrics": metadata.get("metrics", {}),
        "available_models": list(models.keys())
    }


@app.post("/predict")
def predict(patient: PatientInput):
    try:
        data = patient.dict()
        
        X = preprocess_input(data)
        
        wait_time = float(models['xgb_regressor'].predict(X)[0])
        
        LONG_WAIT_THRESHOLD = 15
        is_long_wait = wait_time > LONG_WAIT_THRESHOLD
        
        difference = wait_time - LONG_WAIT_THRESHOLD
        long_wait_prob = 1 / (1 + np.exp(-difference / 5))
        
        has_quantile = all([models.get('quantile_25'), models.get('quantile_50'), models.get('quantile_75')])
        
        if has_quantile:
            lower_bound = float(models['quantile_25'].predict(X)[0])
            median = float(models['quantile_50'].predict(X)[0])
            upper_bound = float(models['quantile_75'].predict(X)[0])
        else:
            lower_bound = max(0, wait_time * 0.7)
            median = wait_time
            upper_bound = wait_time * 1.3
        
        if wait_time < 10:
            risk_level = "LOW"
        elif wait_time < 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        response = {
            "status": "success",
            "model_used": "xgboost",
            "predicted_wait_time": round(wait_time, 1),
            "is_long_wait": is_long_wait,
            "long_wait_probability": round(long_wait_prob, 3),
            "risk_level": risk_level,
            "prediction_interval": {
                "lower_bound_25th": round(lower_bound, 1),
                "median_50th": round(median, 1),
                "upper_bound_75th": round(upper_bound, 1),
                "interpretation": f"50% of similar cases wait between {round(lower_bound, 0)}-{round(upper_bound, 0)} minutes",
                "using_quantile_models": has_quantile
            },
            "patient_info": {
                "triage_level": data['triage_level'],
                "department": data['department'],
                "queue_position": data['queue_length']
            }
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/ready")
def readiness_check():
    if scaler is None:
        raise HTTPException(status_code=503, detail="Scaler not loaded")
    
    if models.get('xgb_regressor') is None:
        raise HTTPException(status_code=503, detail="Regressor model not loaded")
    
    if models.get('xgb_classifier') is None:
        raise HTTPException(status_code=503, detail="Classifier model not loaded")
    
    return {"status": "ready", "message": "Core models loaded and ready to serve predictions"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
