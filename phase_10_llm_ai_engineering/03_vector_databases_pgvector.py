r"""
03_vector_databases_pgvector.py

============================================================
1. CONCEPT
============================================================

As vector datasets scale beyond 100,000 embeddings, exact brute-force k-Nearest Neighbor
(k-NN) with $O(N \cdot D)$ complexity becomes computationally prohibitive. Vector databases
and PostgreSQL's `pgvector` extension provide Approximate Nearest Neighbor (ANN) search,
trading $< 1-2\%$ recall for sub-10ms logarithmic $O(\log N)$ retrieval:

1. PostgreSQL `pgvector` Architecture:
   - Native `vector(D)` data type embedded directly into relational PostgreSQL tables.
   - Unifies ACID transactional relational data (users, permissions, timestamps, foreign keys)
     with vector embeddings in a single database, eliminating complex ETL synchronization.
   - Distance Operators:
     * `<->`: Euclidean / L2 Distance ($\|u - v\|_2$).
     * `<#>`: Negative Inner Product (used for maximum inner product search).
     * `<=>`: Cosine Distance ($1 - \cos(u, v)$).

2. Production Indexing Strategies (HNSW vs IVFFlat):
   - HNSW (Hierarchical Navigable Small World):
     * Constructs a multi-layer graph where upper layers contain sparse long-range highway edges
       and lower layers contain dense local connections.
     * Hyperparameters:
       - `m`: Maximum number of bidirectional connections per element per layer (e.g. 16 to 64).
       - `ef_construction`: Size of dynamic candidate list during graph building (e.g. 64 to 200).
       - `ef_search`: Candidate list size during queries (higher `ef_search` = higher recall at cost of latency).
     * Pros: Highest recall ($> 98\%$), exceptional query latency ($< 5\text{ms}$), dynamic updates.
     * Cons: High RAM usage and longer index build times.
   - IVFFlat (Inverted File Flat):
     * Partitions the vector space into $K$ Voronoi cells using k-means clustering.
     * Hyperparameters:
       - `lists`: Number of cluster centroids (typically $\sqrt{N}$ or $N / 1000$).
       - `probes`: Number of neighboring centroids inspected during query (e.g. 1 to 10).
     * Pros: Minimal RAM overhead, fast build times.
     * Cons: Lower recall on edge cases; requires re-indexing when data distribution shifts.

3. Hybrid Search & Reciprocal Rank Fusion (RRF):
   - Dense vector search excels at conceptual semantic similarity, but struggles with exact
     keyword matching (part numbers, specific product codes, exact names).
   - Hybrid Search combines dense vector retrieval with sparse PostgreSQL full-text search (`tsvector` / BM25).
   - Reciprocal Rank Fusion (RRF) merges disparate ranking lists without score calibration:
     $$\text{RRF}(d) = \sum_{m \in M} \frac{1}{k + \text{rank}_m(d)}$$
     where $k$ is a constant (typically 60) and $\text{rank}_m(d)$ is the 1-based rank in method $m$.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (pgvector / SQLAlchemy)     | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Vector Storage               | Native PostgreSQL `vector(1536)`   | Standalone Pinecone / Weaviate DB  |
| Distance Queries             | SQL `ORDER BY embedding <=> :query`| SDK client `.query({ vector })`    |
| Metadata Pre-Filtering       | Native SQL `WHERE tenant_id = 5`   | Proprietary metadata filter DSL    |
| Index Types                  | HNSW / IVFFlat via DDL             | Cloud-managed proprietary indexes  |
| Hybrid Search                | SQL combining vector + `tsvector`  | Dual API queries + manual fusion   |
| Transactions                 | ACID transactions with rollback    | Eventual consistency / 2-phase API |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In the JavaScript/TypeScript ecosystem, developers frequently adopt SaaS vector databases
   (Pinecone, Qdrant Cloud) due to easy HTTP SDKs, which introduces dual-database syncing challenges
   and eventual consistency issues.
2. In Python backend architectures, `pgvector` allows keeping vectors inside the primary PostgreSQL
   database. A single atomic SQL query can enforce tenant isolation (`tenant_id = :tid`), apply
   business filters (`is_archived = false`), and execute HNSW vector similarity search in a single pass.


============================================================
3. UNDER THE HOOD (HNSW Graph Traversal & Voronoi Cells)
============================================================

1. HNSW Multi-Layer Skip-List Graph Mechanics:
   - Inspired by Skip Lists, HNSW builds layers $L_{\max}$ down to $L_0$.
   - Search begins at entry point in the highest layer $L_{\max}$.
   - The query performs greedy search: moving to neighboring nodes that are closer to the query
     until a local minimum is reached.
   - It drops down to the next lower layer and repeats greedy search, narrowing down the neighborhood
     until reaching layer $L_0$, where it executes detailed local exploration with candidate list size `ef_search`.
   - Result: $O(\log N)$ logarithmic search complexity instead of $O(N)$ linear scans.

2. IVFFlat Centroid Inverted Lists:
   - IVFFlat uses k-means to compute $C$ cluster centroids across the vector space.
   - Every vector in the table is assigned to its closest centroid's inverted posting list.
   - At query time: the query vector finds the closest `probes` centroids and scans ONLY the
     vectors stored in those specific inverted lists, skipping $> 95\%$ of the table rows.


============================================================
4. COMMON GOTCHAS
============================================================

1. Building IVFFlat on an Empty Table:
   - IVFFlat trains k-means centroids during `CREATE INDEX`. If executed on an empty table or
     before data is loaded, all centroids collapse to the origin, permanently degrading recall!
   - FIX: Always load initial production data BEFORE building an IVFFlat index, or use HNSW
     which builds incrementally as rows are inserted.

2. Forgetting `SET hnsw.ef_search`:
   - The default `hnsw.ef_search` parameter in pgvector defaults to 40. For complex high-dimensional
     queries, this may result in $< 90\%$ recall.
   - FIX: Tune `SET hnsw.ef_search = 100` in the database session for critical retrieval endpoints.

3. Neglecting Relational Partitioning / Pre-filtering:
   - In multi-tenant SaaS applications, running HNSW across all tenants and filtering `WHERE tenant_id = X`
     afterwards can cause index scan aborts if the tenant has few rows.
   - FIX: Partition tables by `tenant_id` or use composite indexes/iterative index scans.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Compare HNSW and IVFFlat indexes in pgvector. When would you choose each for an AI application?"
A1: "HNSW builds a hierarchical navigable small-world graph. It delivers superior query latency (sub-5ms)
     and excellent recall (typically $> 98\%$), and it supports incremental real-time inserts without
     degradation. However, it consumes significant RAM because it must store graph edge lists in memory,
     and index build times are longer.
     IVFFlat clusters the vector space into Voronoi cells using k-means. It uses a fraction of the RAM
     and builds rapidly, but it has lower recall on boundaries and requires periodic re-indexing as
     data distribution changes. Furthermore, creating an IVFFlat index on an empty table produces useless
     centroids.
     In production, I default to HNSW for mission-critical RAG and semantic search where high recall and
     low latency are paramount, reserving IVFFlat for memory-constrained environments or append-only
     batch datasets."

Q2: "What is Hybrid Search, and how does Reciprocal Rank Fusion (RRF) work in PostgreSQL?"
A2: "Hybrid Search combines dense vector similarity search with sparse keyword search (BM25 or PostgreSQL
     `tsvector`). Dense vectors capture semantic conceptual meaning and synonyms, but fail on exact alphanumeric
     tokens like model SKUs or error codes. Sparse keyword search captures exact tokens perfectly.
     To combine their results without normalizing mismatched score distributions (cosine distance vs BM25 rank),
     we use Reciprocal Rank Fusion. RRF assigns a score based purely on reciprocal rank positions:
     $\text{score}(d) = \sum 1 / (60 + \text{rank}(d))$. Documents that rank highly across both semantic
     and keyword passes rise to the top, providing robust search quality across all query types."

Q3: "Why choose `pgvector` inside PostgreSQL over a dedicated vector database like Pinecone or Milvus?"
A3: "Choosing `pgvector` keeps vectors co-located with primary application data inside PostgreSQL.
     This provides three massive engineering advantages:
     First, ACID Consistency: Inserting a document and its embedding happens in a single atomic transaction;
     there is no eventual consistency lag or dual-write failure where relational DB succeeds but vector DB fails.
     Second, Unified Querying: We can filter on complex relational permissions, tenant IDs, foreign keys,
     and timestamps in the same SQL query with query planner optimization.
     Third, Operational Simplicity: We reuse existing PostgreSQL backup, replica, monitoring, and compliance
     infrastructure without operating and paying for an additional distributed database cluster."
"""

