r"""
02_embeddings_and_vector_math.py

============================================================
1. CONCEPT
============================================================

Vector embeddings represent the mathematical bridge between human language and machine
computation. They transform discrete text into continuous dense vectors in high-dimensional
vector spaces $\mathbb{R}^D$ ($D \in \{384, 768, 1536, 3072\}$):

1. Vector Similarity Metrics:
   - Dot Product:
     $$A \cdot B = \sum_{i=1}^D A_i B_i$$
     * Scales with vector magnitude. If vectors have identical angles but different lengths,
       dot product favors longer vectors.
   - Cosine Similarity:
     $$\cos(\theta) = \frac{A \cdot B}{\|A\|_2 \|B\|_2} = \frac{\sum A_i B_i}{\sqrt{\sum A_i^2} \sqrt{\sum B_i^2}}$$
     * Measures the angular difference between vectors, bounded in $[-1.0, 1.0]$.
     * Scale-invariant: independent of document or token length.
   - Euclidean Distance ($L_2$ Norm):
     $$d_2(A, B) = \|A - B\|_2 = \sqrt{\sum_{i=1}^D (A_i - B_i)^2}$$
     * Geometric distance in Euclidean space ($0 \le d_2 < \infty$).
   - Manhattan Distance ($L_1$ Norm):
     $$d_1(A, B) = \sum_{i=1}^D |A_i - B_i|$$

2. The Normalized Unit Vector Identity:
   - If vectors are normalized to unit length ($\|A\|_2 = 1.0$ and $\|B\|_2 = 1.0$):
     $$\cos(\theta) = A \cdot B$$
     $$d_2(A, B)^2 = 2 - 2(A \cdot B) = 2(1 - \cos(\theta))$$
   - Cosine similarity, dot product, and squared Euclidean distance become strictly monotonic!
     Sorting by maximum dot product is mathematically equivalent to sorting by minimum Euclidean distance.

3. High-Speed Batch Search via BLAS Matrix Multiplication:
   - For a query vector $q \in \mathbb{R}^D$ and a document matrix $E \in \mathbb{R}^{N \times D}$:
     $$S = E \cdot q$$
   - Using NumPy and optimized BLAS (Basic Linear Algebra Subprograms), computing similarities
     across 100,000 documents takes under 10 milliseconds on a single CPU core.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (NumPy)                     | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Embedding Buffer             | `np.ndarray(..., dtype=np.float32)`| `Float32Array`                     |
| Dot Product                  | `np.dot(a, b)` / `a @ b`           | Loop multiplying and accumulating  |
| Cosine Similarity            | `np.dot(a, b) / (norm(a)*norm(b))` | Custom function using `reduce()`   |
| Batch Search                 | `scores = matrix @ query`          | Iterating array of `Float32Array`  |
| Top-K Selection              | `np.argpartition(scores, -k)[-k:]` | Custom heap / `sort()`             |
| Quantization                 | Native `.astype(np.float16)`       | `Int8Array` manual conversion      |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Node.js, calculating vector similarities requires looping in JavaScript or using WebAssembly.
   A single-threaded loop over 100,000 1536-dimensional vectors creates significant garbage collection
   and latency spikes.
2. In Python with NumPy, `matrix @ query` dispatches directly to multi-threaded C/Fortran routines
   (OpenBLAS or MKL) utilizing AVX-512 SIMD instructions, evaluating millions of floating-point
   operations per millisecond.


============================================================
3. UNDER THE HOOD (Memory Footprint & Quantization)
============================================================

1. Memory Economics of High-Dimensional Embeddings:
   - 1 vector ($D = 1536$, `float32`): $1536 \times 4 \text{ bytes} = 6,144 \text{ bytes} \approx 6 \text{ KB}$.
   - 100,000 vectors: $\approx 600 \text{ MB}$ raw RAM.
   - 1,000,000 vectors: $\approx 6 \text{ GB}$ raw RAM.
   - In standard Python lists, each float is boxed into a 24-byte `PyObject`, inflating memory
     to $> 30 \text{ GB}$. Storing embeddings as contiguous 2D NumPy arrays is mandatory.

2. Vector Quantization (Scalar & Product Quantization):
   - Scalar Quantization (SQ8): Converts 32-bit floats into 8-bit integers (`int8`), shrinking
     memory consumption by 75% with negligible recall drop ($< 1\%$).
   - Binary Quantization: Reduces each dimension to 1 bit (positive vs negative), accelerating
     similarity search to Hamming distance bitwise `XOR` and `POPCNT` CPU instructions.


============================================================
4. COMMON GOTCHAS
============================================================

1. Using Dot Product on Non-Normalized Vectors:
   - When vectors are not normalized to unit length, longer documents or vectors with large
     magnitudes receive artificially elevated dot products, skewing similarity rankings.
   - FIX: Always normalize embeddings before computing dot products: `v = v / np.linalg.norm(v)`.

2. The Curse of Dimensionality:
   - In spaces with thousands of dimensions ($D \ge 1536$), the ratio between the distance to
     the nearest point and the distance to the farthest point approaches 1 ($d_{\max} \approx d_{\min}$).
   - Cosine similarity remains robust in high dimensions, whereas Euclidean distance without
     normalization loses discriminatory power.

3. Sorting Entire Arrays for Top-K ($O(N \log N)$ vs $O(N)$):
   - Calling `np.argsort(scores)[::-1][:k]` fully sorts all $N$ elements in $O(N \log N)$ time.
   - FIX: Use `np.argpartition(scores, -k)[-k:]`, which finds the top $K$ elements in linear $O(N)$
     time, followed by sorting only the top $K$ items.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the mathematical relationship between Dot Product, Cosine Similarity, and Euclidean Distance."
A1: "Cosine similarity measures the cosine of the angle between two vectors, defined as their dot product
     divided by the product of their L2 norms. Dot product measures both angle and magnitude.
     When vectors are L2-normalized to unit length ($\|A\| = 1$, $\|B\| = 1$), cosine similarity simplifies
     directly to the dot product.
     Furthermore, expanding the squared Euclidean distance between two unit vectors yields:
     $\|A - B\|^2 = \|A\|^2 + \|B\|^2 - 2(A \cdot B) = 2 - 2(A \cdot B) = 2(1 - \cos(\theta))$.
     This proves that for normalized vectors, minimizing Euclidean distance is mathematically identical
     to maximizing cosine similarity. Therefore, in production vector search, we pre-normalize all vectors
     at ingestion time, allowing us to replace expensive square roots and divisions with lightning-fast
     dot product matrix multiplications."

Q2: "How would you implement semantic search over 100,000 document chunks using pure NumPy?"
A2: "I arrange all 100,000 document embeddings into a single 2D NumPy array of shape $(100000, D)$ with
     `dtype=float32` and pre-normalize each row to unit length using `E = E / np.linalg.norm(E, axis=1, keepdims=True)`.
     When a search query arrives, I embed and normalize the query vector $q \in \mathbb{R}^D$.
     I compute the similarity scores for all 100,000 documents simultaneously using a single matrix-vector
     multiplication: `scores = E @ q`.
     To extract the top $K$ results efficiently without the $O(N \log N)$ cost of a full sort, I use
     `np.argpartition(scores, -k)[-k:]` to find the top $K$ indices in $O(N)$ time, sort only those $K$
     scores, and map the indices back to document metadata."

Q3: "What is vector quantization, and why is it used in production vector databases?"
A3: "Vector quantization reduces the precision of high-dimensional embedding vectors to dramatically
     decrease RAM consumption and accelerate nearest-neighbor search.
     In Scalar Quantization (SQ8), each 32-bit floating-point dimension is mapped onto an 8-bit integer,
     reducing memory footprint by 75% (from 6KB to 1.5KB per 1536-dim vector) with less than a 1% impact
     on retrieval accuracy.
     In Product Quantization (PQ), the vector is split into sub-vectors that are mapped to learned centroid
     codebooks. This enables databases like pgvector, Qdrant, and Milvus to keep hundreds of millions of
     vectors resident in RAM or cache, replacing floating-point operations with rapid integer lookups."
"""

