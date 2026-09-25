"""
Phase 9: scikit-learn ML Workflow — From Data to Prediction
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: scikit-learn (sklearn) provides the standard ML workflow in Python:
     Dataset -> Split -> Preprocess -> Train (fit) -> Evaluate (score) -> Predict.
     It covers regression, classification, clustering, and all data transformations.
   - JS/TS Equivalent: TensorFlow.js exists, but there's nothing comparable to
     sklearn's breadth in JS. sklearn is like if Express.js existed for ML —
     a batteries-included framework where you swap models via a uniform API:
     every estimator has .fit(X, y), .predict(X), and .score(X, y).
   - Key insight: sklearn DOES NOT do deep learning (that's PyTorch/TensorFlow).
     sklearn is for classical ML: linear/logistic regression, random forests,
     SVMs, k-means, etc. These cover 80% of real-world ML problems.

2. UNDER THE HOOD (CPython & Memory):
   - sklearn is built on NumPy and SciPy. Models store learned parameters as
     NumPy arrays (e.g., linear regression coefficients are a float64 array).
   - .fit() mutates the estimator in-place: `model.fit(X, y)` trains the model
     and stores the learned parameters as attributes (e.g., model.coef_,
     model.intercept_). The trailing underscore convention means "set by fit."
   - Pipeline: sklearn's Pipeline chains transformers + estimator into a single
     object. Calling pipeline.fit(X, y) calls fit_transform() on each
     transformer sequentially, then fit() on the final estimator.

3. COMMON GOTCHA:
   - Data leakage: If you normalize/scale your data BEFORE splitting into
     train/test, the test set statistics leak into the scaler. Always fit
     the scaler on train data only, then transform both train and test.
     sklearn's Pipeline prevents this by fitting only during pipeline.fit().

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "Walk me through a typical ML pipeline."
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I start with exploratory data analysis — checking distributions, missing
       values, and correlations using Pandas describe() and corr()."
     * "Then I split into train and test sets FIRST, typically 80/20, using
       train_test_split with a fixed random_state for reproducibility."
     * "Preprocessing happens inside a Pipeline to prevent data leakage:
       StandardScaler for numeric features, OneHotEncoder for categoricals,
       combined with ColumnTransformer."
     * "I choose a model based on the problem type: LinearRegression or
       RandomForest for regression, LogisticRegression or RandomForest for
       classification. I start simple, then increase complexity if needed."
     * "Evaluation: for regression I use MSE, RMSE, R-squared. For classification
       I use accuracy, precision, recall, F1, and a confusion matrix. I watch
       for overfitting by comparing train vs test scores."
     * "If the model overfits, I add regularization, reduce features, or use
       cross-validation with GridSearchCV to tune hyperparameters."

   - Interview Question: "Explain overfitting vs underfitting."
   - How to Answer Out Loud:
     * "Overfitting means the model memorizes the training data including noise.
       It scores high on train data but poorly on unseen test data. Signs:
       train accuracy 99%, test accuracy 70%. Fixes: more data, regularization
       (L1/L2), simpler model, or dropout/early stopping for neural nets."
     * "Underfitting means the model is too simple to capture the patterns.
       Both train and test scores are low. Fixes: more features, a more
       complex model, or reduced regularization."
     * "The sweet spot is where test performance is maximized — this is the
       bias-variance tradeoff."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
from sklearn.datasets import make_regression, make_classification


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_train_test_split():
    """The FIRST step: split data before any preprocessing."""
    # Generate synthetic regression data
    X, y = make_regression(n_samples=200, n_features=3, noise=10, random_state=42)

    # Split BEFORE any scaling/preprocessing (prevents data leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,       # 20% for testing
        random_state=42,     # Reproducibility — same as fixing Math.random seed
    )
    print(f"  Total samples: {len(X)}")
    print(f"  Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples")
    print(f"  X_train shape: {X_train.shape}")  # (160, 3) — 160 samples, 3 features

    # In JS: you'd manually shuffle and slice the array
    # const shuffled = [...data].sort(() => Math.random() - 0.5)
    # const train = shuffled.slice(0, 160), test = shuffled.slice(160)

    return X_train, X_test, y_train, y_test


def demonstrate_linear_regression():
    """Regression: predicting a continuous value."""
    # Synthetic housing-like data
    np.random.seed(42)
    n = 200
    sqft = np.random.uniform(500, 3000, n)
    bedrooms = np.random.randint(1, 6, n)
    noise = np.random.normal(0, 20000, n)
    # True relationship: price = 150*sqft + 30000*bedrooms + noise
    price = 150 * sqft + 30000 * bedrooms + noise

    X = pd.DataFrame({"sqft": sqft, "bedrooms": bedrooms})
    y = price

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Pipeline: Scale -> Fit (prevents data leakage)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),      # Normalize features to mean=0, std=1
        ("model", LinearRegression()),      # Ordinary Least Squares
    ])

    # .fit() trains the model — mutates pipeline in-place
    pipeline.fit(X_train, y_train)

    # .predict() uses the trained model
    y_pred = pipeline.predict(X_test)

    # Evaluation metrics for regression
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print(f"  Linear Regression Results:")
    print(f"    MSE  = {mse:,.0f}")
    print(f"    RMSE = {rmse:,.0f}")
    print(f"    R2   = {r2:.4f} (1.0 = perfect, 0.0 = predicting mean)")

    # Access learned parameters
    model = pipeline.named_steps["model"]
    print(f"    Coefficients: {model.coef_.round(2)}")  # [~150, ~30000]
    print(f"    Intercept: {model.intercept_:.2f}")

    # Predict a new house
    new_house = pd.DataFrame({"sqft": [1500], "bedrooms": [3]})
    predicted_price = pipeline.predict(new_house)
    print(f"    Predicted price for 1500sqft 3BR: \${predicted_price[0]:,.0f}")

    return pipeline, r2


def demonstrate_classification():
    """Classification: predicting a category/label."""
    # Synthetic binary classification data
    X, y = make_classification(
        n_samples=300,
        n_features=4,
        n_informative=3,
        n_redundant=1,
        random_state=42,
    )
    feature_names = ["feature_1", "feature_2", "feature_3", "feature_4"]
    X_df = pd.DataFrame(X, columns=feature_names)

    X_train, X_test, y_train, y_test = train_test_split(
        X_df, y, test_size=0.2, random_state=42, stratify=y
    )
    # stratify=y ensures class proportions are preserved in both splits

    print(f"  Class distribution (train): {np.bincount(y_train)}")
    print(f"  Class distribution (test):  {np.bincount(y_test)}")

    # Logistic Regression — despite the name, it's a CLASSIFIER
    log_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(random_state=42)),
    ])
    log_pipeline.fit(X_train, y_train)
    y_pred_log = log_pipeline.predict(X_test)

    # Random Forest — ensemble of decision trees
    rf_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestClassifier(n_estimators=100, random_state=42)),
    ])
    rf_pipeline.fit(X_train, y_train)
    y_pred_rf = rf_pipeline.predict(X_test)

    # Classification metrics
    for name, y_pred in [("Logistic Regression", y_pred_log), ("Random Forest", y_pred_rf)]:
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        print(f"\n  {name}:")
        print(f"    Accuracy  = {acc:.4f}")
        print(f"    Precision = {prec:.4f} (of predicted positives, how many are correct)")
        print(f"    Recall    = {rec:.4f} (of actual positives, how many did we find)")
        print(f"    F1 Score  = {f1:.4f} (harmonic mean of precision and recall)")

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred_rf)
    print(f"\n  Confusion Matrix (RF):")
    print(f"    [[TN={cm[0,0]}, FP={cm[0,1]}],")
    print(f"     [FN={cm[1,0]}, TP={cm[1,1]}]]")

    return log_pipeline, rf_pipeline


def demonstrate_cross_validation():
    """Cross-validation: more robust evaluation than a single train/test split."""
    X, y = make_classification(n_samples=200, n_features=4, random_state=42)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(random_state=42)),
    ])

    # 5-fold cross-validation: splits data into 5 folds, trains 5 times,
    # each time using a different fold as the test set
    scores = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"  5-Fold CV Accuracy: {scores}")
    print(f"  Mean: {scores.mean():.4f} +/- {scores.std():.4f}")

    # This is more reliable than a single split because it uses all data
    # for both training and testing (just not at the same time)

    return scores


def demonstrate_feature_engineering():
    """Feature engineering: creating better features from raw data."""
    np.random.seed(42)
    df = pd.DataFrame({
        "length": np.random.uniform(5, 20, 100),
        "width": np.random.uniform(3, 10, 100),
        "material": np.random.choice(["wood", "metal", "plastic"], 100),
    })
    # True target: area + material bonus
    material_bonus = df["material"].map({"wood": 10, "metal": 25, "plastic": 5})
    df["price"] = df["length"] * df["width"] * 2 + material_bonus + np.random.normal(0, 5, 100)

    # Feature engineering: create interaction feature
    df["area"] = df["length"] * df["width"]
    df["perimeter"] = 2 * (df["length"] + df["width"])

    # Encode categorical: LabelEncoder (ordinal) or pd.get_dummies (one-hot)
    df_encoded = pd.get_dummies(df, columns=["material"], drop_first=True)
    print(f"  After get_dummies:\n{df_encoded.head()}")
    print(f"  Columns: {list(df_encoded.columns)}")

    # Train with engineered features
    feature_cols = [c for c in df_encoded.columns if c != "price"]
    X = df_encoded[feature_cols]
    y = df_encoded["price"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ])
    model.fit(X_train, y_train)

    r2_train = model.score(X_train, y_train)
    r2_test = model.score(X_test, y_test)
    print(f"\n  R2 (train): {r2_train:.4f}")
    print(f"  R2 (test):  {r2_test:.4f}")

    # Overfitting check: if train >> test, model is memorizing
    gap = r2_train - r2_test
    status = "OK" if gap < 0.1 else "POTENTIAL OVERFITTING"
    print(f"  Train-Test gap: {gap:.4f} ({status})")

    return model


def demonstrate_overfitting_underfitting():
    """Visualize overfitting vs underfitting concepts (without plots)."""
    from sklearn.preprocessing import PolynomialFeatures

    # Generate simple nonlinear data
    np.random.seed(42)
    X = np.sort(np.random.uniform(0, 10, 50)).reshape(-1, 1)
    y = np.sin(X).ravel() + np.random.normal(0, 0.2, 50)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    results = {}
    for degree in [1, 3, 15]:
        pipe = Pipeline([
            ("poly", PolynomialFeatures(degree=degree, include_bias=False)),
            ("model", LinearRegression()),
        ])
        pipe.fit(X_train, y_train)
        train_r2 = pipe.score(X_train, y_train)
        test_r2 = pipe.score(X_test, y_test)
        results[degree] = (train_r2, test_r2)
        label = {1: "UNDERFIT", 3: "GOOD FIT", 15: "OVERFIT"}[degree]
        print(f"  Degree {degree:2d} ({label:>8s}): Train R2={train_r2:.4f}, Test R2={test_r2:.4f}")

    # Degree 1: Underfit — both scores low (too simple for sinusoidal data)
    # Degree 3: Good fit — both scores high and close
    # Degree 15: Overfit — train very high, test drops (memorized noise)

    return results


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: train_test_split preserves total count
    X, y = make_regression(n_samples=100, n_features=2, random_state=42)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    assert len(X_tr) + len(X_te) == 100, "Split should preserve total count"
    assert len(X_tr) == 80, "80/20 split: train should have 80"

    # Test 2: Pipeline fit and predict
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ])
    pipe.fit(X_tr, y_tr)
    preds = pipe.predict(X_te)
    assert preds.shape == (20,), "Predictions shape should match test set"

    # Test 3: R2 score is reasonable for easy data
    r2 = r2_score(y_te, preds)
    assert r2 > 0.5, f"R2 should be decent for easy regression data, got {r2:.4f}"

    # Test 4: Classification accuracy is reasonable
    X_c, y_c = make_classification(n_samples=200, n_features=4, random_state=42)
    X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(X_c, y_c, test_size=0.2, random_state=42)
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(random_state=42)),
    ])
    clf.fit(X_tr_c, y_tr_c)
    acc = accuracy_score(y_te_c, clf.predict(X_te_c))
    assert acc > 0.7, f"Accuracy should be reasonable, got {acc:.4f}"

    # Test 5: Confusion matrix shape
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_pred = np.array([0, 1, 1, 1, 0, 0])
    cm = confusion_matrix(y_true, y_pred)
    assert cm.shape == (2, 2), "Binary confusion matrix should be 2x2"
    assert cm.sum() == len(y_true), "CM should account for all samples"

    # Test 6: Precision, recall, F1
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    assert 0 <= prec <= 1, "Precision should be in [0, 1]"
    assert 0 <= rec <= 1, "Recall should be in [0, 1]"
    assert abs(f1 - 2 * prec * rec / (prec + rec)) < 1e-10, "F1 formula check"

    # Test 7: Cross-validation returns correct number of scores
    scores = cross_val_score(
        LogisticRegression(random_state=42), X_c, y_c, cv=5
    )
    assert len(scores) == 5, "5-fold CV should return 5 scores"
    assert all(0 <= s <= 1 for s in scores), "All CV scores should be in [0, 1]"

    # Test 8: StandardScaler transforms to ~0 mean
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_tr)
    col_means = np.abs(X_scaled.mean(axis=0))
    assert all(m < 1e-10 for m in col_means), "Scaled data should have ~0 mean"

    # Test 9: Feature engineering - get_dummies
    df = pd.DataFrame({"color": ["red", "blue", "red"]})
    encoded = pd.get_dummies(df, columns=["color"], drop_first=True)
    assert "color_red" in encoded.columns, "One-hot encoding should create color_red"
    assert "color_blue" not in encoded.columns, "drop_first should drop first category"

    # Test 10: Overfitting detection — high-degree polynomial
    from sklearn.preprocessing import PolynomialFeatures
    np.random.seed(42)
    X_simple = np.sort(np.random.uniform(0, 5, 30)).reshape(-1, 1)
    y_simple = X_simple.ravel() * 2 + np.random.normal(0, 0.5, 30)
    X_tr_s, X_te_s, y_tr_s, y_te_s = train_test_split(X_simple, y_simple, test_size=0.3, random_state=42)

    simple_pipe = Pipeline([("model", LinearRegression())])
    simple_pipe.fit(X_tr_s, y_tr_s)
    simple_r2 = simple_pipe.score(X_te_s, y_te_s)
    assert simple_r2 > 0.8, f"Simple linear fit on linear data should have high R2, got {simple_r2:.4f}"

    print("[SUCCESS] All 10 scikit-learn self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9: scikit-learn ML Workflow")
    print("=" * 70)
    print("\n--- Train/Test Split ---")
    demonstrate_train_test_split()
    print("\n--- Linear Regression ---")
    demonstrate_linear_regression()
    print("\n--- Classification ---")
    demonstrate_classification()
    print("\n--- Cross-Validation ---")
    demonstrate_cross_validation()
    print("\n--- Feature Engineering ---")
    demonstrate_feature_engineering()
    print("\n--- Overfitting vs Underfitting ---")
    demonstrate_overfitting_underfitting()
    print("-" * 70)
    run_tests()
    print("=" * 70)
