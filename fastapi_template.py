from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import joblib
import pandas as pd
import numpy as np

app = FastAPI(title="ER Wait Time Predictor", version="1.0")

xgb_regressor = joblib.load("trained_models/xgboost_regressor.pkl")
xgb_classifier = joblib.load("trained_models/xgboost_classifier.pkl")
quantile_25 = joblib.load("trained_models/xgboost_quantile_25.pkl")
quantile_50 = joblib.load("trained_models/xgboost_quantile_50.pkl")
quantile_75 = joblib.load("trained_models/xgboost_quantile_75.pkl")

class PatientData(BaseModel):
    arrival_time: str
    triage_level: int
    age: int
    department: str
    num_doctors_available: int
    queue_length: int
    is_weekend: int = 0
    
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

@app.get("/")
def root():
    return {"message": "ER Wait Time Prediction API", "version": "1.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/predict")
def predict(patient: PatientData):
    try:
        data = patient.dict()
        prediction = predict_wait_time(data, return_interval=True)
        return {"status": "success", "prediction": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
