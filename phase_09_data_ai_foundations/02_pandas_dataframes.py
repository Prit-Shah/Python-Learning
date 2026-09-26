r"""
02_pandas_dataframes.py

============================================================
1. CONCEPT
============================================================

Pandas is the industry-standard data manipulation and analysis library in Python.
It introduces labeled, multi-dimensional structures optimized for tabular analytics:

1. Core Data Structures:
   - `pd.Series`: 1D labeled homogeneous array wrapping a NumPy ndarray or PyArrow buffer.
     Composed of values, an explicit `Index`, and a `name`.
   - `pd.DataFrame`: 2D labeled tabular container composed of ordered columns.
     Columns are aligned on a shared `Index`.

2. Indexing Paradigms (`.loc` vs `.iloc`):
   - `.loc[row_label, col_label]`: Label-based indexing.
     * Accepts explicit row/column labels, boolean masks, and slices.
     * NOTE: Label slices `loc['A':'C']` are INCLUSIVE of both start and stop!
   - `.iloc[row_pos, col_pos]`: Integer position-based indexing (0 to $N-1$).
     * Adheres to standard Python indexing rules (exclusive of stop: `iloc[0:3]` returns rows 0, 1, 2).

3. High-Performance Vectorized Transformations:
   - Vectorized Arithmetic: Column operations execute at C-speed (`df["total"] = df["qty"] * df["unit_price"]`).
   - Conditional Column Branching: Avoid slow `.apply(lambda ...)` loops by using compiled NumPy
     branching: `np.where(condition, true_val, false_val)` or `np.select(conditions, choices)`.

4. Split-Apply-Combine (`groupby`):
   - Partitions rows into groups by unique key values, applies aggregation/transformation functions,
     and combines results into a new DataFrame.
   - Named Aggregations: `df.groupby("dept").agg(avg_sal=("salary", "mean"), headcount=("id", "count"))`.

5. Relational Merges and Joins:
   - `pd.merge(left, right, on="key", how="inner|left|right|outer")`: Executes relational SQL-style joins.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Pandas)                    | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Table Container              | `pd.DataFrame`                     | `Array<Record<string, any>>`       |
| Column Access                | `df["price"]` (vectorized Series)  | `items.map(x => x.price)`          |
| Row Filtering                | `df.loc[df["age"] >= 21]`          | `items.filter(x => x.age >= 21)`   |
| Position Slicing             | `df.iloc[0:10]`                    | `items.slice(0, 10)`               |
| Aggregation / Grouping       | `df.groupby("city")["age"].mean()` | Custom `reduce()` or Lodash        |
| Relational Join              | `pd.merge(users, orders, on="id")` | Manual nested loops / hash maps    |
| Conditional Mapping          | `np.where(df["score"] > 80, "A")`  | `items.map(x => x.score > 80 ? ..)`|
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In JavaScript, transforming a dataset using `.filter().map()` instantiates intermediate
   heap-allocated JavaScript arrays and objects at every step, creating high garbage-collection
   pressure on large datasets.
2. In Pandas, operations are executed columnar-wise across contiguous C-memory blocks with SIMD
   vectorization, bypassing Python interpreter overhead.


============================================================
3. UNDER THE HOOD (BlockManager & Memory Mechanics)
============================================================

1. The Columnar BlockManager:
   - A Pandas DataFrame does NOT store rows in memory.
   - It organizes columns into homogenous multi-column contiguous 2D memory blocks managed
     by an internal `BlockManager`:
     * `FloatBlock`: Contains all `float64` columns.
     * `IntBlock`: Contains all `int64` columns.
     * `ObjectBlock`: Stores pointers to arbitrary Python objects or strings.
   - Columnar operations like `df["salary"].mean()` access a single contiguous memory block
     with optimal CPU cache locality.

2. Why `df.iterrows()` Is Catastrophically Slow:
   - `iterrows()` transposes columnar blocks into rows on every iteration.
   - For every single row, it instantiates a brand-new Python `pd.Series` object on the heap,
     upcasting all types to `object`.
   - Iterating over 100,000 rows with `iterrows()` takes seconds to minutes; vectorized operations
     execute in milliseconds (a 1,000x speed difference).

3. Modern Copy-on-Write (CoW):
   - In modern Pandas (2.0+), slices of DataFrames return references that share memory buffers
     lazily until an actual write operation occurs.
   - Only when a column in the slice is modified does Pandas trigger an explicit copy of that
     specific column buffer, eliminating accidental mutations and defensive copies.


============================================================
4. COMMON GOTCHAS
============================================================

1. The `SettingWithCopyWarning`:
   - Writing `df[df["age"] > 25]["status"] = "Senior"` performs chained indexing:
     `df[mask]` creates a temporary slice, and `['status'] = ...` attempts to mutate that temporary object.
   - The original DataFrame `df` may NOT be updated, and Python emits `SettingWithCopyWarning`.
   - FIX: Always use `.loc` for assignment: `df.loc[df["age"] > 25, "status"] = "Senior"`.

2. The `.apply(lambda ...)` Trap:
   - Using `.apply()` is simply a Python `for` loop hidden behind a method call.
   - It loses SIMD acceleration and forces Python interpreter context switches on every row.
   - FIX: Use built-in vectorized methods, string accessors (`.str`), or `np.where()`.

3. Storing Categorical Strings as `object`:
   - An `object` column stores individual 8-byte pointers to Python string objects, wasting RAM.
   - Converting repetitive text columns (e.g. state, country, status) to `category` dtype
     replaces strings with integer codes, reducing memory consumption by up to 90%.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Pandas stores a DataFrame in memory and why you should avoid `df.iterrows()`."
A1: "Under the hood, Pandas uses a columnar `BlockManager` that groups columns of the same dtype into
     contiguous 2D NumPy memory arrays—for instance, grouping all float columns into a single contiguous
     buffer. This layout makes column-wise arithmetic extremely fast and cache-efficient.
     `df.iterrows()` is an anti-pattern because it forces row-wise access: on every iteration, Pandas
     must slice across disparate memory blocks, cast heterogeneous types to `object`, and instantiate
     a brand-new Python `Series` object on the heap. This causes massive memory overhead and degrades
     execution speeds by up to a thousand times compared to native vectorized column operations."

Q2: "What is the `SettingWithCopyWarning` and how do you resolve it?"
A2: "The `SettingWithCopyWarning` occurs during chained assignment, such as `df[df['active'] == True]['tier'] = 'Gold'`.
     In chained indexing, Python first executes `df[condition]`, which may return either a view or a temporary
     memory copy. The second operation `['tier'] = ...` modifies that intermediate object. If it was a copy,
     the modification is lost and never reflected in the parent DataFrame.
     To fix it, we use single-index assignment with `.loc`: `df.loc[df['active'] == True, 'tier'] = 'Gold'`.
     This directly references the parent DataFrame's memory buffer in a single atomic operation."

Q3: "How do you conditionally create new columns in Pandas without using `.apply()`?"
A3: "Instead of calling `.apply()` with a Python lambda—which iterates row-by-row in Python bytecode—I use
     vectorized NumPy functions like `np.where()` for binary conditions or `np.select()` for multi-condition logic.
     For example, `df['status'] = np.where(df['score'] >= 70, 'PASS', 'FAIL')`. This evaluates the condition
     and assigns values entirely inside compiled C loops without creating Python-level function call frames,
     achieving 50 to 100 times faster execution."
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
# 1. CORE PIPELINE OPERATIONS
# ==============================================================================

def build_sample_dataset() -> pd.DataFrame:
    """Creates a sample enterprise employee and payroll dataset."""
    return pd.DataFrame({
        "emp_id": [101, 102, 103, 104, 105, 106],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Evan", "Fiona"],
        "department": ["Engineering", "Sales", "Engineering", "Marketing", "Engineering", "Sales"],
        "salary": [135000, 85000, 150000, 92000, 115000, 98000],
        "years_experience": [7, 3, 10, 4, 5, 6],
        "rating": [4.8, 3.9, 4.9, 4.1, 4.2, 4.6]
    })


def compute_compensation_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Demonstrates vectorized transformations and conditional branching
    without slow row-by-row .apply() loops.
    """
    # Create working copy to maintain functional purity
    result_df = df.copy()

    # 1. Vectorized bonus calculation: salary * 0.15 for high rating (>= 4.5), else 0.05
    bonus_multiplier = np.where(result_df["rating"] >= 4.5, 0.15, 0.05)
    result_df["bonus"] = (result_df["salary"] * bonus_multiplier).round(2)
    result_df["total_comp"] = result_df["salary"] + result_df["bonus"]

    # 2. Multi-condition seniority mapping using np.select
    conditions = [
        result_df["years_experience"] >= 8,
        result_df["years_experience"] >= 5,
    ]
    choices = ["Principal / Staff", "Senior"]
    result_df["seniority_level"] = np.select(conditions, choices, default="Associate / Mid")

    return result_df


