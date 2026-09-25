"""
Automated Pytest Suite for Project P5: ML Prediction API
"""
import pytest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from pathlib import Path
from fastapi.testclient import TestClient
from ..trainer import train_and_serialize_model
from ..app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_model_training_and_serialization(tmp_path):
    model_file = tmp_path / "test_model.joblib"
    metrics = train_and_serialize_model(model_file)
    assert model_file.exists()
    assert metrics["r2_score"] > 0.85, f"R2 score too low: {metrics['r2_score']}"
    assert metrics["train_samples"] == 800
    assert metrics["test_samples"] == 200


def test_single_prediction_endpoint(client):
    payload = {
        "sqft": 2200.0,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "age_years": 5.0,
    }
    resp = client.post("/api/v1/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_price_usd" in data
    assert data["estimated_price_usd"] > 100_000.0


def test_batch_prediction_endpoint(client):
    batch_payload = {
        "houses": [
            {"sqft": 1200.0, "bedrooms": 2, "bathrooms": 1.0, "age_years": 20.0},
            {"sqft": 3500.0, "bedrooms": 5, "bathrooms": 3.5, "age_years": 2.0},
        ]
    }
    resp = client.post("/api/v1/predict/batch", json=batch_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_processed"] == 2
    assert len(data["predictions"]) == 2
    # Larger house should have higher estimated price
    price_small = data["predictions"][0]["estimated_price_usd"]
    price_large = data["predictions"][1]["estimated_price_usd"]
    assert price_large > price_small


def test_invalid_input_validation(client):
    # sqft below minimum (200)
    bad_payload = {"sqft": 50.0, "bedrooms": 1, "bathrooms": 1.0, "age_years": 0.0}
    resp = client.post("/api/v1/predict", json=bad_payload)
    assert resp.status_code == 422
