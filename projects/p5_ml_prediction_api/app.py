"""
Project P5: FastAPI ML Inference Microservice
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from .schemas import HouseFeatures, BatchPredictionRequest, BatchPredictionResponse, SinglePredictionResponse
from .service import inference_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload model weights into memory during service boot
    inference_service.load_model()
    yield


app = FastAPI(
    title="P5: Production ML Prediction API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz", tags=["System"])
async def health_check():
    return {
        "status": "ready",
        "model_loaded": inference_service.model is not None,
    }


@app.post("/api/v1/predict", response_model=SinglePredictionResponse, tags=["Inference"])
async def predict_single(features: HouseFeatures):
    """Predicts estimated market price for a single property."""
    batch_res = inference_service.predict_batch([features])
    return batch_res.predictions[0]


@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse, tags=["Inference"])
async def predict_batch(payload: BatchPredictionRequest):
    """High-throughput vectorized batch prediction endpoint."""
    return inference_service.predict_batch(payload.houses)