# ==============================================================================
# 2. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 02_pandas_dataframes.py...")

    # ------------------------------------------------------------
    # Test 1: Series & DataFrame Creation and Types
    # ------------------------------------------------------------
    print("  -> Testing DataFrame construction, indexing and schema validation...")
    df = build_sample_dataset()
    assert df.shape == (6, 6)
    assert list(df.columns) == ["emp_id", "name", "department", "salary", "years_experience", "rating"]
    assert df["salary"].dtype in [np.int64, np.int32]
    assert df["rating"].dtype == np.float64

    # ------------------------------------------------------------
    # Test 2: Indexing with .loc vs .iloc
    # ------------------------------------------------------------
    print("  -> Testing .loc (label-based) vs .iloc (position-based) indexing...")
    # .loc with boolean mask: filter Engineering department
    eng_loc = df.loc[df["department"] == "Engineering", ["name", "salary"]]
    assert len(eng_loc) == 3
    assert list(eng_loc["name"]) == ["Alice", "Charlie", "Evan"]

    # .iloc with positional slice: first 2 rows, first 3 columns
    subset_iloc = df.iloc[0:2, 0:3]
    assert subset_iloc.shape == (2, 3)
    assert list(subset_iloc.columns) == ["emp_id", "name", "department"]
    assert subset_iloc.iloc[0, 1] == "Alice"
    assert subset_iloc.iloc[1, 1] == "Bob"

    # ------------------------------------------------------------
    # Test 3: SettingWithCopy Safe Assignment via .loc
    # ------------------------------------------------------------
    print("  -> Testing mutation and safe assignment via .loc...")
    df_mut = df.copy()
    # Correct assignment using .loc (avoids SettingWithCopyWarning)
    df_mut.loc[df_mut["name"] == "Bob", "salary"] = 90000
    assert df_mut.loc[df_mut["name"] == "Bob", "salary"].values[0] == 90000
    # Original remains untouched
    assert df.loc[df["name"] == "Bob", "salary"].values[0] == 85000

    # ------------------------------------------------------------
    # Test 4: Vectorized Calculations & np.select Branching
    # ------------------------------------------------------------
    print("  -> Testing vectorized metrics computation and conditional branching...")
    processed_df = compute_compensation_metrics(df)

    # Check Charlie: rating 4.9 -> bonus = 150000 * 0.15 = 22500 -> total = 172500
    charlie_row = processed_df.loc[processed_df["name"] == "Charlie"].iloc[0]
    assert charlie_row["bonus"] == 22500.0
    assert charlie_row["total_comp"] == 172500.0
    assert charlie_row["seniority_level"] == "Principal / Staff"

    # Check Bob: rating 3.9 -> bonus = 85000 * 0.05 = 4250 -> total = 89250
    bob_row = processed_df.loc[processed_df["name"] == "Bob"].iloc[0]
    assert bob_row["bonus"] == 4250.0
    assert bob_row["total_comp"] == 89250.0
    assert bob_row["seniority_level"] == "Associate / Mid"

    # ------------------------------------------------------------
    # Test 5: GroupBy Aggregation & Relational Merges
    # ------------------------------------------------------------
    print("  -> Testing split-apply-combine GroupBy and relational merges...")
    # GroupBy department with named aggregations
    dept_summary = df.groupby("department").agg(
        headcount=("emp_id", "count"),
        avg_salary=("salary", "mean")
    ).reset_index()

    assert len(dept_summary) == 3
    eng_summary = dept_summary.loc[dept_summary["department"] == "Engineering"].iloc[0]
    assert eng_summary["headcount"] == 3
    # (135000 + 150000 + 115000) / 3 = 133333.33
    assert np.isclose(eng_summary["avg_salary"], 133333.33, atol=0.01)

    # Relational Join (pd.merge)
    benefits_df = pd.DataFrame({
        "department": ["Engineering", "Sales", "Executive"],
        "stock_units": [1000, 300, 5000]
    })
    # Inner join on department
    merged_inner = pd.merge(df, benefits_df, on="department", how="inner")
    assert len(merged_inner) == 5  # Marketing omitted because it's not in benefits_df

    # Left join preserves Marketing with NaN for stock_units
    merged_left = pd.merge(df, benefits_df, on="department", how="left")
    assert len(merged_left) == 6
    marketing_row = merged_left.loc[merged_left["department"] == "Marketing"].iloc[0]
    assert pd.isna(marketing_row["stock_units"])

    print("[SUCCESS] All 5 Pandas DataFrame & Series tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9 - 02: Pandas DataFrames, Series & Vectorized Transformations")
    print("=" * 70)
    run_tests()
    print("=" * 70)
