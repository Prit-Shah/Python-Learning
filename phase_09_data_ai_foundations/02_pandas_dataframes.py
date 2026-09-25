"""
Phase 9: Pandas DataFrame & Series
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Pandas provides labeled, tabular data structures. A DataFrame is
     a 2D table (like a spreadsheet or SQL result set) with named columns and
     an index. A Series is a single labeled column.
   - JS/TS Equivalent: Think of a DataFrame like an array of uniform objects
     `[{name: "Alice", age: 30}, {name: "Bob", age: 25}]`, but with NumPy
     performance. In JS you'd use lodash/Ramda for groupBy, sortBy, filter —
     Pandas gives you all of that built-in with a consistent, chainable API.
   - Key difference: Pandas is built ON TOP of NumPy. Each column is stored
     as a contiguous NumPy array under the hood. Operations are vectorized C,
     not Python loops.

2. UNDER THE HOOD (CPython & Memory):
   - A DataFrame is a dict-like container of Series objects, each backed by a
     NumPy ndarray. The BlockManager organizes columns by dtype into contiguous
     memory blocks — all int64 columns share one block, all float64 another.
   - This columnar layout means column-wise operations are cache-friendly and
     fast. Row-wise iteration (df.iterrows()) is SLOW because it crosses
     dtype boundaries and creates temporary Series objects per row.
   - Pandas uses Copy-on-Write (CoW) in newer versions (2.0+): when you slice
     a DataFrame, it shares memory until you modify it, then copies lazily.

3. COMMON GOTCHA:
   - SettingWithCopyWarning: `df[df['age'] > 25]['name'] = 'X'` does NOT modify
     df — it modifies a temporary copy. Use df.loc[mask, 'name'] = 'X' instead.
     This is the #1 Pandas trap. In JS, chained property access always works
     on the original object — in Pandas, chained indexing creates temporaries.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How is a Pandas DataFrame stored in memory?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "A DataFrame is essentially a collection of Series objects, each backed
       by a contiguous NumPy array. The BlockManager groups columns by dtype
       into memory blocks — all int64 columns in one block, all float64 in
       another — which makes columnar operations cache-efficient."
     * "This is why column operations like df['price'].mean() are fast — it's
       a single NumPy operation on contiguous memory. But df.iterrows() is
       slow because it constructs a Series per row, crossing dtype boundaries."
     * "For filtering, always use .loc[mask, col] or .query() — never chained
       indexing like df[mask]['col'] = val, which creates ambiguous copies."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
import pandas as pd
import json
import tempfile
from pathlib import Path


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_series_basics():
    """Series: labeled 1D array — the building block of DataFrames."""
    # From a list — auto integer index
    s = pd.Series([10, 20, 30, 40], name="scores")
    print(f"  Series:\n{s}")
    print(f"  dtype={s.dtype}, shape={s.shape}")

    # From a dict — keys become index
    temps = pd.Series({"NYC": 72, "LA": 85, "CHI": 68}, name="temp_f")
    print(f"\n  Named index Series:\n{temps}")
    print(f"  temps['NYC'] = {temps['NYC']}")  # Label-based access
    print(f"  temps.iloc[0] = {temps.iloc[0]}")  # Position-based access

    # Vectorized operations — just like NumPy
    celsius = (temps - 32) * 5 / 9
    print(f"\n  Celsius:\n{celsius.round(1)}")

    return s, temps


def demonstrate_dataframe_creation():
    """Multiple ways to create DataFrames."""
    # From dict of lists (most common)
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "age": [30, 25, 35, 28],
        "city": ["NYC", "LA", "NYC", "CHI"],
        "salary": [95000, 82000, 115000, 78000],
    })
    print(f"  DataFrame from dict:\n{df}")
    print(f"  dtypes:\n{df.dtypes}")
    print(f"  shape: {df.shape} (rows, cols)")
    print(f"  columns: {list(df.columns)}")

    # From list of dicts (like JS array of objects)
    records = [
        {"product": "Widget", "price": 9.99, "qty": 100},
        {"product": "Gadget", "price": 24.99, "qty": 50},
    ]
    df2 = pd.DataFrame(records)
    print(f"\n  From records:\n{df2}")

    return df


def demonstrate_selection_and_filtering():
    """Column selection, row filtering, loc vs iloc."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "dept": ["eng", "sales", "eng", "sales", "eng"],
        "salary": [95000, 82000, 115000, 78000, 105000],
        "years": [5, 3, 8, 2, 6],
    })

    # Column selection
    names = df["name"]  # Returns Series
    subset = df[["name", "salary"]]  # Returns DataFrame
    print(f"  Single column (Series):\n{names.values}")
    print(f"  Multi-column subset:\n{subset}")

    # Row filtering with boolean mask
    engineers = df[df["dept"] == "eng"]
    print(f"\n  Engineers:\n{engineers}")

    # Complex filtering — use & (and), | (or), ~ (not) with parens
    senior_eng = df[(df["dept"] == "eng") & (df["years"] >= 5)]
    print(f"\n  Senior engineers (>= 5 yrs):\n{senior_eng}")

    # .loc — label-based: [row_mask, column_names]
    result = df.loc[df["salary"] > 90000, ["name", "salary"]]
    print(f"\n  .loc filtered:\n{result}")

    # .iloc — integer position-based (like array indexing)
    first_two = df.iloc[0:2, 0:2]  # First 2 rows, first 2 columns
    print(f"\n  .iloc[0:2, 0:2]:\n{first_two}")

    # .query() — SQL-like string syntax (cleaner for complex filters)
    queried = df.query("dept == 'eng' and salary > 100000")
    print(f"\n  .query() result:\n{queried}")

    return df


