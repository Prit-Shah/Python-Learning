"""
Project P5: Pydantic Validation Schemas for ML Inference
"""
from pydantic import BaseModel, Field


class HouseFeatures(BaseModel):
    sqft: float = Field(..., gt=200, lt=20000, description="Square footage", examples=[1850.0])
    bedrooms: int = Field(..., ge=1, le=15, description="Number of bedrooms", examples=[3])
    bathrooms: float = Field(..., ge=1.0, le=10.0, description="Number of bathrooms", examples=[2.0])
    age_years: float = Field(..., ge=0.0, le=150.0, description="Age of the property in years", examples=[10.5])


class BatchPredictionRequest(BaseModel):
    houses: list[HouseFeatures] = Field(..., min_length=1, max_length=100)


class SinglePredictionResponse(BaseModel):
    estimated_price_usd: float
    features: HouseFeatures


class BatchPredictionResponse(BaseModel):
    predictions: list[SinglePredictionResponse]
    total_processed: int
    inference_latency_ms: float