import sys
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. VECTOR SIMILARITY ENGINE
# ==============================================================================

class VectorMath:
    """Core mathematical operations for high-dimensional vector representations."""

    @staticmethod
    def l2_normalize(v: np.ndarray) -> np.ndarray:
        """Normalizes vector or 2D matrix rows to unit Euclidean length (L2 norm = 1.0)."""
        if v.ndim == 1:
            norm = np.linalg.norm(v)
            return v / norm if norm > 0 else v
        else:
            norms = np.linalg.norm(v, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return v / norms

    @staticmethod
    def dot_product(a: np.ndarray, b: np.ndarray) -> float:
        """Computes standard dot product: sum(a_i * b_i)."""
        return float(np.dot(a, b))

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Computes cosine similarity: (a . b) / (||a|| * ||b||)."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Computes Euclidean (L2) distance: sqrt(sum((a_i - b_i)^2))."""
        return float(np.linalg.norm(a - b))

    @staticmethod
    def manhattan_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Computes Manhattan (L1) distance: sum(|a_i - b_i|)."""
        return float(np.sum(np.abs(a - b)))


# ==============================================================================
# 2. IN-MEMORY SEMANTIC SEARCH ENGINE
# ==============================================================================

class InMemoryVectorIndex:
    """
    High-performance semantic vector index:
    - Pre-normalizes vectors upon insertion.
    - Uses BLAS matrix multiplication (E @ q) for sub-millisecond retrieval.
    - Employs np.argpartition for linear-time O(N) top-K extraction.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self.doc_ids: List[str] = []
        self.doc_texts: List[str] = []
        self.matrix: Optional[np.ndarray] = None  # Shape: (N, D)

    def add_documents(self, ids: List[str], texts: List[str], vectors: np.ndarray) -> None:
        assert vectors.shape[1] == self.dimension, f"Vector dimension must be {self.dimension}"
        assert len(ids) == len(texts) == len(vectors)

        # Pre-normalize vectors to unit length
        norm_vectors = VectorMath.l2_normalize(vectors)

        if self.matrix is None:
            self.matrix = norm_vectors.astype(np.float32)
        else:
            self.matrix = np.vstack([self.matrix, norm_vectors.astype(np.float32)])

        self.doc_ids.extend(ids)
        self.doc_texts.extend(texts)

    def search(self, query_vector: np.ndarray, top_k: int = 3) -> List[Dict[str, Any]]:
        if self.matrix is None or len(self.doc_ids) == 0:
            return []

        # 1. Normalize query vector
        norm_query = VectorMath.l2_normalize(query_vector).astype(np.float32)

        # 2. Vectorized BLAS matrix-vector dot product (N similarities in 1 operation)
        similarity_scores = self.matrix @ norm_query  # Shape: (N,)

        # 3. Efficient Top-K via argpartition
        n_docs = len(self.doc_ids)
        k = min(top_k, n_docs)

        # argpartition moves top k elements to the end in O(N)
        top_k_indices = np.argpartition(similarity_scores, -k)[-k:]
        # Sort only the top k items in descending order
        top_k_indices = top_k_indices[np.argsort(-similarity_scores[top_k_indices])]

        results = []
        for idx in top_k_indices:
            results.append({
                "id": self.doc_ids[idx],
                "text": self.doc_texts[idx],
                "score": float(similarity_scores[idx])
            })
        return results


# ==============================================================================
# 3. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 02_embeddings_and_vector_math.py...")

    # ------------------------------------------------------------
    # Test 1: Vector Metric Calculations
    # ------------------------------------------------------------
    print("  -> Testing Dot Product, Cosine Similarity, and Euclidean Distance...")
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])  # Orthogonal to v1
    v3 = np.array([2.0, 0.0, 0.0])  # Parallel to v1, double length

    # Orthogonal vectors
    assert VectorMath.dot_product(v1, v2) == 0.0
    assert VectorMath.cosine_similarity(v1, v2) == 0.0
    assert np.isclose(VectorMath.euclidean_distance(v1, v2), np.sqrt(2.0))
    assert VectorMath.manhattan_distance(v1, v2) == 2.0

    # Parallel vectors with different magnitudes
    assert VectorMath.dot_product(v1, v3) == 2.0
    assert np.isclose(VectorMath.cosine_similarity(v1, v3), 1.0), "Cosine similarity must be scale invariant"
    assert VectorMath.euclidean_distance(v1, v3) == 1.0

    # ------------------------------------------------------------
    # Test 2: Unit Vector Mathematical Identity
    # ------------------------------------------------------------
    print("  -> Verifying Normalized Unit Vector Identity: ||u - v||^2 == 2*(1 - cos(theta))...")
    u_raw = np.array([3.0, 4.0, 0.0])
    v_raw = np.array([1.0, 1.0, 1.0])

    u = VectorMath.l2_normalize(u_raw)
    v = VectorMath.l2_normalize(v_raw)

    assert np.isclose(np.linalg.norm(u), 1.0)
    assert np.isclose(np.linalg.norm(v), 1.0)

    # For unit vectors: dot product == cosine similarity
    dot_sim = VectorMath.dot_product(u, v)
    cos_sim = VectorMath.cosine_similarity(u, v)
    assert np.isclose(dot_sim, cos_sim)

    # Euclidean distance identity
    euc_dist_sq = VectorMath.euclidean_distance(u, v) ** 2
    identity_val = 2.0 * (1.0 - cos_sim)
    assert np.isclose(euc_dist_sq, identity_val, atol=1e-7)

    # ------------------------------------------------------------
    # Test 3: High-Dimensional Batch Search Engine
    # ------------------------------------------------------------
    print("  -> Testing in-memory vector index batch search and top-K ranking...")
    dim = 8
    index = InMemoryVectorIndex(dimension=dim)

    # Create 5 synthetic document vectors
    doc_vectors = np.array([
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Doc 1: Perfect match to query
        [0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # Doc 2: High match
        [0.0, 0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0],  # Doc 3: Low match
        [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],  # Doc 4: Orthogonal
        [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], # Doc 5: Opposing direction
    ], dtype=np.float32)

    doc_ids = ["doc_1", "doc_2", "doc_3", "doc_4", "doc_5"]
    doc_texts = [
        "Python FastAPI and async microservices architecture",
        "Python backend web development with databases",
        "Frontend React and Vue user interfaces",
        "DevOps Kubernetes container deployment",
        "Antagonistic unrelated topic"
    ]

    index.add_documents(doc_ids, doc_texts, doc_vectors)

    # Query aligned with dimension 0
    query = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    top_results = index.search(query, top_k=3)

    assert len(top_results) == 3
    # Top 1 must be doc_1 with score 1.0
    assert top_results[0]["id"] == "doc_1"
    assert np.isclose(top_results[0]["score"], 1.0)

    # Top 2 must be doc_2
    assert top_results[1]["id"] == "doc_2"
    assert top_results[1]["score"] > 0.9

    # Score monotonicity
    assert top_results[0]["score"] >= top_results[1]["score"] >= top_results[2]["score"]

    print("[SUCCESS] All 3 Embeddings & Vector Math tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 - 02: Dense Embeddings, Vector Math & Semantic Search")
    print("=" * 70)
    run_tests()
    print("=" * 70)
