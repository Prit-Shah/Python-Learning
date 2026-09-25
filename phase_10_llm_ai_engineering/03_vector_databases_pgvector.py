"""
Phase 10: Vector Databases — pgvector & In-Memory Vector Store
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: Vector databases store embeddings and enable efficient similarity
     search (nearest neighbor queries). Instead of SQL WHERE clauses, you query
     by "find the 10 vectors most similar to this query vector."
   - JS/TS Equivalent: No direct equivalent. In JS you might use Pinecone's
     REST API. In Python, you can use pgvector (PostgreSQL extension),
     Qdrant, ChromaDB, Weaviate, or Milvus. pgvector is popular because it
     runs inside your existing PostgreSQL — no new infrastructure.
   - Key concepts: ANN (Approximate Nearest Neighbor) search, HNSW index
     (graph-based, fast recall), IVFFlat index (cluster-based, less memory),
     metadata filtering (combine vector search with SQL-like filters).

2. UNDER THE HOOD (CPython & Memory):
   - Brute-force search: compute similarity against ALL vectors. O(N*D) where
     N = number of vectors, D = dimensions. Fine for <10K vectors.
   - HNSW (Hierarchical Navigable Small World): Builds a layered graph where
     each node connects to its nearest neighbors. Search traverses the graph
     from top layer down, narrowing candidates. O(log N) search time.
   - IVFFlat: Clusters vectors using k-means, then searches only the nearest
     clusters. Faster than brute-force but requires periodic re-clustering.
   - pgvector SQL: `SELECT * FROM items ORDER BY embedding <=> query_vec LIMIT 10`
     The `<=>` operator is cosine distance, `<->` is L2 distance.

3. COMMON GOTCHA:
   - Not creating an index: pgvector without an HNSW or IVFFlat index falls
     back to brute-force sequential scan. Fine for 1K vectors, catastrophic
     for 1M. Always create an index for production.
   - Metadata filtering AFTER vector search: If you filter after retrieving
     top-K, you might get fewer than K results. Pre-filter when possible,
     or over-fetch and then filter.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "How would you implement semantic search in a
     production system?"
   - How to Answer Out Loud (60-90 sec verbal script):
     * "I'd use pgvector as the vector store since we're already on Postgres.
       I'd add the vector extension, create a column with type `vector(1536)`,
       and build an HNSW index for fast approximate search."
     * "At ingestion: I chunk documents, embed each chunk with the embedding
       API, and store the vector alongside metadata (source, page, timestamp)."
     * "At query time: I embed the user query, run a vector similarity query
       with `ORDER BY embedding <=> query_vec LIMIT 10`, optionally adding
       WHERE clauses for metadata filtering."
     * "For hybrid search, I'd combine vector similarity with BM25 text
       search using Reciprocal Rank Fusion to get the best of both semantic
       and keyword matching."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
from dataclasses import dataclass, field
from typing import Any
import json
import time


# ══════════════════════════════════════════════════════════════════════
# IN-MEMORY VECTOR STORE — Teaches the vector DB interface pattern
# Production: Replace with pgvector, Qdrant, ChromaDB, etc.
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Document:
    """A document with its embedding and metadata."""
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A search result with score."""
    document: Document
    score: float  # cosine similarity


