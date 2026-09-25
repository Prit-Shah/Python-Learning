"""
Phase 10: Embeddings & Vector Similarity
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Embeddings convert text into dense numerical vectors (arrays of
     floats) that capture semantic meaning. Similar texts have vectors that
     are close in vector space. This is the foundation of semantic search,
     recommendations, and RAG (Retrieval-Augmented Generation).
   - JS/TS Equivalent: No direct equivalent in JS. You might use TensorFlow.js
     embeddings, but in production, you call an embedding API (OpenAI, Cohere)
     and get back a float array. The math (cosine similarity, dot product)
     is the same in any language.
   - Key concepts: Embedding dimensions (1536 for text-embedding-3-small,
     3072 for text-embedding-3-large), cosine similarity (-1 to 1, higher =
     more similar), Euclidean distance (lower = more similar).

2. UNDER THE HOOD (CPython & Memory):
   - Embeddings are NumPy float32 arrays. A 1536-dim embedding is 6KB.
     Storing 1M embeddings = ~6GB of raw float data.
   - Cosine similarity: cos(A, B) = (A . B) / (||A|| * ||B||). NumPy
     computes this in C with BLAS routines — vectorized dot products on
     contiguous memory. For 1536 dims, this is ~3000 float multiplications.
   - For batch similarity (query vs N documents), NumPy matrix multiplication
     `embeddings @ query` computes ALL similarities in one operation — O(N*D)
     where D is dimension, but executed in optimized C/Fortran BLAS.

3. COMMON GOTCHA:
   - Normalizing embeddings: Cosine similarity assumes unit vectors for
     efficient computation. Many APIs return normalized embeddings, but if
     yours doesn't, you must normalize first: `v / np.linalg.norm(v)`.
     Without normalization, dot product != cosine similarity.
   - Dimensionality matters for storage, not just accuracy. 3072-dim
     embeddings use 2x the storage and compute of 1536-dim ones.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How do embeddings work and how would you use them
     for semantic search?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "Embeddings are dense vector representations of text produced by
       neural networks. Similar texts map to nearby points in vector space."
     * "For semantic search: I embed all documents at ingestion time and
       store the vectors. At query time, I embed the user query, then find
       the K nearest document vectors using cosine similarity."
     * "Cosine similarity measures the angle between vectors — it's the
       dot product of normalized vectors, ranging from -1 to 1. I prefer
       it over Euclidean distance because it's scale-invariant."
     * "In production, I use a vector database like pgvector or Qdrant for
       efficient approximate nearest neighbor (ANN) search using HNSW or
       IVFFlat indexes, which turn O(N) brute-force into O(log N)."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════════════
# MOCK EMBEDDING MODEL — Simulates OpenAI's embedding API
# ══════════════════════════════════════════════════════════════════════

class MockEmbeddingModel:
    """
    Simulates embedding generation using simple text features.

    REAL CODE (with OpenAI):
        from openai import OpenAI
        client = OpenAI()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=["Hello world", "Hi there"],
        )
        vectors = [item.embedding for item in response.data]
    """

    def __init__(self, dimensions: int = 64):
        self.dimensions = dimensions
        self._cache: dict[str, np.ndarray] = {}

    def embed(self, text: str) -> np.ndarray:
        """Generate a pseudo-embedding based on text character features."""
        if text in self._cache:
            return self._cache[text]

        # Use deterministic hashing for reproducibility
        np.random.seed(hash(text.lower().strip()) % (2**31))
        base = np.random.randn(self.dimensions).astype(np.float32)

        # Add semantic-ish features based on simple text analysis
        words = text.lower().split()
        word_set = set(words)

        # Nudge similar topics toward similar vectors
        topic_vectors = {
            "python": np.array([1, 0.5, 0, 0] + [0] * (self.dimensions - 4), dtype=np.float32),
            "programming": np.array([0.8, 0.5, 0, 0] + [0] * (self.dimensions - 4), dtype=np.float32),
            "code": np.array([0.7, 0.4, 0, 0] + [0] * (self.dimensions - 4), dtype=np.float32),
            "machine": np.array([0, 0, 1, 0.5] + [0] * (self.dimensions - 4), dtype=np.float32),
            "learning": np.array([0, 0, 0.8, 0.5] + [0] * (self.dimensions - 4), dtype=np.float32),
            "ai": np.array([0, 0, 0.9, 0.7] + [0] * (self.dimensions - 4), dtype=np.float32),
            "food": np.array([0, 0, 0, 0, 1, 0.5] + [0] * (self.dimensions - 6), dtype=np.float32),
            "cooking": np.array([0, 0, 0, 0, 0.8, 0.6] + [0] * (self.dimensions - 6), dtype=np.float32),
            "weather": np.array([0, 0, 0, 0, 0, 0, 1, 0.5] + [0] * (self.dimensions - 8), dtype=np.float32),
        }
        for word, vec in topic_vectors.items():
            if word in word_set:
                base += vec * 2.0

        # Normalize to unit vector (critical for cosine similarity)
        norm = np.linalg.norm(base)
        if norm > 0:
            base = base / norm

        self._cache[text] = base
        return base

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts — returns matrix of shape (N, dimensions)."""
        return np.array([self.embed(t) for t in texts])


