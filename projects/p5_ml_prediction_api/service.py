"""
Project P5: In-Memory Inference Service
"""
import joblib
import time
from pathlib import Path
import pandas as pd
from .schemas import HouseFeatures, BatchPredictionResponse, SinglePredictionResponse


class ModelInferenceService:
    def __init__(self, model_path: Path | str = "model.joblib"):
        self.model_path = Path(model_path).resolve()
        self.model = None

    def load_model(self):
        if not self.model_path.exists():
            from .trainer import train_and_serialize_model
            train_and_serialize_model(self.model_path)
        self.model = joblib.load(self.model_path)

    def predict_batch(self, houses: list[HouseFeatures]) -> BatchPredictionResponse:
        if self.model is None:
            self.load_model()

        t0 = time.perf_counter()

        # Convert to Pandas DataFrame for pipeline consumption
        df = pd.DataFrame([h.model_dump() for h in houses])
        predictions = self.model.predict(df)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        items = [
            SinglePredictionResponse(
                estimated_price_usd=round(float(price), 2),
                features=houses[i],
            )
            for i, price in enumerate(predictions)
        ]

        return BatchPredictionResponse(
            predictions=items,
            total_processed=len(items),
            inference_latency_ms=round(elapsed_ms, 2),
        )


inference_service = ModelInferenceService()
