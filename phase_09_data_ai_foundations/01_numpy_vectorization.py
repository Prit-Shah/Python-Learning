r"""
01_numpy_vectorization.py

============================================================
1. CONCEPT
============================================================

NumPy (Numerical Python) is the foundational high-performance computing library
underpinning the entire Python AI and Data Science ecosystem (PyTorch, TensorFlow,
Pandas, Scikit-Learn, SciPy):

1. The `ndarray` Data Structure:
   - An $N$-dimensional, homogeneous, fixed-size memory container.
   - Key attributes:
     * `shape`: Tuple of array dimensions (e.g., `(3, 4)` for a 3-row by 4-column matrix).
     * `dtype`: Explicit low-level machine type (`np.int32`, `np.float32`, `np.float64`).
     * `strides`: Tuple of bytes to step in each dimension when traversing memory.
     * `ndim`: Total number of array dimensions.
     * `nbytes`: Total memory consumed by the raw byte buffer.

2. Vectorization & Universal Functions (ufuncs):
   - Vectorization: Expressing mathematical operations on entire arrays at once without
     writing explicit Python `for` loops.
   - Universal Functions (`ufunc`): Compiled C-level functions that operate element-by-element
     with hardware-accelerated SIMD (Single Instruction, Multiple Data) CPU vector registers.
   - Eliminates Python interpreter overhead, dynamic type inspection, and reference counting
     during iteration.

3. Array Broadcasting Rules:
   - Allows arithmetic operations between arrays of different shapes without copying data.
   - Rule of Trailing Alignment: Two shapes are compatible if, starting from the trailing
     (rightmost) dimension and working backward:
     1. The dimensions are equal, OR
     2. One of the dimensions is 1.
   - Dimensions of size 1 are virtually stretched using zero-stride indexing without allocating
     additional RAM.

4. Views vs Copies:
   - Slicing (`arr[1:5]`): Returns a VIEW sharing the same underlying memory buffer.
     Mutating the view modifies the original array!
   - Advanced / Fancy Indexing (`arr[[0, 2]]` or boolean masking `arr[arr > 0]`): Always creates
     a NEW heap-allocated COPY.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (NumPy)                     | JavaScript / TypeScript (V8)       |
+------------------------------+------------------------------------+------------------------------------+
| Typed Buffer                 | `np.ndarray` (multi-dimensional)   | `Float64Array` / `TypedArray` (1D) |
| Element-wise Math            | `arr * 2 + 5` (vectorized C loop)  | `arr.map(x => x * 2 + 5)` (JS loop)|
| Multi-Dimensional Shape      | Native shape tuple `(rows, cols)`  | Array of arrays `number[][]`       |
| Broadcasting                 | Automatic shape alignment          | Manual nested loops                |
| Slicing Mechanics            | Zero-copy strided view (`arr[1:4]`)| `arr.slice(1, 4)` (allocates copy) |
| Linear Algebra               | Native matrix operator `A @ B`     | Custom loops or `mathjs` library   |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. JavaScript's `TypedArray` (`Float64Array`) provides contiguous memory for 1D arrays, but
   lacks multi-dimensional strides, broadcasting, and matrix math. In JS, multidimensional tables
   are modeled as arrays of arrays (`[][]`), which introduces pointer-chasing memory fragmentation.
2. In JS, `array.slice()` always returns a shallow copy with newly allocated memory. In NumPy,
   basic slicing returns a view that points directly to the original memory buffer with adjusted
   strides and offsets.


============================================================
3. UNDER THE HOOD (CPython & Memory Layout)
============================================================

1. Python List vs NumPy `ndarray` Memory Layout:
   - Python List: An array of pointers (`PyObject*`). Each integer or float is a boxed heap
     object with a 16-byte `PyObject_HEAD` (refcount + type pointer) plus value.
     A list of 1,000,000 64-bit floats requires ~36 MB of memory due to pointer chasing and boxing.
   - NumPy Array: A single contiguous block of raw C memory bytes.
     A 1,000,000 float64 array requires exactly $1,000,000 \times 8 \text{ bytes} = 8 \text{ MB}$.

2. Memory Strides & Row-Major Order (C-Contiguous):
   - For an array with shape `(3, 4)` and `dtype=float64` (8 bytes per item):
     * `strides = (32, 8)`.
     * To move down 1 row, advance $4 \times 8 = 32$ bytes.
     * To move right 1 column, advance $1 \times 8 = 8$ bytes.
   - Memory address formula: $\text{addr}(i, j) = \text{base} + i \cdot \text{stride}_0 + j \cdot \text{stride}_1$.

3. Hardware Acceleration & GIL Release:
   - NumPy universal functions are implemented in compiled C and Fortran.
   - Modern CPUs execute SIMD instructions (AVX-512, AVX2, NEON), computing 4 to 8 double-precision
     floating-point multiplications simultaneously in a single clock cycle.
   - NumPy releases the Python GIL during heavy vector calculations, allowing linear algebra
     libraries (OpenBLAS, Intel MKL) to leverage all available CPU threads in parallel.


============================================================
4. COMMON GOTCHAS
============================================================

1. Accidental In-Place Mutation via Slicing Views:
   - Slicing `sub = arr[0:5]` does NOT copy data.
   - Writing `sub[0] = 999` silently mutates `arr[0]` in the original dataset!
   - FIX: Explicitly call `.copy()` whenever independent data is required: `sub = arr[0:5].copy()`.

2. The Python List Appending Anti-Pattern:
   - Trying to grow NumPy arrays inside a loop using `np.append(arr, item)` creates a complete
     new memory copy on EVERY iteration, degrading performance to $O(N^2)$.
   - FIX: Pre-allocate the array using `np.zeros(size)` or build a standard Python list and convert
     once via `np.array(list)`.

3. Axis Orientation Confusion:
   - `axis=0` operates along dimension 0, collapsing rows (computes column-wise sums/means).
   - `axis=1` operates along dimension 1, collapsing columns (computes row-wise sums/means).


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Why is NumPy vectorization 50 to 100 times faster than a standard Python for-loop?"
A1: "NumPy achieves orders-of-magnitude speedups through three architectural factors:
     First, Memory Layout: NumPy stores data in raw, contiguous C-buffers without the `PyObject`
     header overhead or pointer indirection of standard Python lists, enabling optimal CPU L1/L2
     cache locality.
     Second, SIMD Parallelism: NumPy ufuncs execute compiled C loops that utilize modern CPU vector
     registers (such as AVX-512), calculating multiple floating-point operations per clock cycle.
     Third, Elimination of Dynamic Dispatch: A Python for-loop inspects types and increments/decrements
     reference counts on every iteration; NumPy executes statically-typed loops entirely in C and
     releases the GIL for parallel computation."

Q2: "Explain the Broadcasting rules in NumPy and how stride manipulation avoids memory allocation."
A2: "Broadcasting aligns arrays of differing shapes by evaluating their dimensions from right to left.
     Two dimensions are compatible if they are equal or if one of them is 1. If a dimension is 1,
     NumPy virtually stretches that dimension to match the other array.
     Under the hood, NumPy achieves this using stride tricks: by setting the memory stride for that
     dimension to 0 bytes, advancing along that dimension repeatedly reads the exact same memory address.
     This allows operations like adding a 1D vector to a 2D matrix with zero additional memory allocation."

Q3: "What is the difference between a View and a Copy in NumPy, and how can you programmatically verify it?"
A3: "A View is an array object with its own shape and strides that points to the exact same underlying
     memory buffer as another array. Basic slicing (`arr[1:5]`) returns a view, meaning mutations to
     the slice directly alter the original array.
     A Copy is a brand-new, independent memory allocation. Boolean masking (`arr[arr > 0]`) and fancy
     indexing (`arr[[0, 2]]`) always return copies.
     To programmatically verify whether two arrays share memory, we inspect `arr.base` (which returns
     the root array if it's a view, or `None` if it owns its memory) or call `np.shares_memory(a, b)`."
"""

