"""
Project P5: Model Training & Serialization Pipeline
"""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_squared_error


def train_and_serialize_model(output_path: Path | str = "model.joblib") -> dict:
    """Trains a Housing Price Regressor pipeline and persists it via joblib."""
    np.random.seed(42)
    n_samples = 1000

    sqft = np.random.uniform(500, 4500, n_samples)
    bedrooms = np.random.randint(1, 6, n_samples)
    bathrooms = np.random.randint(1, 4, n_samples)
    age_years = np.random.uniform(0, 50, n_samples)

    # True price formula with non-linear noise
    price = (
        180.0 * sqft
        + 25000.0 * bedrooms
        + 18000.0 * bathrooms
        - 1200.0 * age_years
        + np.random.normal(0, 15000, n_samples)
    )

    X = pd.DataFrame({
        "sqft": sqft,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "age_years": age_years,
    })
    y = price

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(n_estimators=50, random_state=42)),
    ])

    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    r2 = float(r2_score(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))

    dest = Path(output_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, dest)

    return {
        "model_file": str(dest),
        "r2_score": round(r2, 4),
        "rmse": round(rmse, 2),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }


if __name__ == "__main__":
    metrics = train_and_serialize_model()
    print("[SUCCESS] Model trained and persisted.")
    print(metrics)