def demonstrate_csv_json_io():
    """Reading and writing CSV/JSON files."""
    df = pd.DataFrame({
        "product": ["Widget", "Gadget", "Doohickey"],
        "price": [9.99, 24.99, 4.99],
        "qty": [100, 50, 200],
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "products.csv"
        json_path = Path(tmpdir) / "products.json"

        # Write CSV
        df.to_csv(csv_path, index=False)
        print(f"  Wrote CSV to {csv_path.name}")
        csv_content = csv_path.read_text()
        print(f"  CSV content:\n{csv_content}")

        # Read CSV back
        df_csv = pd.read_csv(csv_path)
        print(f"  Read back {len(df_csv)} rows from CSV")

        # Write JSON (orient='records' gives array-of-objects like JS)
        df.to_json(json_path, orient="records", indent=2)
        print(f"  JSON content:\n{json_path.read_text()[:200]}")

        # Read JSON back
        df_json = pd.read_json(json_path)
        print(f"  Read back {len(df_json)} rows from JSON")

    return df


def demonstrate_adding_and_transforming_columns():
    """Adding columns, apply, and map — column transformations."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie"],
        "salary": [95000, 82000, 115000],
        "bonus_pct": [0.10, 0.08, 0.12],
    })

    # Vectorized column creation (fast)
    df["total_comp"] = df["salary"] * (1 + df["bonus_pct"])
    df["tax_bracket"] = np.where(df["salary"] > 90000, "high", "standard")
    print(f"  With new columns:\n{df}")

    # .apply() — row-wise or column-wise custom function
    # CAUTION: .apply() is a Python loop under the hood — slower than vectorized
    df["name_upper"] = df["name"].apply(str.upper)
    # In JS: arr.map(row => row.name.toUpperCase())

    # .map() — element-wise transform on a Series
    bracket_labels = {"high": "H", "standard": "S"}
    df["bracket_code"] = df["tax_bracket"].map(bracket_labels)
    print(f"\n  After apply & map:\n{df}")

    return df


def demonstrate_sorting_and_ranking():
    """Sorting, ranking, and indexing."""
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana"],
        "score": [88, 95, 72, 95],
    })

    # Sort by values
    sorted_df = df.sort_values("score", ascending=False)
    print(f"  Sorted by score desc:\n{sorted_df}")

    # Rank (handles ties)
    df["rank"] = df["score"].rank(ascending=False, method="min")
    print(f"\n  With ranks:\n{df}")

    # Set index
    indexed = df.set_index("name")
    print(f"\n  With name as index:\n{indexed}")
    print(f"  indexed.loc['Alice'] =\n{indexed.loc['Alice']}")

    return df


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: Series creation
    s = pd.Series([1, 2, 3])
    assert s.dtype == np.int64, "Default int dtype should be int64"
    assert len(s) == 3, "Length mismatch"

    # Test 2: DataFrame shape
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert df.shape == (2, 2), "Shape should be (2, 2)"
    assert list(df.columns) == ["a", "b"], "Column names mismatch"

    # Test 3: Boolean filtering
    df = pd.DataFrame({"val": [10, 20, 30, 40]})
    filtered = df[df["val"] > 20]
    assert len(filtered) == 2, "Should have 2 rows > 20"
    assert list(filtered["val"]) == [30, 40], "Filtered values wrong"

    # Test 4: .loc filtering
    df = pd.DataFrame({"name": ["A", "B", "C"], "score": [80, 90, 70]})
    result = df.loc[df["score"] >= 80, "name"]
    assert list(result) == ["A", "B"], ".loc filtering failed"

    # Test 5: Vectorized column creation
    df = pd.DataFrame({"price": [10.0, 20.0], "qty": [5, 3]})
    df["total"] = df["price"] * df["qty"]
    assert list(df["total"]) == [50.0, 60.0], "Vectorized column failed"

    # Test 6: CSV round-trip
    df = pd.DataFrame({"x": [1, 2, 3]})
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.csv"
        df.to_csv(path, index=False)
        df2 = pd.read_csv(path)
        assert list(df2["x"]) == [1, 2, 3], "CSV round-trip failed"

    # Test 7: Sorting
    df = pd.DataFrame({"v": [3, 1, 2]})
    sorted_vals = list(df.sort_values("v")["v"])
    assert sorted_vals == [1, 2, 3], "Sorting failed"

    # Test 8: .apply()
    s = pd.Series(["hello", "world"])
    upper = s.apply(str.upper)
    assert list(upper) == ["HELLO", "WORLD"], ".apply() failed"

    # Test 9: .map() with dict
    s = pd.Series(["a", "b", "c"])
    mapped = s.map({"a": 1, "b": 2, "c": 3})
    assert list(mapped) == [1, 2, 3], ".map() failed"

    # Test 10: .query() method
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 20, 30, 40]})
    result = df.query("x > 2")
    assert len(result) == 2, ".query() filter failed"

    print("[SUCCESS] All 10 Pandas self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9: Pandas DataFrame & Series")
    print("=" * 70)
    print("\n--- Series Basics ---")
    demonstrate_series_basics()
    print("\n--- DataFrame Creation ---")
    demonstrate_dataframe_creation()
    print("\n--- Selection & Filtering ---")
    demonstrate_selection_and_filtering()
    print("\n--- CSV & JSON I/O ---")
    demonstrate_csv_json_io()
    print("\n--- Adding & Transforming Columns ---")
    demonstrate_adding_and_transforming_columns()
    print("\n--- Sorting & Ranking ---")
    demonstrate_sorting_and_ranking()
    print("-" * 70)
    run_tests()
    print("=" * 70)