import sys
import time
import warnings
warnings.filterwarnings("ignore")
import numpy as np

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. DEMONSTRATION & BENCHMARK FUNCTIONS
# ==============================================================================

def benchmark_loop_vs_vectorized(n: int = 100_000) -> dict:
    """
    Demonstrates empirical performance difference between a pure Python loop
    and compiled NumPy SIMD vectorization.
    """
    py_list = list(range(n))
    np_arr = np.arange(n, dtype=np.float64)

    # 1. Pure Python Loop
    t0 = time.perf_counter()
    _ = [x * 2.5 + 1.0 for x in py_list]
    py_time = time.perf_counter() - t0

    # 2. NumPy Vectorized Execution
    t1 = time.perf_counter()
    _ = np_arr * 2.5 + 1.0
    np_time = time.perf_counter() - t1

    speedup = py_time / np_time if np_time > 0 else 1.0
    return {
        "n_elements": n,
        "python_loop_sec": py_time,
        "numpy_vectorized_sec": np_time,
        "speedup_factor": speedup
    }


def demonstrate_broadcasting() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Demonstrates zero-copy broadcasting: adding a (3, 1) column vector
    to a (1, 4) row vector yields a (3, 4) matrix.
    """
    col_vector = np.array([[10], [20], [30]])  # shape: (3, 1)
    row_vector = np.array([[1, 2, 3, 4]])      # shape: (1, 4)

    # Broadcasting aligns shapes: (3, 1) + (1, 4) -> (3, 4)
    result_matrix = col_vector + row_vector
    return col_vector, row_vector, result_matrix


# ==============================================================================
# 2. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 01_numpy_vectorization.py...")

    # ------------------------------------------------------------
    # Test 1: Array Shape, Dtypes & Memory Strides
    # ------------------------------------------------------------
    print("  -> Testing ndarray shape, dtype and strided memory layout...")
    arr = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
    assert arr.shape == (2, 3)
    assert arr.dtype == np.int32
    assert arr.ndim == 2
    assert arr.itemsize == 4  # 32 bits = 4 bytes
    assert arr.nbytes == 2 * 3 * 4  # 24 bytes total
    # C-contiguous strides: move 1 row = 3 items * 4 bytes = 12 bytes; move 1 col = 4 bytes
    assert arr.strides == (12, 4)

    # ------------------------------------------------------------
    # Test 2: Vectorization & Arithmetic Operations
    # ------------------------------------------------------------
    print("  -> Testing SIMD vectorization and ufunc operations...")
    data = np.array([1.0, 4.0, 9.0, 16.0], dtype=np.float64)
    sqrt_res = np.sqrt(data)
    assert np.allclose(sqrt_res, [1.0, 2.0, 3.0, 4.0])

    scaled = data * 2.0 - 1.0
    assert np.allclose(scaled, [1.0, 7.0, 17.0, 31.0])

    # ------------------------------------------------------------
    # Test 3: Broadcasting Mechanics
    # ------------------------------------------------------------
    print("  -> Testing broadcasting dimension alignment rules...")
    col_v, row_v, broadcast_res = demonstrate_broadcasting()
    assert broadcast_res.shape == (3, 4)
    expected_matrix = np.array([
        [11, 12, 13, 14],
        [21, 22, 23, 24],
        [31, 32, 33, 34]
    ])
    assert np.array_equal(broadcast_res, expected_matrix)

    # Incompatible shape broadcasting must raise ValueError
    a_bad = np.zeros((2, 3))
    b_bad = np.zeros((2, 4))
    try:
        _ = a_bad + b_bad
        assert False, "Should raise ValueError on incompatible broadcast shapes"
    except ValueError:
        pass

    # ------------------------------------------------------------
    # Test 4: Views vs Copies Memory Verification
    # ------------------------------------------------------------
    print("  -> Testing View vs Copy memory sharing and mutation...")
    original = np.array([10, 20, 30, 40, 50], dtype=np.int64)

    # Basic slice creates a VIEW
    view_slice = original[1:4]
    assert np.shares_memory(original, view_slice) is True
    assert view_slice.base is original

    # Modifying the view modifies the original
    view_slice[0] = 999
    assert original[1] == 999, "Mutating view must alter parent array"

    # Boolean indexing creates a COPY
    copy_mask = original[original > 50]
    assert np.shares_memory(original, copy_mask) is False
    assert copy_mask.base is None
    copy_mask[0] = 0
    assert original[1] == 999, "Mutating copy must NOT alter parent array"

    # Explicit .copy() creates independent buffer
    explicit_copy = original.copy()
    assert np.shares_memory(original, explicit_copy) is False

    # ------------------------------------------------------------
    # Test 5: Reductions & Linear Algebra Matrix Multiplication (@)
    # ------------------------------------------------------------
    print("  -> Testing reduction axes and matrix dot products...")
    mat = np.array([
        [1, 2, 3],
        [4, 5, 6]
    ])
    # axis=0: sum down columns (result shape: (3,))
    assert np.array_equal(mat.sum(axis=0), [5, 7, 9])
    # axis=1: sum across rows (result shape: (2,))
    assert np.array_equal(mat.sum(axis=1), [6, 15])

    # Matrix multiplication (@ operator): (2, 3) @ (3, 2) -> (2, 2)
    mat_b = np.array([
        [1, 2],
        [3, 4],
        [5, 6]
    ])
    mat_mult = mat @ mat_b
    assert mat_mult.shape == (2, 2)
    # [1*1 + 2*3 + 3*5, 1*2 + 2*4 + 3*6] = [22, 28]
    # [4*1 + 5*3 + 6*5, 4*2 + 5*4 + 6*6] = [49, 64]
    assert np.array_equal(mat_mult, [[22, 28], [49, 64]])

    # L2 Euclidean vector norm
    vec = np.array([3.0, 4.0])
    l2_norm = np.linalg.norm(vec)
    assert np.isclose(l2_norm, 5.0)

    print("[SUCCESS] All 5 NumPy Vectorization & Linear Algebra tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 9 - 01: NumPy ndarrays, Vectorization & Memory Strides")
    print("=" * 70)
    bench = benchmark_loop_vs_vectorized(100_000)
    print(f"  Benchmark (100k items): Python Loop = {bench['python_loop_sec']:.4f}s | "
          f"NumPy = {bench['numpy_vectorized_sec']:.4f}s | Speedup: {bench['speedup_factor']:.1f}x")
    run_tests()
    print("=" * 70)