import sys
import math
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
# 1. SQL SCHEMA SPECIFICATION FOR PGVECTOR
# ==============================================================================

PGVECTOR_SQL_SCHEMA = """-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Document chunks table with embeddings and relational metadata
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INT NOT NULL,
    document_id UUID NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    tsv_content tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1. HNSW Index for ultra-fast semantic similarity search (Cosine Distance)
CREATE INDEX idx_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 2. GIN Index for sparse keyword Full-Text Search (BM25)
CREATE INDEX idx_chunks_tsv ON document_chunks USING gin (tsv_content);

-- 3. Composite B-Tree for relational tenant isolation
CREATE INDEX idx_chunks_tenant_doc ON document_chunks (tenant_id, document_id);
"""


# ==============================================================================
# 2. IVFFLAT CLUSTERING & VORONOI PARTITIONING SIMULATOR
# ==============================================================================

class IVFFlatSimulator:
    """
    Simulates IVFFlat indexing mechanics:
    - Trains K centroid clusters via k-means.
    - Partitions documents into inverted lists (Voronoi cells).
    - Executes query search across configurable 'probes' centroids.
    """

    def __init__(self, n_lists: int = 4):
        self.n_lists = n_lists
        self.centroids: Optional[np.ndarray] = None  # Shape: (K, D)
        self.inverted_lists: Dict[int, List[Tuple[str, np.ndarray]]] = {}

    def fit_and_populate(self, doc_ids: List[str], vectors: np.ndarray) -> None:
        """Clusters vectors into centroids and populates inverted lists."""
        n_samples, dim = vectors.shape
        assert n_samples >= self.n_lists, "Must have more samples than cluster lists"

        # Initialize centroids spaced across the dataset for deterministic simulation
        step = max(1, n_samples // self.n_lists)
        self.centroids = vectors[::step][:self.n_lists].copy()
        self.inverted_lists = {i: [] for i in range(self.n_lists)}

        # Assign each vector to closest centroid (Voronoi cell)
        for doc_id, vec in zip(doc_ids, vectors):
            # Compute distance to all centroids
            dists = np.linalg.norm(self.centroids - vec, axis=1)
            closest_cluster = int(np.argmin(dists))
            self.inverted_lists[closest_cluster].append((doc_id, vec))

    def search(self, query: np.ndarray, probes: int = 1, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Searches nearest centroids up to 'probes' depth, scanning only
        vectors within those inverted lists.
        """
        assert self.centroids is not None, "Index must be trained before search"
        probes = min(probes, self.n_lists)

        # 1. Find nearest centroids to query
        centroid_dists = np.linalg.norm(self.centroids - query, axis=1)
        probed_clusters = np.argsort(centroid_dists)[:probes]

        # 2. Scan vectors only in probed inverted lists
        candidates: List[Tuple[str, float]] = []
        for cluster_idx in probed_clusters:
            for doc_id, vec in self.inverted_lists[cluster_idx]:
                dist = float(np.linalg.norm(vec - query))
                candidates.append((doc_id, dist))

        # 3. Sort candidates and return top K
        candidates.sort(key=lambda x: x[1])
        return candidates[:top_k]


# ==============================================================================
# 3. RECIPROCAL RANK FUSION (HYBRID SEARCH ENGINE)
# ==============================================================================

class ReciprocalRankFusion:
    """
    Implements standard Reciprocal Rank Fusion (RRF) to merge
    dense vector rankings with sparse keyword BM25 rankings.
    """

    @staticmethod
    def fuse_rankings(
        vector_ranked_ids: List[str],
        keyword_ranked_ids: List[str],
        k: int = 60
    ) -> List[Tuple[str, float]]:
        """
        Calculates RRF score: sum(1 / (k + rank)) across both ranked result lists.
        """
        scores: Dict[str, float] = {}

        # Process vector ranks (1-based index)
        for rank_idx, doc_id in enumerate(vector_ranked_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank_idx))

        # Process keyword ranks (1-based index)
        for rank_idx, doc_id in enumerate(keyword_ranked_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank_idx))

        # Sort descending by fused RRF score
        fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return fused


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 03_vector_databases_pgvector.py...")

    # ------------------------------------------------------------
    # Test 1: pgvector SQL Schema Syntax Validation
    # ------------------------------------------------------------
    print("  -> Validating PostgreSQL pgvector DDL and index specifications...")
    assert "CREATE EXTENSION IF NOT EXISTS vector;" in PGVECTOR_SQL_SCHEMA
    assert "vector(1536)" in PGVECTOR_SQL_SCHEMA
    assert "USING hnsw (embedding vector_cosine_ops)" in PGVECTOR_SQL_SCHEMA
    assert "WITH (m = 16, ef_construction = 64)" in PGVECTOR_SQL_SCHEMA
    assert "USING gin (tsv_content)" in PGVECTOR_SQL_SCHEMA

    # ------------------------------------------------------------
    # Test 2: IVFFlat Centroid Partitioning & Probing Tradeoff
    # ------------------------------------------------------------
    print("  -> Testing IVFFlat inverted file partitioning and probes scaling...")
    ivf = IVFFlatSimulator(n_lists=3)

    # 6 vectors in 2D space:
    # Cluster 0: near (0, 0)
    # Cluster 1: near (10, 10)
    # Cluster 2: near (50, 50)
    doc_ids = ["doc_0a", "doc_0b", "doc_1a", "doc_1b", "doc_2a", "doc_2b"]
    vectors = np.array([
        [0.0, 0.1], [0.1, 0.0],
        [10.0, 10.1], [10.2, 9.9],
        [50.0, 50.1], [50.1, 49.9]
    ])

    ivf.fit_and_populate(doc_ids, vectors)

    # Query near Cluster 0
    query_near_0 = np.array([0.05, 0.05])

    # Probe 1: searches only nearest cluster (Cluster 0)
    res_p1 = ivf.search(query_near_0, probes=1, top_k=2)
    assert len(res_p1) == 2
    assert {res_p1[0][0], res_p1[1][0]} == {"doc_0a", "doc_0b"}

    # Probe 3: searches all clusters
    res_p3 = ivf.search(query_near_0, probes=3, top_k=6)
    assert len(res_p3) == 6
    assert res_p3[0][0] in ["doc_0a", "doc_0b"]  # Nearest must be first

    # ------------------------------------------------------------
    # Test 3: Reciprocal Rank Fusion (Hybrid Search Alignment)
    # ------------------------------------------------------------
    print("  -> Testing Reciprocal Rank Fusion (RRF) rank aggregation...")
    # Dense vector ranking (semantic understanding)
    vector_results = ["doc_A", "doc_B", "doc_C", "doc_D"]
    # Keyword ranking (exact keyword match)
    keyword_results = ["doc_E", "doc_A", "doc_F", "doc_B"]

    # Fusing rankings: doc_A is #1 in vector and #2 in keyword -> MUST BE #1 OVERALL
    fused_results = ReciprocalRankFusion.fuse_rankings(
        vector_results, keyword_results, k=60
    )

    top_doc_id, top_score = fused_results[0]
    assert top_doc_id == "doc_A", f"Expected doc_A at top of fused ranks, got {top_doc_id}"

    # Calculate expected mathematical RRF score for doc_A:
    # 1 / (60 + 1) [from vector] + 1 / (60 + 2) [from keyword]
    expected_score_a = (1.0 / 61.0) + (1.0 / 62.0)
    assert np.isclose(top_score, expected_score_a)

    # Verify doc_B ranks highly as well (present in both lists)
    doc_b_rank = [item[0] for item in fused_results].index("doc_B")
    assert doc_b_rank in [1, 2]

    print("[SUCCESS] All 3 pgvector, IVFFlat & RRF Hybrid Search tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10 - 03: Vector Databases, pgvector & HNSW/IVFFlat Indexing")
    print("=" * 70)
    run_tests()
    print("=" * 70)
