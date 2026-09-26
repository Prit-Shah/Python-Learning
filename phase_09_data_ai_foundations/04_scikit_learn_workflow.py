r"""
04_scikit_learn_workflow.py

============================================================
1. CONCEPT
============================================================

Scikit-Learn (sklearn) is the premier classical Machine Learning library in Python.
It provides a mathematically rigorous, unified object-oriented interface for predictive
modeling, classification, regression, clustering, and feature engineering:

1. The Unified Estimator API Contract:
   - Estimators: Learn representations or parameters from data via `.fit(X, y)`.
     Learned parameters are stored as attributes with a trailing underscore (`coef_`, `intercept_`, `classes_`).
   - Transformers: Filter, encode, or normalize feature matrices via `.transform(X)`.
     Combines both steps on training data via `.fit_transform(X, y)`.
   - Predictors: Generate target predictions via `.predict(X)` or posterior probabilities via `.predict_proba(X)`.

2. The Production `Pipeline` Architecture:
   - Encapsulates feature transformations (imputation, scaling, one-hot encoding) and the
     final estimator into a single, atomic composable object:
     `Pipeline(steps=[('scaler', StandardScaler()), ('classifier', LogisticRegression())])`.
   - Eliminates Data Leakage: Guarantees that feature statistics (means, standard deviations)
     are computed STRICTLY on the training fold during cross-validation.

3. Classification Evaluation Metrics:
   - Accuracy: $\frac{TP + TN}{TP + TN + FP + FN}$. Misleading on imbalanced datasets.
   - Precision: $\frac{TP}{TP + FP}$. Fraction of predicted positives that were actually positive.
     Critical when False Positives are expensive (e.g. spam classification).
   - Recall (Sensitivity): $\frac{TP}{TP + FN}$. Fraction of actual positives identified.
     Critical when False Negatives are fatal (e.g. cancer detection, fraud alerts).
   - $F_1$ Score: Harmonic mean balancing precision and recall:
     $F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$.
   - Confusion Matrix: $2 \times 2$ grid containing $[[TN, FP], [FN, TP]]$.

4. Model Serialization & Production Serving:
   - Models are serialized to disk using `joblib` or `pickle`.
   - In production, incoming inference JSON is passed directly through the loaded pipeline's
     `.predict()` method without manual normalization re-implementation.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Scikit-Learn)              | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Unified Model Interface      | `.fit(X, y)`, `.predict(X)`        | Custom classes / `brain.js` / TFJS |
| Model Pipeline               | `Pipeline([('scale', ...), ...])`  | Functional composition / Lodash flow|
| Feature Normalization        | `StandardScaler()`                 | Manual array mapping math          |
| Train/Test Partitioning      | `train_test_split(..., stratify=y)`| Manual shuffle and array splitting |
| Model Persistence            | `joblib.dump(model, 'model.joblib')`| JSON export / TFJS weight files   |
| Evaluation Matrix            | `classification_report(y, y_pred)` | Custom reduce loops calculating F1 |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. JavaScript has fragmented ML libraries without a unified estimator standard. Swapping an
   algorithm in JS often requires rewriting data preparation code.
2. In Scikit-Learn, swapping a model from `LogisticRegression` to `RandomForestClassifier` or
   `GradientBoostingClassifier` requires altering only one line of code; the surrounding pipeline,
   feature transforms, cross-validation, and scoring remain 100% identical.


============================================================
3. UNDER THE HOOD (Cython Kernels & Pipeline Mechanics)
============================================================

1. Cython Execution & Native Optimization:
   - Scikit-Learn's core algorithms (coordinate descent, tree splitting, distance metrics)
     are compiled in Cython and linked against optimized C/Fortran linear algebra libraries (BLAS/LAPACK).
   - Python code acts purely as a high-level configuration orchestrator; heavy mathematical loops
     execute in native machine code with zero Python interpreter overhead.

2. Pipeline Sequential Data Flow:
   - Calling `pipeline.fit(X_train, y_train)`:
     * Stage 1 (`StandardScaler`): Calls `.fit_transform(X_train)`, storing $\mu$ and $\sigma$ as `mean_` and `scale_`.
     * Stage 2 (`LogisticRegression`): Receives standardized array and calls `.fit(X_scaled, y_train)`.
   - Calling `pipeline.predict(X_test)`:
     * Stage 1 (`StandardScaler`): Calls ONLY `.transform(X_test)` using the stored training $\mu$ and $\sigma$.
     * Stage 2 (`LogisticRegression`): Calls `.predict(X_test_scaled)`.
   - Test data statistics are NEVER calculated, preventing data leakage mathematically.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Data Leakage Catastrophe:
   - Calling `scaler.fit_transform(X)` on the ENTIRE dataset BEFORE `train_test_split()`.
   - The test set mean and standard deviation contaminate the scaler parameters, yielding
     falsely optimistic evaluation metrics that plummet when deployed to real production traffic.
   - FIX: ALWAYS split data first, or wrap preprocessing and estimator inside a `Pipeline`.

2. Misleading Accuracy on Imbalanced Classes:
   - In fraud detection where 99.8% of transactions are legitimate, a dummy model predicting
     "Non-Fraud" for every single transaction achieves 99.8% accuracy while detecting 0 fraud cases!
   - FIX: Evaluate with Precision, Recall, F1 Score, and ROC-AUC / PR-AUC curves.

3. Mismatched Feature Columns During Inference:
   - Passing features in a different column order or with missing columns at inference time.
   - FIX: Modern Scikit-Learn (1.0+) tracks `feature_names_in_` and raises immediate validation errors
     if incoming inference DataFrames do not match training schemas.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Walk through an end-to-end Scikit-Learn workflow from raw data to a deployed production model."
A1: "I establish an end-to-end ML lifecycle in five structured phases:
     First, Data Splitting: I immediately split raw data using `train_test_split` with `stratify=y`
     to preserve class distributions, isolating the test set before any transformations occur.
     Second, Pipeline Construction: I build an atomic Scikit-Learn `Pipeline`. I use `ColumnTransformer`
     to apply `StandardScaler` to continuous numerical features and `OneHotEncoder` to categoricals,
     terminating in our chosen estimator (e.g. `LogisticRegression` or `RandomForestClassifier`).
     Third, Hyperparameter Tuning: I optimize hyperparameters using `GridSearchCV` or `RandomizedSearchCV`
     with 5-fold cross-validation evaluated on $F_1$ score rather than raw accuracy.
     Fourth, Evaluation: I evaluate the winning pipeline on the untouched test set, generating a full
     confusion matrix and precision-recall curve.
     Fifth, Serialization: I serialize the entire pipeline using `joblib.dump()`. This packages the
     trained transformers and model into a single artifact, guaranteeing identical preprocessing at inference."

Q2: "Explain the tradeoff between Precision and Recall. In what business scenarios do you optimize each?"
A2: "Precision measures the accuracy of positive predictions—out of all instances flagged positive, how
     many were truly positive? Recall measures completeness—out of all actual positives in reality, how
     many did the model successfully find?
     Precision and Recall exist in fundamental tension: lowering the classification decision threshold
     increases recall at the cost of precision, and vice-versa.
     We optimize for Precision when the cost of a False Positive is high—for example, in automated spam
     filtering or high-confidence trade execution where false alarms damage trust or capital.
     We optimize for Recall when the cost of a False Negative is catastrophic—such as cancer screening,
     fraud detection, or defect detection in manufacturing, where missing a single true positive carries
     severe consequences."

Q3: "What is the difference between `.fit()`, `.transform()`, and `.fit_transform()`?"
A3: "`.fit()` computes the internal parameters from a dataset—such as computing the mean and variance in
     `StandardScaler` or optimizing weights in a regression model—without modifying the data.
     `.transform()` applies those previously learned parameters to transform a dataset into a new feature
     space without modifying the learned parameters.
     `.fit_transform()` is an optimized convenience method for training data that computes parameters and
     returns the transformed data in a single pass.
     We must NEVER call `.fit()` or `.fit_transform()` on test or inference data, as doing so recalculates
     parameters and causes data leakage."
"""