class InMemoryVectorStore:
    """
    In-memory vector store implementing the core vector DB interface.

    This mirrors the interface of production vector databases:
    - pgvector: SQL-based, runs inside PostgreSQL
    - Qdrant: gRPC/REST API, built in Rust, great for production
    - ChromaDB: Python-native, good for prototyping
    - Weaviate: GraphQL API, supports hybrid search

    REAL pgvector SQL equivalent:
        CREATE EXTENSION vector;
        CREATE TABLE documents (
            id UUID PRIMARY KEY,
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB DEFAULT '{}'
        );
        CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

        -- Insert
        INSERT INTO documents (id, content, embedding, metadata)
        VALUES ($1, $2, $3, $4);

        -- Search (cosine distance — lower is better, so we negate for similarity)
        SELECT id, content, metadata,
               1 - (embedding <=> $1) AS similarity
        FROM documents
        ORDER BY embedding <=> $1
        LIMIT 10;
    """

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._embeddings_matrix: np.ndarray | None = None
        self._id_list: list[str] = []
        self._dirty = True

    def upsert(self, doc: Document) -> None:
        """Insert or update a document."""
        self._documents[doc.id] = doc
        self._dirty = True

    def upsert_batch(self, docs: list[Document]) -> None:
        """Batch upsert for efficiency."""
        for doc in docs:
            self._documents[doc.id] = doc
        self._dirty = True

    def _rebuild_index(self) -> None:
        """Rebuild the embeddings matrix for fast batch similarity."""
        if not self._dirty or not self._documents:
            return
        self._id_list = list(self._documents.keys())
        self._embeddings_matrix = np.array(
            [self._documents[id_].embedding for id_ in self._id_list]
        )
        self._dirty = False

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Similarity search — find the K nearest documents.

        Args:
            query_embedding: The query vector.
            top_k: Number of results to return.
            metadata_filter: Optional {key: value} filter. All must match.
            score_threshold: Optional minimum similarity score.
        """
        self._rebuild_index()
        if self._embeddings_matrix is None or len(self._id_list) == 0:
            return []

        # Vectorized cosine similarity: matrix @ query
        # For normalized vectors, this gives cosine similarity directly
        similarities = self._embeddings_matrix @ query_embedding

        # Get sorted indices (descending similarity)
        sorted_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in sorted_indices:
            if len(results) >= top_k:
                break

            doc_id = self._id_list[idx]
            doc = self._documents[doc_id]
            score = float(similarities[idx])

            # Apply score threshold
            if score_threshold is not None and score < score_threshold:
                break  # Since sorted, all remaining will be lower

            # Apply metadata filter
            if metadata_filter:
                if not all(
                    doc.metadata.get(k) == v for k, v in metadata_filter.items()
                ):
                    continue

            results.append(SearchResult(document=doc, score=score))

        return results

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._dirty = True
            return True
        return False

    def count(self) -> int:
        return len(self._documents)


# ── Mock Embedding Model (from file 02) ──────────────────────────────

class SimpleEmbedder:
    """Simple deterministic embedder for demonstrations."""

    def __init__(self, dims: int = 64):
        self.dims = dims

    def embed(self, text: str) -> np.ndarray:
        np.random.seed(hash(text.lower().strip()) % (2**31))
        vec = np.random.randn(self.dims).astype(np.float32)
        # Topic-based nudging for semantic similarity
        lower = text.lower()
        if any(w in lower for w in ["python", "code", "programming", "developer"]):
            vec[:4] += np.array([2.0, 1.0, 0.5, 0.0], dtype=np.float32)
        if any(w in lower for w in ["machine", "learning", "ai", "model", "neural"]):
            vec[4:8] += np.array([2.0, 1.0, 0.5, 0.0], dtype=np.float32)
        if any(w in lower for w in ["database", "sql", "postgres", "query"]):
            vec[8:12] += np.array([2.0, 1.0, 0.5, 0.0], dtype=np.float32)
        if any(w in lower for w in ["food", "cooking", "recipe", "restaurant"]):
            vec[12:16] += np.array([2.0, 1.0, 0.5, 0.0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed(t) for t in texts]


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_vector_store_crud():
    """Basic CRUD operations on the vector store."""
    store = InMemoryVectorStore()
    embedder = SimpleEmbedder(dims=64)

    # Insert documents
    docs = [
        ("doc1", "Python is great for web development", {"category": "programming", "year": 2024}),
        ("doc2", "Machine learning models require training data", {"category": "ai", "year": 2024}),
        ("doc3", "SQL databases store structured data", {"category": "database", "year": 2023}),
        ("doc4", "Italian cooking uses olive oil and fresh herbs", {"category": "food", "year": 2023}),
        ("doc5", "Neural networks are inspired by the brain", {"category": "ai", "year": 2024}),
        ("doc6", "PostgreSQL supports JSON and vector columns", {"category": "database", "year": 2024}),
    ]

    for doc_id, text, meta in docs:
        store.upsert(Document(
            id=doc_id,
            text=text,
            embedding=embedder.embed(text),
            metadata=meta,
        ))

    print(f"  Inserted {store.count()} documents")

    # Search
    query = "How to build AI with Python?"
    query_emb = embedder.embed(query)
    results = store.search(query_emb, top_k=3)

    print(f"\n  Query: '{query}'")
    print(f"  Top 3 results:")
    for r in results:
        print(f"    {r.score:.4f} | [{r.document.id}] {r.document.text}")

    # Delete
    store.delete("doc4")
    print(f"\n  After delete: {store.count()} documents")

    return store


def demonstrate_metadata_filtering():
    """Combining vector search with metadata filters."""
    store = InMemoryVectorStore()
    embedder = SimpleEmbedder(dims=64)

    docs = [
        ("d1", "Python web framework Flask", {"category": "programming", "language": "python"}),
        ("d2", "JavaScript React frontend", {"category": "programming", "language": "javascript"}),
        ("d3", "Python machine learning scikit", {"category": "ai", "language": "python"}),
        ("d4", "TensorFlow deep learning models", {"category": "ai", "language": "python"}),
        ("d5", "Node.js Express API backend", {"category": "programming", "language": "javascript"}),
    ]

    store.upsert_batch([
        Document(id=id_, text=text, embedding=embedder.embed(text), metadata=meta)
        for id_, text, meta in docs
    ])

    query_emb = embedder.embed("Python programming")

    # Without filter
    all_results = store.search(query_emb, top_k=5)
    print("  All results (no filter):")
    for r in all_results:
        print(f"    {r.score:.4f} | {r.document.metadata} | {r.document.text}")

    # With metadata filter — only Python documents
    python_results = store.search(
        query_emb, top_k=5,
        metadata_filter={"language": "python"},
    )
    print("\n  Filtered (language=python):")
    for r in python_results:
        print(f"    {r.score:.4f} | {r.document.metadata} | {r.document.text}")

    # With score threshold
    high_sim = store.search(query_emb, top_k=5, score_threshold=0.5)
    print(f"\n  High similarity only (>0.5): {len(high_sim)} results")

    return python_results


def demonstrate_pgvector_sql():
    """Show the actual pgvector SQL patterns (conceptual, not executed)."""
    print("  === pgvector SQL Patterns ===")
    print()

    sql_examples = {
        "Create Extension": "CREATE EXTENSION IF NOT EXISTS vector;",

        "Create Table": """
    CREATE TABLE documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content TEXT NOT NULL,
        embedding vector(1536),
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT now()
    );""",

        "Create HNSW Index": """
    -- HNSW: Fast, high recall, more memory
    -- m=16: max connections per node (higher = better recall, more RAM)
    -- ef_construction=64: build-time quality (higher = better, slower build)
    CREATE INDEX idx_docs_embedding ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);""",

        "Create IVFFlat Index": """
    -- IVFFlat: Less memory, requires training step
    -- lists: number of clusters (sqrt(N) is a good starting point)
    CREATE INDEX idx_docs_embedding_ivf ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);""",

        "Insert": """
    INSERT INTO documents (content, embedding, metadata)
    VALUES ($1, $2::vector, $3::jsonb);""",

        "Cosine Search": """
    -- <=> is cosine distance (1 - similarity), so lower = better
    SELECT id, content, metadata,
           1 - (embedding <=> $1::vector) AS similarity
    FROM documents
    WHERE metadata->>'category' = 'programming'
    ORDER BY embedding <=> $1::vector
    LIMIT 10;""",

        "L2 Search": """
    -- <-> is L2 (Euclidean) distance
    SELECT id, content, 1 / (1 + (embedding <-> $1::vector)) AS similarity
    FROM documents
    ORDER BY embedding <-> $1::vector
    LIMIT 10;""",

        "Hybrid Search (BM25 + Vector)": """
    -- Combine keyword search (ts_rank) with vector search
    -- Uses Reciprocal Rank Fusion (RRF)
    WITH keyword_results AS (
        SELECT id, ts_rank(to_tsvector(content), plainto_tsquery($2)) AS keyword_rank
        FROM documents
        WHERE to_tsvector(content) @@ plainto_tsquery($2)
    ),
    vector_results AS (
        SELECT id, 1 - (embedding <=> $1::vector) AS vector_score
        FROM documents
        ORDER BY embedding <=> $1::vector
        LIMIT 20
    )
    SELECT COALESCE(k.id, v.id) AS id,
           COALESCE(1.0 / (60 + kr.rn), 0) + COALESCE(1.0 / (60 + vr.rn), 0) AS rrf_score
    FROM ...  -- RRF combines both rankings
    ORDER BY rrf_score DESC
    LIMIT 10;""",
    }

    for name, sql in sql_examples.items():
        print(f"  [{name}]")
        for line in sql.strip().split("\n"):
            print(f"    {line}")
        print()


def demonstrate_index_comparison():
    """Compare vector index strategies."""
    print("  === Vector Index Comparison ===")
    print()
    print(f"  {'Index':<12} {'Search':<10} {'Build':<10} {'Memory':<10} {'Recall':<10} {'Best For'}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*20}")
    print(f"  {'Flat/Brute':<12} {'O(N*D)':<10} {'O(1)':<10} {'Low':<10} {'100%':<10} {'<10K vectors'}")
    print(f"  {'IVFFlat':<12} {'O(N/L*D)':<10} {'O(N*D)':<10} {'Medium':<10} {'~95%':<10} {'Cost-sensitive'}")
    print(f"  {'HNSW':<12} {'O(logN*D)':<10} {'O(N*logN)':<10} {'High':<10} {'~99%':<10} {'Production default'}")
    print()
    print("  HNSW parameters:")
    print("    m (max connections): 16 default, higher = better recall, more RAM")
    print("    ef_construction: 64 default, higher = better quality, slower build")
    print("    ef_search: 40 default, higher = better recall, slower query")
    print()
    print("  Rule of thumb: Start with HNSW for everything. Only use IVFFlat")
    print("  if memory is a hard constraint. Never go flat in production.")


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    embedder = SimpleEmbedder(dims=64)

    # Test 1: Vector store insert and count
    store = InMemoryVectorStore()
    doc = Document(id="t1", text="test", embedding=embedder.embed("test"), metadata={})
    store.upsert(doc)
    assert store.count() == 1, "Store should have 1 document"

    # Test 2: Batch upsert
    docs = [
        Document(id=f"t{i}", text=f"text {i}", embedding=embedder.embed(f"text {i}"))
        for i in range(2, 6)
    ]
    store.upsert_batch(docs)
    assert store.count() == 5, "Store should have 5 documents"

    # Test 3: Search returns results
    query_emb = embedder.embed("test query")
    results = store.search(query_emb, top_k=3)
    assert len(results) <= 3, "Should return at most top_k results"
    assert len(results) > 0, "Should return at least 1 result"

    # Test 4: Results are sorted by score (descending)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True), "Results should be sorted desc"

    # Test 5: Search result structure
    assert hasattr(results[0], 'document'), "Result should have document"
    assert hasattr(results[0], 'score'), "Result should have score"
    assert isinstance(results[0].document, Document), "Should be a Document"

    # Test 6: Delete
    assert store.delete("t1"), "Delete should return True for existing doc"
    assert store.count() == 4, "Count should decrease after delete"
    assert not store.delete("nonexistent"), "Delete should return False for missing doc"

    # Test 7: Metadata filtering
    store2 = InMemoryVectorStore()
    store2.upsert(Document("a", "python code", embedder.embed("python code"), {"lang": "python"}))
    store2.upsert(Document("b", "js code", embedder.embed("js code"), {"lang": "javascript"}))
    store2.upsert(Document("c", "more python", embedder.embed("more python"), {"lang": "python"}))

    py_results = store2.search(
        embedder.embed("programming"),
        top_k=10,
        metadata_filter={"lang": "python"},
    )
    assert all(r.document.metadata["lang"] == "python" for r in py_results),         "All filtered results should be Python"

    # Test 8: Score threshold
    high_results = store2.search(
        embedder.embed("python code"),
        top_k=10,
        score_threshold=0.99,  # Very high threshold
    )
    assert all(r.score >= 0.99 for r in high_results), "All should be above threshold"

    # Test 9: Upsert updates existing document
    store3 = InMemoryVectorStore()
    store3.upsert(Document("x", "old text", embedder.embed("old text")))
    store3.upsert(Document("x", "new text", embedder.embed("new text")))
    assert store3.count() == 1, "Upsert should update, not duplicate"

    # Test 10: Empty store search returns empty
    empty_store = InMemoryVectorStore()
    empty_results = empty_store.search(embedder.embed("query"))
    assert empty_results == [], "Empty store should return empty results"

    print("[SUCCESS] All 10 Vector Database self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10: Vector Databases & pgvector")
    print("=" * 70)
    print("\n--- Vector Store CRUD ---")
    demonstrate_vector_store_crud()
    print("\n--- Metadata Filtering ---")
    demonstrate_metadata_filtering()
    print("\n--- pgvector SQL Patterns ---")
    demonstrate_pgvector_sql()
    print("\n--- Index Comparison ---")
    demonstrate_index_comparison()
    print("-" * 70)
    run_tests()
    print("=" * 70)
