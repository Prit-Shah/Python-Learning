"""
Phase 9: Data Cleaning, Transformations & Statistics
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Real-world data is messy — missing values, duplicates, wrong types,
     outliers. Data cleaning is 60-80% of any data project. Pandas provides
     fillna, dropna, apply, groupby, merge, pivot_table for all of this.
   - JS/TS Equivalent: In JS you'd chain `.filter().map().reduce()` and use
     lodash's `_.groupBy()`, `_.merge()`. Pandas does the same but on columnar
     data backed by NumPy, so it's orders of magnitude faster on large datasets.
   - Statistics: NumPy and Pandas give you mean, median, std, var, percentile,
     correlation — all as one-liners.

2. UNDER THE HOOD (CPython & Memory):
   - NaN (Not a Number): Pandas uses np.nan (IEEE 754 float NaN) to represent
     missing data. NaN propagates in arithmetic: 5 + NaN = NaN. This is why
     Pandas upcasts int columns with missing values to float64 — there's no
     NaN in int64. (Pandas 1.0+ introduced pd.NA as a solution with nullable
     integer types like Int64 — note the capital I.)
   - groupby() uses a hash table internally — it maps group keys to integer
     labels, then uses these labels to partition the data for aggregation.
     The actual aggregation dispatches to Cython/C, not Python loops.

3. COMMON GOTCHA:
   - NaN comparison: `np.nan == np.nan` is False! NaN is not equal to itself.
     Use pd.isna() or pd.notna() to check for missing values, never `== NaN`.
     In JS, `NaN === NaN` is also false, so this should be familiar — but the
     "silent upcast to float" is Python/Pandas-specific and catches people.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "Walk me through your data cleaning pipeline."
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I start with df.info() and df.describe() to understand shape, dtypes,
       and missing value counts. Then df.duplicated().sum() for duplicate rows."
     * "For missing values: if < 5% of a column, I might fillna with median
       (numeric) or mode (categorical). If > 30%, I consider dropping the column
       entirely. I use df.isna().sum() to quantify per column."
     * "Type corrections: pd.to_datetime for date strings, .astype() for
       numeric conversions, .str.strip().str.lower() for text normalization."
     * "For groupby aggregations: I use .groupby('col').agg() with named
       aggregations for clarity, and always reset_index() after to get a
       clean flat DataFrame."
     * "I validate the pipeline with shape checks, dtype assertions, and
       checking df.isna().sum() == 0 at the end."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
import pandas as pd


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_missing_values():
    """Handling NaN: detection, filling, and dropping."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob", None, "Diana", "Eve"],
        "age": [30, np.nan, 35, 28, np.nan],
        "salary": [95000, 82000, np.nan, 78000, 105000],
        "dept": ["eng", "sales", "eng", None, "eng"],
    })
    print(f"  Raw data:\n{df}")
    print(f"\n  Missing value counts:\n{df.isna().sum()}")
    print(f"  Total missing: {df.isna().sum().sum()}")

    # fillna — fill with a specific value or strategy
    df_filled = df.copy()
    df_filled["age"] = df_filled["age"].fillna(df_filled["age"].median())
    df_filled["salary"] = df_filled["salary"].fillna(df_filled["salary"].mean())
    df_filled["name"] = df_filled["name"].fillna("Unknown")
    df_filled["dept"] = df_filled["dept"].fillna("unassigned")
    print(f"\n  After fillna:\n{df_filled}")

    # dropna — remove rows with any NaN
    df_dropped = df.dropna()
    print(f"\n  After dropna: {len(df_dropped)} rows remain (from {len(df)})")

    # dropna with subset — only check specific columns
    df_partial = df.dropna(subset=["name", "dept"])
    print(f"  dropna(subset=['name','dept']): {len(df_partial)} rows remain")

    # NaN gotcha: NaN != NaN
    assert np.nan != np.nan, "NaN is never equal to itself!"
    assert pd.isna(np.nan), "Use pd.isna() to check for NaN"

    return df_filled


