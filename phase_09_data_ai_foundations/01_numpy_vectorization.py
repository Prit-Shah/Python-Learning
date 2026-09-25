"""
Phase 9: NumPy Arrays & Vectorized Operations
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: NumPy is THE numerical computing library in Python. Its ndarray
     is a fixed-type, contiguous-memory array that enables element-wise math
     WITHOUT Python-level loops — this is called "vectorization."
   - JS/TS Equivalent: JavaScript's TypedArrays (Float64Array, Int32Array) are
     the closest analogy — fixed-type, contiguous buffers. But JS has no
     built-in broadcasting, matrix ops, or slicing. In JS you'd do
     `arr.map(x => x * 2)` — in NumPy you just write `arr * 2`.
   - Key difference: NumPy operations are executed in compiled C/Fortran code
     under the hood, so a vectorized `arr * 2` on 1M elements is 50-100x
     faster than a Python for-loop doing the same thing.

2. UNDER THE HOOD (CPython & Memory):
   - A Python list stores an array of PyObject* pointers — each element can be
     any type, each is a separately heap-allocated object with refcount.
   - A NumPy ndarray stores a single contiguous block of raw bytes (dtype).
     There are NO PyObject wrappers per element. A float64 array of 1M elements
     is exactly 8MB of contiguous memory, vs a Python list which needs ~28 bytes
     per float PyObject + 8 bytes per pointer = ~36MB.
   - Vectorized ops call compiled C loops that iterate over this raw buffer
     WITHOUT acquiring/releasing the GIL per element. This is why NumPy
     is "fast" — it's not Python doing the work, it's C.
   - Broadcasting: When shapes differ, NumPy "broadcasts" the smaller array
     across the larger one using stride tricks — no actual data copies happen.

3. COMMON GOTCHA:
   - NumPy arrays are mutable AND assignment creates a VIEW, not a copy.
     `b = a[2:5]` makes b a view into a's memory. Mutating b mutates a.
     This is different from JS `arr.slice(2, 5)` which returns a new array.
     Use `a[2:5].copy()` to get independent data.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "Why is NumPy faster than pure Python for numerical work?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "NumPy stores data in contiguous, fixed-type memory buffers — not as
       Python objects on the heap. A million float64s is exactly 8MB of raw
       bytes with zero per-element overhead."
     * "Vectorized operations dispatch to compiled C/Fortran routines that
       iterate over this raw buffer without GIL contention per element.
       So `arr * 2` doesn't create a million Python float objects — it
       does a tight C loop over 8-byte doubles."
     * "Broadcasting avoids copies: when you add a scalar to a matrix,
       NumPy uses stride tricks to virtually replicate the scalar without
       allocating new memory."
     * "The tradeoff: NumPy arrays are homogeneous and fixed-type. You can't
       mix strings and ints like a Python list. And views share memory, so
       you need to be conscious of when you need .copy()."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_creation_and_dtype():
    """Array creation, dtypes, and memory layout."""
    # From a Python list — NumPy infers dtype
    a = np.array([1, 2, 3, 4, 5])
    print(f"  Array: {a}, dtype={a.dtype}, shape={a.shape}, ndim={a.ndim}")
    print(f"  Itemsize: {a.itemsize} bytes, total bytes: {a.nbytes}")
    # In JS: `new Int64Array([1,2,3,4,5])` — but JS has no int64, only BigInt64Array

    # Explicit dtype
    floats = np.array([1, 2, 3], dtype=np.float32)
    print(f"  Float32 array: {floats}, itemsize={floats.itemsize}")

    # Zeros, ones, arange, linspace — factory functions
    zeros = np.zeros((2, 3))  # 2x3 matrix of 0.0
    ones = np.ones((3,), dtype=np.int32)
    rng = np.arange(0, 10, 2)  # Like Python range but returns ndarray
    lin = np.linspace(0, 1, 5)  # 5 evenly spaced floats in [0, 1]
    print(f"  zeros shape={zeros.shape}, ones={ones}, arange={rng}")
    print(f"  linspace(0,1,5) = {lin}")

    # Identity matrix
    eye = np.eye(3)
    print(f"  Identity 3x3:\n{eye}")

    return a, floats, zeros


def demonstrate_vectorization_vs_loop():
    """Show the power of vectorized operations vs Python loops."""
    size = 100_000
    arr = np.arange(size, dtype=np.float64)

    # Vectorized: element-wise operations without loops
    # In JS you'd write: arr.map(x => x * 2 + 1)
    result = arr * 2 + 1  # Entire operation in C, no Python loop

    # Universal functions (ufuncs) — compiled element-wise operations
    squares = np.square(arr[:5])
    sqrts = np.sqrt(arr[1:6])
    print(f"  arr[:5]         = {arr[:5]}")
    print(f"  arr[:5] * 2 + 1 = {result[:5]}")
    print(f"  np.square       = {squares}")
    print(f"  np.sqrt([1..5]) = {sqrts}")

    # Boolean masking — vectorized filtering (like .filter() in JS)
    data = np.array([10, 25, 3, 47, 8, 33])
    mask = data > 15  # Returns array of bools
    filtered = data[mask]  # Fancy indexing with bool array
    print(f"  data = {data}")
    print(f"  mask (>15) = {mask}")
    print(f"  filtered = {filtered}")

    return result, filtered


def demonstrate_broadcasting():
    """Broadcasting: how NumPy aligns shapes for operations."""
    # Scalar broadcast: adds 10 to every element
    a = np.array([1, 2, 3])
    print(f"  a + 10 = {a + 10}")

    # 1D + 2D broadcasting
    matrix = np.array([[1, 2, 3],
                       [4, 5, 6]])  # shape (2, 3)
    row = np.array([10, 20, 30])     # shape (3,)
    # NumPy broadcasts row across each row of matrix
    result = matrix + row
    print(f"  matrix + row =\n{result}")
    # In JS: you'd need a nested loop or lodash

    # Column broadcast — reshape to (3, 1)
    col = np.array([[100], [200]])  # shape (2, 1)
    result2 = matrix + col
    print(f"  matrix + col =\n{result2}")

    return result, result2


def demonstrate_views_vs_copies():
    """GOTCHA: Slicing creates views, not copies."""
    original = np.array([10, 20, 30, 40, 50])

    # Slice creates a VIEW (shared memory)
    view = original[1:4]
    view[0] = 999  # This MUTATES original!
    print(f"  After view mutation: original = {original}")
    # In JS: arr.slice(1, 4) would create a NEW array

    # Use .copy() for independent data
    original2 = np.array([10, 20, 30, 40, 50])
    independent = original2[1:4].copy()
    independent[0] = 999
    print(f"  After copy mutation: original2 = {original2}")  # Unchanged

    return original, original2


def demonstrate_reshaping_and_stacking():
    """Reshaping, transposing, and combining arrays."""
    a = np.arange(12)
    reshaped = a.reshape(3, 4)  # 3 rows x 4 cols
    print(f"  arange(12).reshape(3,4) =\n{reshaped}")
    print(f"  Transposed =\n{reshaped.T}")

    # Stacking
    x = np.array([1, 2, 3])
    y = np.array([4, 5, 6])
    vstacked = np.vstack([x, y])  # shape (2, 3)
    hstacked = np.hstack([x, y])  # shape (6,)
    print(f"  vstack = {vstacked}")
    print(f"  hstack = {hstacked}")

    return reshaped


def demonstrate_aggregations():
    """Statistical aggregations — the building blocks for data science."""
    data = np.array([14.2, 19.7, 8.3, 22.1, 15.6, 11.4, 18.9])

    print(f"  mean   = {np.mean(data):.2f}")
    print(f"  median = {np.median(data):.2f}")
    print(f"  std    = {np.std(data):.2f}")
    print(f"  var    = {np.var(data):.2f}")
    print(f"  min    = {np.min(data):.2f}, argmin = {np.argmin(data)}")
    print(f"  max    = {np.max(data):.2f}, argmax = {np.argmax(data)}")
    print(f"  sum    = {np.sum(data):.2f}")

    # Axis-based aggregation on 2D
    matrix = np.array([[1, 2, 3],
                       [4, 5, 6]])
    print(f"  sum(axis=0) columns = {matrix.sum(axis=0)}")  # [5, 7, 9]
    print(f"  sum(axis=1) rows    = {matrix.sum(axis=1)}")  # [6, 15]

    return data


def demonstrate_random_and_linear_algebra():
    """NumPy random generation and basic linear algebra."""
    rng = np.random.default_rng(seed=42)  # Modern API (not np.random.seed)

    uniform = rng.uniform(0, 1, size=5)
    normal = rng.normal(loc=0, scale=1, size=5)
    integers = rng.integers(1, 100, size=5)
    print(f"  uniform = {uniform}")
    print(f"  normal  = {normal}")
    print(f"  integers = {integers}")

    # Dot product & matrix multiplication
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])
    dot = np.dot(a, b)  # 1*4 + 2*5 + 3*6 = 32
    print(f"  dot product = {dot}")

    # Matrix multiply with @
    A = np.array([[1, 2], [3, 4]])
    B = np.array([[5, 6], [7, 8]])
    C = A @ B
    print(f"  A @ B =\n{C}")

    return dot, C


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: Dtype and shape
    a = np.array([1.0, 2.0, 3.0])
    assert a.dtype == np.float64, "Default float dtype should be float64"
    assert a.shape == (3,), "Shape mismatch"

    # Test 2: Vectorized arithmetic
    arr = np.array([10, 20, 30])
    result = arr * 2 + 5
    assert np.array_equal(result, np.array([25, 45, 65])), "Vectorized math failed"

    # Test 3: Boolean masking
    data = np.array([1, 5, 3, 8, 2, 7])
    filtered = data[data > 4]
    assert np.array_equal(filtered, np.array([5, 8, 7])), "Boolean mask failed"

    # Test 4: Broadcasting
    matrix = np.ones((2, 3))
    row = np.array([1, 2, 3])
    result = matrix + row
    expected = np.array([[2, 3, 4], [2, 3, 4]])
    assert np.array_equal(result, expected), "Broadcasting failed"

    # Test 5: View vs copy
    orig = np.array([1, 2, 3, 4, 5])
    view = orig[1:4]
    view[0] = 99
    assert orig[1] == 99, "View should mutate original"

    copy = np.array([1, 2, 3, 4, 5])
    independent = copy[1:4].copy()
    independent[0] = 99
    assert copy[1] == 2, "Copy should NOT mutate original"

    # Test 6: Reshape
    flat = np.arange(6)
    reshaped = flat.reshape(2, 3)
    assert reshaped.shape == (2, 3), "Reshape failed"
    assert reshaped[1, 2] == 5, "Element access after reshape failed"

    # Test 7: Aggregations
    data = np.array([2.0, 4.0, 6.0, 8.0])
    assert np.mean(data) == 5.0, "Mean calculation failed"
    assert np.sum(data) == 20.0, "Sum failed"
    assert np.min(data) == 2.0, "Min failed"
    assert np.argmax(data) == 3, "Argmax failed"

    # Test 8: Axis aggregation
    m = np.array([[1, 2], [3, 4]])
    assert np.array_equal(m.sum(axis=0), np.array([4, 6])), "Column sum failed"
    assert np.array_equal(m.sum(axis=1), np.array([3, 7])), "Row sum failed"

    # Test 9: Dot product
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])
    assert np.dot(a, b) == 32, "Dot product failed"

    # Test 10: Matrix multiply with @
    A = np.array([[1, 0], [0, 1]])  # Identity
    B = np.array([[5, 6], [7, 8]])
    assert np.array_equal(A @ B, B), "Identity @ B should equal B"

    print("[SUCCESS] All 10 NumPy self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9: NumPy Arrays & Vectorized Operations")
    print("=" * 70)
    print("\n--- Array Creation & Dtypes ---")
    demonstrate_creation_and_dtype()
    print("\n--- Vectorization vs Loops ---")
    demonstrate_vectorization_vs_loop()
    print("\n--- Broadcasting ---")
    demonstrate_broadcasting()
    print("\n--- Views vs Copies (GOTCHA) ---")
    demonstrate_views_vs_copies()
    print("\n--- Reshaping & Stacking ---")
    demonstrate_reshaping_and_stacking()
    print("\n--- Aggregations ---")
    demonstrate_aggregations()
    print("\n--- Random & Linear Algebra ---")
    demonstrate_random_and_linear_algebra()
    print("-" * 70)
    run_tests()
    print("=" * 70)
