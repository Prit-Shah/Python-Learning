r"""
03_data_cleaning_and_stats.py

============================================================
1. CONCEPT
============================================================

Data preprocessing, cleansing, and statistical exploration constitute 70-80% of real-world
Data Engineering and Machine Learning pipelines. Raw data contains missingness, noise,
outliers, and mismatched scales that degrade model convergence:

1. Missing Data Handling & Nullable Typing:
   - Legacy `np.nan` (IEEE 754 floating-point NaN):
     * Because `NaN` is a float, presence of a single missing value forces integer columns
       to silently upcast to `float64`, consuming double the memory.
   - Modern Nullable Types (`pd.NA`, `Int64`, `boolean`, `string`):
     * Uses an internal boolean bitmask to track missing entries while retaining integer
       and boolean types. Supports Three-Valued Logic (`True`, `False`, `pd.NA`).
   - Imputation Strategies:
     * Median: Preferred for skewed numerical distributions (robust to outliers).
     * Mean: Appropriate for normal/Gaussian distributions.
     * Mode: Preferred for categorical columns.
     * Forward/Backward fill (`ffill`, `bfill`): Standard for sequential time-series data.

2. Outlier Detection & Mitigation:
   - Interquartile Range (IQR) Method:
     * $\text{IQR} = Q_3 - Q_1$ (75th percentile minus 25th percentile).
     * Lower Bound: $Q_1 - 1.5 \times \text{IQR}$.
     * Upper Bound: $Q_3 + 1.5 \times \text{IQR}$.
     * Points beyond these bounds are statistical outliers.
   - Z-Score Method:
     * $Z = \frac{x - \mu}{\sigma}$. Values with $|Z| > 3.0$ fall beyond 99.7% of a normal distribution.
   - Winsorization (Clipping): Clamps extreme values to percentile bounds without dropping rows.

3. Feature Scaling & Normalization:
   - Min-Max Normalization: Rescales features to a fixed range $[0, 1]$:
     $X_{\text{norm}} = \frac{X - X_{\min}}{X_{\max} - X_{\min}}$.
   - Z-Score Standardization: Centers data to mean $\mu = 0$ with unit variance $\sigma = 1$:
     $X_{\text{std}} = \frac{X - \mu}{\sigma}$. Essential for distance-based ML models (KNN, SVM, PCA, Neural Nets).

4. Statistical Correlation & Covariance:
   - Pearson Correlation Coefficient ($r \in [-1, 1]$): Measures linear relationship between features.
   - Covariance Matrix: Measures directional joint variability across feature dimensions.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Pandas & NumPy)            | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Missing Representation       | `np.nan` (float) / `pd.NA`         | `null` / `undefined` / `NaN`       |
| Missing Check                | `pd.isna(x)` / `pd.notna(x)`       | `x === null || x === undefined`    |
| Imputation                   | `df.fillna(df.median())`           | Custom reduce loop to find median  |
| Outlier Filtering            | Vectorized `df[df["val"] < upper]` | `items.filter(x => x.val < upper)` |
| Percentile / Quantile        | `df.quantile([0.25, 0.75])`        | Manual sort & index calculation    |
| Correlation Matrix           | `df.corr(method="pearson")`        | Multi-pass nested loops / mathjs   |
| Winsorizing / Clipping       | `df["val"].clip(lower, upper)`     | `Math.min(Math.max(x, min), max)`  |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. JavaScript differentiates between `null` (intentional absence) and `undefined` (uninitialized).
   In Python Data Science, `np.nan` is an IEEE 754 float representation where arithmetic operations
   propagate NaN (`5.0 + np.nan = np.nan`).
2. In JS, calculating covariance or quantiles on 1M rows requires writing manual JavaScript loops
   that stress V8 garbage collection. In Pandas, these operations dispatch to multi-threaded Cython
   and C routines using Welford's algorithm for numerically stable variance.


============================================================
3. UNDER THE HOOD (CPython & IEEE 754 Floating Point)
============================================================

1. The IEEE 754 NaN Bit Specification:
   - A 64-bit float comprises: 1 sign bit, 11 exponent bits, and 52 mantissa (fraction) bits.
   - `NaN` is defined by an exponent of all 1s and a non-zero mantissa.
   - By IEEE 754 standard, `NaN != NaN` is mandated at the hardware CPU level!
     Evaluating `np.nan == np.nan` yields `False`.
   - Always evaluate missingness via `pd.isna()` or `np.isnan()`.

2. Numerically Stable Variance & Covariance (Welford's Algorithm):
   - Naive variance calculation $\sum x^2 - \frac{(\sum x)^2}{N}$ suffers from catastrophic
     cancellation (floating-point precision loss when subtracting two huge numbers).
   - NumPy and Pandas implement Welford's single-pass algorithm or two-pass compensated summation,
     updating running means and sum of squared differences incrementally to preserve 64-bit precision.


============================================================
4. COMMON GOTCHAS
============================================================

1. Testing `if x == np.nan`:
   - Because `np.nan == np.nan` evaluates to `False`, checking equality against NaN will NEVER succeed!
   - FIX: Use `pd.isna(x)` or `np.isnan(x)`.

2. Imputing with Mean on Skewed Data:
   - For highly skewed metrics (income, housing prices, web latency), extreme positive outliers
     distort the mean upward.
   - Imputing missing values with the mean injects unrealistic bias. Always use the `median()` for skewed data.

3. Data Leakage During Preprocessing:
   - Calculating global Min/Max or Mean/Std across the ENTIRE dataset before train-test splitting
     leaks target information from test rows into training features.
   - FIX: Compute statistics strictly on the training set, and apply those fitted values to the test set.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Walk me through an end-to-end data cleaning and validation pipeline in Pandas."
A1: "I establish a deterministic data cleaning pipeline in five sequential stages:
     First, Schema Validation & Deduplication: Inspect dtypes, convert date strings with `pd.to_datetime()`,
     and eliminate duplicate records via `df.drop_duplicates(subset=...)`.
     Second, Missingness Profiling: Evaluate `df.isna().mean()`. For columns with under 5% missingness,
     I impute with the median for continuous skewed variables or mode for categorical features, while
     adding missingness indicator flags for downstream ML models.
     Third, Outlier Treatment: Compute IQR bounds and clip extreme values using `.clip()` to prevent
     influential leverage points without discarding valuable training observations.
     Fourth, Feature Scaling: Apply Z-Score standardization for linear and distance-based models or
     Min-Max normalization for bounded neural network inputs.
     Fifth, Integrity Assertions: Validate with automated assertions: `assert df.isna().sum().sum() == 0`
     and verify expected shape constraints before sending data downstream."

Q2: "What is the difference between `np.nan` and Pandas `pd.NA`?"
A2: "`np.nan` is an IEEE 754 floating-point constant. Because it is fundamentally a float, any integer
     column containing `np.nan` must silently upcast to `float64`, which breaks integer semantics and
     wastes memory.
     Pandas introduced `pd.NA` alongside nullable extension types (`Int64`, `boolean`, `string`).
     These types use a separate boolean validity bitmap to track missing positions without mutating the
     underlying integer memory buffer, enabling true integer columns with missing data and consistent
     Three-Valued Logic where `pd.NA & True` yields `pd.NA`."

Q3: "When should you choose Z-Score Standardization over Min-Max Normalization?"
A3: "Min-Max Normalization scales values into a rigid $[0, 1]$ interval. It is sensitive to extreme outliers
     because a single massive value will compress all normal data into a tiny cluster near zero. It is
     best used when data has strictly bounded ranges (such as image pixel values in $[0, 255]$) or algorithms
     requiring bounded intervals (like certain neural network activations).
     Z-Score Standardization centers data around mean 0 with unit variance 1. It does not bound data to a
     finite range and handles outliers much more gracefully. It is standard for linear regression, logistic
     regression, PCA, and algorithms that assume normally distributed feature inputs."
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. DATA CLEANING & STATISTICAL PIPELINE
# ==============================================================================

class DataCleaner:
    """Production data preprocessing and statistical transformation pipeline."""

    @staticmethod
    def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        """
        Imputes numerical columns with median (robust to outliers)
        and categorical columns with mode.
        """
        clean_df = df.copy()
        for col in clean_df.columns:
            if pd.api.types.is_numeric_dtype(clean_df[col]):
                median_val = clean_df[col].median()
                clean_df[col] = clean_df[col].fillna(median_val)
            else:
                mode_val = clean_df[col].mode()
                if not mode_val.empty:
                    clean_df[col] = clean_df[col].fillna(mode_val[0])
        return clean_df

    @staticmethod
    def detect_outliers_iqr(series: pd.Series, factor: float = 1.5) -> pd.Series:
        """Returns boolean mask where True indicates an outlier via IQR method."""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - (factor * iqr)
        upper_bound = q3 + (factor * iqr)
        return (series < lower_bound) | (series > upper_bound)

    @staticmethod
    def winsorize_series(series: pd.Series, lower_q: float = 0.05, upper_q: float = 0.95) -> pd.Series:
        """Clips extreme values to quantile thresholds to neutralize outlier leverage."""
        low_val = series.quantile(lower_q)
        high_val = series.quantile(upper_q)
        return series.clip(lower=low_val, upper=high_val)

    @staticmethod
    def standardize_zscore(series: pd.Series) -> pd.Series:
        """Standardizes series to mean=0 and std=1: (x - mean) / std."""
        std = series.std(ddof=1)
        if std == 0:
            return series - series.mean()
        return (series - series.mean()) / std

    @staticmethod
    def normalize_minmax(series: pd.Series) -> pd.Series:
        """Scales series to [0, 1] range: (x - min) / (max - min)."""
        rng = series.max() - series.min()
        if rng == 0:
            return pd.Series(0.0, index=series.index)
        return (series - series.min()) / rng


# ==============================================================================
# 2. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 03_data_cleaning_and_stats.py...")

    # ------------------------------------------------------------
    # Test 1: Missing Value Imputation (Median & Mode)
    # ------------------------------------------------------------
    print("  -> Testing missing value detection and median/mode imputation...")
    raw_df = pd.DataFrame({
        "age": [25.0, 30.0, np.nan, 40.0, 100.0],  # Median of [25, 30, 40, 100] is 35.0
        "category": ["A", "B", "A", None, "A"]     # Mode is "A"
    })
    # Verify NaN comparison gotcha: np.nan == np.nan is False
    assert (np.nan == np.nan) is False, "IEEE 754 specifies NaN != NaN"
    assert pd.isna(raw_df.loc[2, "age"]) is True

    imputed = DataCleaner.impute_missing_values(raw_df)
    assert imputed.isna().sum().sum() == 0, "No missing values must remain after imputation"
    assert imputed.loc[2, "age"] == 35.0, f"Expected median 35.0, got {imputed.loc[2, 'age']}"
    assert imputed.loc[3, "category"] == "A", "Expected mode 'A'"

    # ------------------------------------------------------------
    # Test 2: IQR Outlier Detection
    # ------------------------------------------------------------
    print("  -> Testing IQR outlier detection...")
    # Normal cluster around 10-20, with extreme outlier 500
    vals = pd.Series([10.0, 12.0, 14.0, 15.0, 16.0, 18.0, 20.0, 500.0])
    outliers_mask = DataCleaner.detect_outliers_iqr(vals)

    assert outliers_mask.iloc[-1] is True or outliers_mask.values[-1] == True, "500 must be flagged as outlier"
    assert outliers_mask.iloc[0:7].sum() == 0, "Normal cluster must not be flagged"

    # ------------------------------------------------------------
    # Test 3: Winsorization / Clipping
    # ------------------------------------------------------------
    print("  -> Testing Winsorization percentile clipping...")
    data_series = pd.Series(range(100), dtype=float)  # 0 to 99
    clipped = DataCleaner.winsorize_series(data_series, lower_q=0.05, upper_q=0.95)

    assert clipped.min() == 4.95 or np.isclose(clipped.min(), 4.95)
    assert clipped.max() == 94.05 or np.isclose(clipped.max(), 94.05)
    assert len(clipped) == 100

    # ------------------------------------------------------------
    # Test 4: Z-Score Standardization & Min-Max Normalization
    # ------------------------------------------------------------
    print("  -> Testing Z-Score standardization and Min-Max scaling...")
    feature = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])

    # Z-score: mean = 30, std = 15.811
    z_scaled = DataCleaner.standardize_zscore(feature)
    assert np.isclose(z_scaled.mean(), 0.0, atol=1e-7)
    assert np.isclose(z_scaled.std(ddof=1), 1.0, atol=1e-7)

    # Min-Max: [10, 50] -> [0.0, 1.0]
    minmax_scaled = DataCleaner.normalize_minmax(feature)
    assert minmax_scaled.min() == 0.0
    assert minmax_scaled.max() == 1.0
    assert minmax_scaled.iloc[2] == 0.5  # 30 is midpoint

    # ------------------------------------------------------------
    # Test 5: Statistical Correlation & Covariance Matrix
    # ------------------------------------------------------------
    print("  -> Testing Pearson correlation and covariance calculations...")
    stats_df = pd.DataFrame({
        "x": [1.0, 2.0, 3.0, 4.0, 5.0],
        "y": [2.0, 4.0, 6.0, 8.0, 10.0],  # Perfect positive correlation (r = 1.0)
        "z": [5.0, 4.0, 3.0, 2.0, 1.0]   # Perfect negative correlation (r = -1.0)
    })

    corr_matrix = stats_df.corr(method="pearson")
    assert np.isclose(corr_matrix.loc["x", "y"], 1.0)
    assert np.isclose(corr_matrix.loc["x", "z"], -1.0)
    assert np.isclose(corr_matrix.loc["x", "x"], 1.0)

    # Covariance of x with itself is variance of x (2.5)
    cov_matrix = stats_df.cov()
    assert np.isclose(cov_matrix.loc["x", "x"], 2.5)

    print("[SUCCESS] All 5 Data Cleaning & Statistics tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9 - 03: Data Cleaning, Preprocessing & Statistical Analytics")
    print("=" * 70)
    run_tests()
    print("=" * 70)