# ── Core Vector Math ─────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two vectors.

    cos(A, B) = (A . B) / (||A|| * ||B||)

    For normalized vectors (||A|| = ||B|| = 1), this simplifies to just
    the dot product: cos(A, B) = A . B
    """
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Euclidean (L2) distance between two vectors.
    Lower = more similar. d(A, B) = sqrt(sum((A_i - B_i)^2))
    """
    return float(np.linalg.norm(a - b))


def dot_product_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Dot product — only meaningful for normalized vectors."""
    return float(np.dot(a, b))


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_embedding_basics():
    """Creating and inspecting embeddings."""
    model = MockEmbeddingModel(dimensions=64)

    text = "Python is a great programming language"
    embedding = model.embed(text)

    print(f"  Text: '{text}'")
    print(f"  Embedding shape: {embedding.shape}")
    print(f"  Embedding dtype: {embedding.dtype}")
    print(f"  First 8 values: {embedding[:8].round(4)}")
    print(f"  L2 norm: {np.linalg.norm(embedding):.4f} (should be ~1.0 if normalized)")

    # Batch embedding
    texts = ["Hello world", "Hi there", "Goodbye"]
    batch = model.embed_batch(texts)
    print(f"\n  Batch embedding shape: {batch.shape}")  # (3, 64)

    return embedding


def demonstrate_similarity_search():
    """Semantic similarity — the core of vector search."""
    model = MockEmbeddingModel(dimensions=64)

    # Corpus of documents
    documents = [
        "Python is a great programming language for AI",
        "JavaScript is used for web development",
        "Machine learning models use neural networks",
        "I love cooking Italian food",
        "The weather today is sunny and warm",
        "Deep learning is a subset of AI and machine learning",
        "Python code can be used for data science",
    ]

    # Embed all documents
    doc_embeddings = model.embed_batch(documents)

    # Query
    query = "How to learn Python programming?"
    query_embedding = model.embed(query)

    # Compute similarities
    similarities = []
    for i, doc_emb in enumerate(doc_embeddings):
        sim = cosine_similarity(query_embedding, doc_emb)
        similarities.append((sim, i, documents[i]))

    # Sort by similarity (descending)
    similarities.sort(reverse=True)

    print(f"  Query: '{query}'")
    print(f"  Top results by cosine similarity:")
    for sim, idx, doc in similarities:
        marker = " <-- TOP" if sim == similarities[0][0] else ""
        print(f"    {sim:.4f} | {doc}{marker}")

    return similarities


def demonstrate_similarity_metrics():
    """Comparing different similarity/distance metrics."""
    model = MockEmbeddingModel(dimensions=64)

    pairs = [
        ("Python programming", "Python code"),
        ("Python programming", "Machine learning AI"),
        ("Python programming", "Cooking Italian food"),
    ]

    print(f"  {'Pair':<45} {'Cosine':>8} {'Euclid':>8} {'Dot':>8}")
    print(f"  {'-'*45} {'------':>8} {'------':>8} {'------':>8}")

    for text_a, text_b in pairs:
        a = model.embed(text_a)
        b = model.embed(text_b)
        cos = cosine_similarity(a, b)
        euc = euclidean_distance(a, b)
        dot = dot_product_similarity(a, b)
        label = f"'{text_a}' vs '{text_b}'"
        print(f"  {label:<45} {cos:>8.4f} {euc:>8.4f} {dot:>8.4f}")

    print("\n  Note: For normalized vectors, cosine sim == dot product")
    print("  Cosine: higher = more similar (range -1 to 1)")
    print("  Euclidean: lower = more similar (range 0 to inf)")


def demonstrate_batch_similarity():
    """Efficient batch similarity using matrix multiplication."""
    model = MockEmbeddingModel(dimensions=64)

    documents = [
        "Python programming language",
        "Machine learning with Python",
        "Cooking recipes",
        "Weather forecast",
        "Data science tutorial",
    ]
    doc_embeddings = model.embed_batch(documents)  # shape: (5, 64)
    query_embedding = model.embed("Learn Python for AI")  # shape: (64,)

    # Method 1: Loop (slow for large N)
    loop_sims = [cosine_similarity(query_embedding, d) for d in doc_embeddings]

    # Method 2: Vectorized matrix multiplication (fast!)
    # For normalized vectors: similarity = embeddings @ query
    matrix_sims = doc_embeddings @ query_embedding  # shape: (5,)

    print("  Batch similarity via matrix multiply:")
    for i, (doc, sim) in enumerate(zip(documents, matrix_sims)):
        print(f"    {sim:.4f} | {doc}")

    # Top-K retrieval
    top_k = 3
    top_indices = np.argsort(matrix_sims)[::-1][:top_k]
    print(f"\n  Top-{top_k} results:")
    for idx in top_indices:
        print(f"    [{idx}] {matrix_sims[idx]:.4f} | {documents[idx]}")

    return matrix_sims


def demonstrate_embedding_dimensions():
    """Understanding dimensionality tradeoffs."""
    print("  === Embedding Model Dimensions ===")
    print("  text-embedding-3-small (OpenAI):  1536 dims, 6 KB/vector")
    print("  text-embedding-3-large (OpenAI):  3072 dims, 12 KB/vector")
    print("  text-embedding-ada-002 (legacy):  1536 dims, 6 KB/vector")
    print("  all-MiniLM-L6-v2 (Sentence-BERT): 384 dims, 1.5 KB/vector")
    print()

    # Storage estimation
    for n_docs, dims in [(10_000, 1536), (100_000, 1536), (1_000_000, 1536)]:
        size_mb = (n_docs * dims * 4) / (1024 * 1024)  # float32 = 4 bytes
        print(f"  {n_docs:>10,} docs x {dims} dims = {size_mb:,.0f} MB")

    print()
    print("  Tradeoffs:")
    print("  - Higher dims = better accuracy, more storage/compute")
    print("  - Lower dims = faster search, less RAM, good for prototypes")
    print("  - Matryoshka embeddings: truncate to fewer dims with minimal loss")


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    model = MockEmbeddingModel(dimensions=64)

    # Test 1: Embedding shape and dtype
    emb = model.embed("test text")
    assert emb.shape == (64,), f"Shape should be (64,), got {emb.shape}"
    assert emb.dtype == np.float32, "Dtype should be float32"

    # Test 2: Embeddings are normalized (unit vectors)
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 0.01, f"Norm should be ~1.0, got {norm:.4f}"

    # Test 3: Same text gives same embedding (deterministic)
    emb2 = model.embed("test text")
    assert np.allclose(emb, emb2), "Same text should give same embedding"

    # Test 4: Different text gives different embedding
    emb3 = model.embed("completely different text")
    assert not np.allclose(emb, emb3), "Different text should give different embedding"

    # Test 5: Cosine similarity of identical vectors is 1.0
    sim = cosine_similarity(emb, emb)
    assert abs(sim - 1.0) < 1e-6, f"Self-similarity should be 1.0, got {sim}"

    # Test 6: Cosine similarity range
    a = model.embed("Python programming")
    b = model.embed("Cooking food")
    sim_ab = cosine_similarity(a, b)
    assert -1.0 <= sim_ab <= 1.0, f"Cosine sim should be in [-1, 1], got {sim_ab}"

    # Test 7: Euclidean distance of identical vectors is 0
    dist = euclidean_distance(emb, emb)
    assert abs(dist) < 1e-6, f"Self-distance should be 0, got {dist}"

    # Test 8: Euclidean distance is non-negative
    dist_ab = euclidean_distance(a, b)
    assert dist_ab >= 0, "Distance should be non-negative"

    # Test 9: Batch embedding shape
    batch = model.embed_batch(["a", "b", "c"])
    assert batch.shape == (3, 64), f"Batch shape should be (3, 64), got {batch.shape}"

    # Test 10: Matrix similarity matches loop similarity
    docs = model.embed_batch(["hello", "world", "test"])
    query = model.embed("hello")
    matrix_sims = docs @ query
    loop_sims = np.array([cosine_similarity(query, d) for d in docs])
    assert np.allclose(matrix_sims, loop_sims, atol=0.01), "Matrix sim should match loop sim"

    print("[SUCCESS] All 10 Embedding self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10: Embeddings & Vector Similarity")
    print("=" * 70)
    print("\n--- Embedding Basics ---")
    demonstrate_embedding_basics()
    print("\n--- Similarity Search ---")
    demonstrate_similarity_search()
    print("\n--- Similarity Metrics Comparison ---")
    demonstrate_similarity_metrics()
    print("\n--- Batch Similarity (Matrix Multiply) ---")
    demonstrate_batch_similarity()
    print("\n--- Embedding Dimensions & Storage ---")
    demonstrate_embedding_dimensions()
    print("-" * 70)
    run_tests()
    print("=" * 70)