def demonstrate_duplicates_and_types():
    """Removing duplicates and fixing data types."""
    df = pd.DataFrame({
        "id": [1, 2, 2, 3, 4, 4],
        "date_str": ["2024-01-15", "2024-02-20", "2024-02-20",
                      "2024-03-10", "2024-04-05", "2024-04-05"],
        "amount": ["100.50", "200.75", "200.75", "150.25", "300.00", "300.00"],
        "category": ["  Food ", "transport", " FOOD", "Transport", "food", "Food"],
    })
    print(f"  Raw with dupes & messy types:\n{df}")
    print(f"  Duplicated rows: {df.duplicated().sum()}")

    # Remove exact duplicates
    df_deduped = df.drop_duplicates()
    print(f"  After drop_duplicates: {len(df_deduped)} rows")

    # Remove duplicates by subset (keep first)
    df_deduped2 = df.drop_duplicates(subset=["id"], keep="first")
    print(f"  Deduped by 'id': {len(df_deduped2)} rows")

    # Fix types
    df_clean = df_deduped2.copy()
    df_clean["date"] = pd.to_datetime(df_clean["date_str"])
    df_clean["amount"] = df_clean["amount"].astype(float)
    df_clean["category"] = df_clean["category"].str.strip().str.lower()
    df_clean = df_clean.drop(columns=["date_str"])
    print(f"\n  Cleaned:\n{df_clean}")
    print(f"  dtypes:\n{df_clean.dtypes}")

    return df_clean


def demonstrate_groupby_and_aggregation():
    """GroupBy: split-apply-combine pattern."""
    df = pd.DataFrame({
        "dept": ["eng", "eng", "sales", "sales", "eng", "sales"],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"],
        "salary": [95000, 88000, 72000, 78000, 105000, 68000],
        "years": [5, 3, 4, 2, 6, 1],
    })

    # Basic groupby — like lodash _.groupBy() but with aggregation
    dept_stats = df.groupby("dept")["salary"].agg(["mean", "min", "max", "count"])
    print(f"  Salary stats by dept:\n{dept_stats}")

    # Named aggregations (modern Pandas API)
    summary = df.groupby("dept").agg(
        avg_salary=("salary", "mean"),
        total_headcount=("name", "count"),
        max_years=("years", "max"),
    ).reset_index()
    print(f"\n  Named aggregations:\n{summary}")

    # Multiple aggregations on multiple columns
    multi = df.groupby("dept").agg({
        "salary": ["mean", "std"],
        "years": ["min", "max"],
    })
    print(f"\n  Multi-agg:\n{multi}")

    # Transform — applies function and returns same shape (for column creation)
    df["salary_pct_of_dept"] = df.groupby("dept")["salary"].transform(
        lambda x: (x / x.sum() * 100).round(1)
    )
    print(f"\n  With salary % of dept total:\n{df}")

    return summary


def demonstrate_merge_and_concat():
    """Merging (SQL JOIN) and concatenating DataFrames."""
    employees = pd.DataFrame({
        "emp_id": [1, 2, 3, 4],
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "dept_id": [10, 20, 10, 30],
    })
    departments = pd.DataFrame({
        "dept_id": [10, 20, 40],
        "dept_name": ["Engineering", "Sales", "Marketing"],
    })

    # Inner join (default) — like SQL INNER JOIN
    inner = pd.merge(employees, departments, on="dept_id", how="inner")
    print(f"  Inner join:\n{inner}")

    # Left join — keep all employees
    left = pd.merge(employees, departments, on="dept_id", how="left")
    print(f"\n  Left join:\n{left}")

    # Concat — stack DataFrames vertically (like array spread [...a, ...b])
    df1 = pd.DataFrame({"x": [1, 2]})
    df2 = pd.DataFrame({"x": [3, 4]})
    combined = pd.concat([df1, df2], ignore_index=True)
    print(f"\n  Concatenated: {list(combined['x'])}")

    return inner


def demonstrate_statistics():
    """Descriptive statistics and correlation."""
    np.random.seed(42)
    df = pd.DataFrame({
        "height_cm": np.random.normal(170, 10, 100).round(1),
        "weight_kg": np.random.normal(70, 12, 100).round(1),
        "age": np.random.randint(18, 65, 100),
    })

    # .describe() — summary statistics
    print(f"  describe():\n{df.describe().round(2)}")

    # Individual statistics
    print(f"\n  Mean height: {df['height_cm'].mean():.1f} cm")
    print(f"  Median weight: {df['weight_kg'].median():.1f} kg")
    print(f"  Std dev age: {df['age'].std():.1f}")
    print(f"  25th percentile height: {df['height_cm'].quantile(0.25):.1f}")

    # Correlation matrix — Pearson by default
    corr = df.corr(numeric_only=True)
    print(f"\n  Correlation matrix:\n{corr.round(3)}")

    # Value counts — for categorical data
    bins = pd.cut(df["age"], bins=[17, 30, 45, 65], labels=["young", "mid", "senior"])
    print(f"\n  Age distribution:\n{bins.value_counts().sort_index()}")

    return df


