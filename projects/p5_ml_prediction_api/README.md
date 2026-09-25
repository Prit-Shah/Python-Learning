# 🧗 Project P5: Production ML Prediction API
> **Roadmap Target**: Synthesizes NumPy, Pandas, Scikit-Learn Pipelines, and FastAPI Real-Time Inference (Phase 9).

---

## 🏛️ Architecture & Component Design

```text
p5_ml_prediction_api/
├── trainer.py      # Scikit-Learn pipeline training, metrics & joblib serialization
├── schemas.py      # Pydantic v2 schemas for feature validation & response types
├── service.py      # ModelInferenceService managing in-memory cached model weights
├── app.py          # FastAPI application with lifespan model preloading
└── tests/          # Pytest verification suite
```

---

## ⚡ Technical Highlights

1. **Scikit-Learn Preprocessing Pipeline**:
   The `StandardScaler` and `RandomForestRegressor` are bundled together into a single `Pipeline`. This prevents train-test data leakage and ensures incoming raw inputs are transformed with identical distribution weights.

2. **Lifespan Model Weight Preloading**:
   Rather than reloading 50MB model binaries on each HTTP request (which causes 300ms delays), the model is loaded once into memory during `app.lifespan` startup, delivering sub-5ms latency per prediction.

3. **Vectorized Batch Inference**:
   The `/api/v1/predict/batch` endpoint converts lists of Pydantic models directly into contiguous Pandas/NumPy arrays, running multi-item predictions in compiled C rather than Python loops.

---

## 🚀 Running the Service

```bash
# Train model
python -m projects.p5_ml_prediction_api.trainer

# Run API
uvicorn projects.p5_ml_prediction_api.app:app --reload --port 8000
```