import sys
import tempfile
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. MACHINE LEARNING PIPELINE BUILDER
# ==============================================================================

def generate_synthetic_dataset(
    n_samples: int = 1000,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.Series]:
    """Generates synthetic binary classification dataset representing churn/fraud."""
    X_raw, y_raw = make_classification(
        n_samples=n_samples,
        n_features=4,
        n_informative=3,
        n_redundant=1,
        weights=[0.75, 0.25],  # Imbalanced: 75% Class 0, 25% Class 1
        random_state=random_state
    )
    feature_names = ["usage_hours", "support_tickets", "latency_ms", "account_age_months"]
    df_features = pd.DataFrame(X_raw, columns=feature_names)
    series_target = pd.Series(y_raw, name="churned")
    return df_features, series_target


def create_production_pipeline(random_state: int = 42) -> Pipeline:
    """
    Constructs a leak-free production pipeline encapsulating
    StandardScaler and LogisticRegression.
    """
    pipeline = Pipeline(steps=[
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(random_state=random_state, max_iter=500))
    ])
    return pipeline


# ==============================================================================
# 2. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 04_scikit_learn_workflow.py...")

    # ------------------------------------------------------------
    # Test 1: Dataset Generation & Stratified Partitioning
    # ------------------------------------------------------------
    print("  -> Testing dataset generation and stratified train/test partitioning...")
    X, y = generate_synthetic_dataset(n_samples=1000, random_state=42)
    assert X.shape == (1000, 4)
    assert len(y) == 1000
    assert y.value_counts()[1] / len(y) == 0.25, "Target distribution mismatch"

    # Stratified split: 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    assert X_train.shape == (800, 4)
    assert X_test.shape == (200, 4)
    # Stratification check: 25% positive rate in both splits
    assert np.isclose(y_train.mean(), 0.25, atol=0.01)
    assert np.isclose(y_test.mean(), 0.25, atol=0.01)

    # ------------------------------------------------------------
    # Test 2: Pipeline Training & In-Place Parameter Learning
    # ------------------------------------------------------------
    print("  -> Testing pipeline fit, parameter learning, and no-leak transform...")
    pipeline = create_production_pipeline(random_state=42)

    # Fit pipeline on training set
    pipeline.fit(X_train, y_train)

    # Verify parameters were learned with trailing underscore
    scaler_step: StandardScaler = pipeline.named_steps["scaler"]
    clf_step: LogisticRegression = pipeline.named_steps["classifier"]

    assert hasattr(scaler_step, "mean_")
    assert hasattr(scaler_step, "scale_")
    assert len(scaler_step.mean_) == 4

    assert hasattr(clf_step, "coef_")
    assert hasattr(clf_step, "intercept_")
    assert clf_step.coef_.shape == (1, 4)

    # ------------------------------------------------------------
    # Test 3: Inference & Prediction Evaluation
    # ------------------------------------------------------------
    print("  -> Testing predictions, probabilities, and classification metrics...")
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    assert y_pred.shape == (200,)
    assert y_proba.shape == (200, 2)
    # Probabilities sum to 1.0 per row
    assert np.allclose(y_proba.sum(axis=1), 1.0)

    # Compute classification metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    assert 0.0 <= acc <= 1.0
    assert 0.0 <= prec <= 1.0
    assert 0.0 <= rec <= 1.0
    assert 0.0 <= f1 <= 1.0

    # Ensure model beats random chance (> 75% accuracy)
    assert acc > 0.75, f"Model accuracy too low: {acc}"

    # ------------------------------------------------------------
    # Test 4: Confusion Matrix Mathematical Verification
    # ------------------------------------------------------------
    print("  -> Testing confusion matrix alignment (TN, FP, FN, TP)...")
    cm = confusion_matrix(y_test, y_pred)
    assert cm.shape == (2, 2)
    tn, fp, fn, tp = cm.ravel()
    assert (tn + fp + fn + tp) == 200

    # Mathematical identity verification
    expected_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    expected_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    assert np.isclose(prec, expected_prec)
    assert np.isclose(rec, expected_rec)

    # ------------------------------------------------------------
    # Test 5: Model Serialization & Deserialization via Joblib
    # ------------------------------------------------------------
    print("  -> Testing model serialization (joblib) and inference persistence...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "churn_pipeline.joblib"

        # Save pipeline artifact
        joblib.dump(pipeline, model_path)
        assert model_path.exists()

        # Reload pipeline artifact
        reloaded_pipeline: Pipeline = joblib.load(model_path)

        # Confirm identical predictions on test set
        reloaded_pred = reloaded_pipeline.predict(X_test)
        assert np.array_equal(y_pred, reloaded_pred), "Reloaded model generated divergent predictions"

        # Test single new record inference
        sample_record = pd.DataFrame([{
            "usage_hours": 1.2,
            "support_tickets": -0.5,
            "latency_ms": 2.1,
            "account_age_months": -0.8
        }])
        single_prediction = reloaded_pipeline.predict(sample_record)
        assert single_prediction[0] in [0, 1]

    print("[SUCCESS] All 5 Scikit-Learn Workflow & Evaluation tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9 - 04: Scikit-Learn Workflow, Pipelines & Model Evaluation")
    print("=" * 70)
    run_tests()
    print("=" * 70)