def demonstrate_pivot_table():
    """Pivot tables — Excel-like summarization."""
    df = pd.DataFrame({
        "region": ["East", "East", "West", "West", "East", "West"],
        "product": ["A", "B", "A", "B", "A", "A"],
        "revenue": [100, 150, 200, 120, 180, 160],
        "qty": [10, 15, 20, 12, 18, 16],
    })

    pivot = pd.pivot_table(
        df,
        values="revenue",
        index="region",
        columns="product",
        aggfunc="sum",
        fill_value=0,
    )
    print(f"  Pivot table (revenue by region x product):\n{pivot}")

    # Multi-value pivot
    pivot2 = pd.pivot_table(
        df,
        values=["revenue", "qty"],
        index="region",
        aggfunc={"revenue": "sum", "qty": "mean"},
    )
    print(f"\n  Multi-value pivot:\n{pivot2}")

    return pivot


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: fillna
    s = pd.Series([1, np.nan, 3])
    filled = s.fillna(0)
    assert list(filled) == [1.0, 0.0, 3.0], "fillna failed"

    # Test 2: dropna
    df = pd.DataFrame({"a": [1, np.nan, 3], "b": [4, 5, np.nan]})
    dropped = df.dropna()
    assert len(dropped) == 1, "dropna should leave 1 row"

    # Test 3: drop_duplicates
    df = pd.DataFrame({"x": [1, 1, 2, 2, 3]})
    deduped = df.drop_duplicates()
    assert len(deduped) == 3, "Should have 3 unique values"

    # Test 4: String cleaning
    s = pd.Series(["  Hello ", " WORLD"])
    cleaned = s.str.strip().str.lower()
    assert list(cleaned) == ["hello", "world"], "String cleaning failed"

    # Test 5: to_datetime
    s = pd.Series(["2024-01-15", "2024-06-30"])
    dates = pd.to_datetime(s)
    assert dates.dtype == "datetime64[ns]", "Should be datetime64"

    # Test 6: groupby mean
    df = pd.DataFrame({"g": ["a", "a", "b"], "v": [10, 20, 30]})
    means = df.groupby("g")["v"].mean()
    assert means["a"] == 15.0, "Group 'a' mean should be 15"
    assert means["b"] == 30.0, "Group 'b' mean should be 30"

    # Test 7: merge inner
    left = pd.DataFrame({"key": [1, 2, 3], "val": ["a", "b", "c"]})
    right = pd.DataFrame({"key": [2, 3, 4], "info": ["x", "y", "z"]})
    merged = pd.merge(left, right, on="key", how="inner")
    assert len(merged) == 2, "Inner merge should have 2 rows"
    assert list(merged["key"]) == [2, 3], "Merged keys wrong"

    # Test 8: concat
    df1 = pd.DataFrame({"x": [1]})
    df2 = pd.DataFrame({"x": [2]})
    combined = pd.concat([df1, df2], ignore_index=True)
    assert list(combined["x"]) == [1, 2], "Concat failed"

    # Test 9: describe() outputs expected keys
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    desc = df["a"].describe()
    assert "mean" in desc.index, "describe() should include mean"
    assert desc["count"] == 5, "Count should be 5"

    # Test 10: NaN comparison gotcha
    assert not (np.nan == np.nan), "NaN should not equal itself"
    assert pd.isna(np.nan), "pd.isna should detect NaN"
    assert not pd.isna(42), "pd.isna(42) should be False"

    print("[SUCCESS] All 10 Data Cleaning self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9: Data Cleaning, Transformations & Statistics")
    print("=" * 70)
    print("\n--- Missing Values ---")
    demonstrate_missing_values()
    print("\n--- Duplicates & Types ---")
    demonstrate_duplicates_and_types()
    print("\n--- GroupBy & Aggregation ---")
    demonstrate_groupby_and_aggregation()
    print("\n--- Merge & Concat ---")
    demonstrate_merge_and_concat()
    print("\n--- Descriptive Statistics ---")
    demonstrate_statistics()
    print("\n--- Pivot Tables ---")
    demonstrate_pivot_table()
    print("-" * 70)
    run_tests()
    print("=" * 70)
