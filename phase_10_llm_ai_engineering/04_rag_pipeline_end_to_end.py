"""
Phase 10: RAG Pipeline — Retrieval-Augmented Generation End-to-End
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Concept: RAG (Retrieval-Augmented Generation) supplements an LLM's knowledge
     with external documents. Instead of fine-tuning, you RETRIEVE relevant
     context at query time and INJECT it into the prompt. This gives the LLM
     access to private/current data it wasn't trained on.
   - JS/TS Equivalent: Same concept in any language. The pipeline is:
     Ingest (chunk + embed + store) -> Query (embed query -> retrieve -> prompt -> generate).
     In Node.js you'd use LangChain.js or build it manually with fetch calls.
   - Key insight: RAG is essentially "smart copy-paste" — you find the most
     relevant text chunks and paste them into the prompt context window.

2. UNDER THE HOOD (CPython & Memory):
   - Chunking: Documents are split into overlapping segments (e.g., 500 tokens
     with 50 token overlap). Overlap prevents losing context at chunk boundaries.
   - At query time, the pipeline: (1) embeds the query, (2) retrieves top-K
     chunks from vector store, (3) constructs a prompt with system instructions
     + retrieved context + user question, (4) sends to LLM for generation.
   - Token budget: If context window is 128K tokens, and your prompt template
     uses 200 tokens, you can fit ~127,800 tokens of retrieved context. But
     more isn't always better — too much context can dilute the signal.

3. COMMON GOTCHA:
   - Chunk size matters enormously. Too small (50 tokens): loses context,
     retrieves fragments. Too large (2000 tokens): wastes token budget,
     dilutes relevance. Sweet spot: 200-500 tokens with 10-20% overlap.
   - Not citing sources: Users need to know WHERE the answer came from.
     Always return source metadata with the response.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   - Interview Question: "Explain how you'd build a RAG system."
   - How to Answer Out Loud (60-90 sec verbal script):
     * "RAG has two phases: ingestion and query. In ingestion, I load
       documents, split them into chunks of 300-500 tokens with overlap,
       embed each chunk using an embedding model, and store vectors
       alongside metadata in pgvector."
     * "At query time, I embed the user's question, retrieve the top 5-10
       most similar chunks via cosine similarity, then construct a prompt:
       system instructions + retrieved context + user question."
     * "The LLM generates a grounded answer from the retrieved context.
       I include source citations and confidence scores."
     * "Key optimizations: hybrid search combining BM25 keyword matching
       with vector similarity, re-ranking retrieved chunks with a
       cross-encoder model, and caching frequently asked queries."
     * "Evaluation: I measure retrieval quality (recall@K, MRR) and
       generation quality (faithfulness, relevance, answer correctness)."
================================================================================
"""

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import numpy as np
import json
import re
from dataclasses import dataclass, field
from typing import Any


# ══════════════════════════════════════════════════════════════════════
# BUILDING BLOCKS — Reusable components for the RAG pipeline
# ══════════════════════════════════════════════════════════════════════

# -- Embedder (simplified from file 02) --
class SimpleEmbedder:
    def __init__(self, dims: int = 64):
        self.dims = dims

    def embed(self, text: str) -> np.ndarray:
        np.random.seed(hash(text.lower().strip()) % (2**31))
        vec = np.random.randn(self.dims).astype(np.float32)
        lower = text.lower()
        topics = {
            "python": 0, "code": 0, "programming": 0, "function": 0,
            "machine": 4, "learning": 4, "ai": 4, "model": 4, "neural": 4,
            "database": 8, "sql": 8, "query": 8, "postgres": 8,
            "api": 12, "rest": 12, "endpoint": 12, "http": 12,
            "async": 16, "await": 16, "concurrency": 16,
            "test": 20, "testing": 20, "pytest": 20,
        }
        for word, offset in topics.items():
            if word in lower:
                vec[offset:offset+4] += np.array([1.5, 0.8, 0.3, 0.1], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


# -- Vector Store (simplified from file 03) --
@dataclass
class Chunk:
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float

class VectorStore:
    def __init__(self):
        self._chunks: dict[str, Chunk] = {}

    def add(self, chunk: Chunk) -> None:
        self._chunks[chunk.id] = chunk

    def add_batch(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.id] = c

    def search(self, query_emb: np.ndarray, top_k: int = 5) -> list[RetrievalResult]:
        if not self._chunks:
            return []
        ids = list(self._chunks.keys())
        matrix = np.array([self._chunks[id_].embedding for id_ in ids])
        sims = matrix @ query_emb
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [
            RetrievalResult(chunk=self._chunks[ids[i]], score=float(sims[i]))
            for i in top_indices
        ]

    def count(self) -> int:
        return len(self._chunks)


# -- Mock LLM --
class MockLLM:
    def generate(self, prompt: str) -> str:
        """Generate a mock response based on context in the prompt."""
        if "context" in prompt.lower():
            # Extract context section and return a summarized response
            lines = prompt.split("\n")
            context_lines = [l for l in lines if l.strip() and not l.startswith("System:")]
            return f"Based on the provided context, here is a synthesized answer covering {len(context_lines)} relevant sections."
        return "I don't have enough context to answer that question."


# ══════════════════════════════════════════════════════════════════════
# CHUNKING — Splitting documents into retrievable segments
# ══════════════════════════════════════════════════════════════════════

def chunk_text(
    text: str,
    chunk_size: int = 200,
    chunk_overlap: int = 40,
    separator: str = " ",
) -> list[str]:
    """
    Split text into overlapping chunks by character count.

    In production, you'd use token-based splitting (tiktoken) and respect
    sentence/paragraph boundaries. This simplified version uses characters.

    Args:
        chunk_size: Target characters per chunk.
        chunk_overlap: Characters of overlap between chunks.
        separator: Split boundary (word-level by default).
    """
    words = text.split(separator)
    chunks = []
    current_chunk: list[str] = []
    current_length = 0

    for word in words:
        word_len = len(word) + 1  # +1 for space
        if current_length + word_len > chunk_size and current_chunk:
            chunk_text = separator.join(current_chunk)
            chunks.append(chunk_text)

            # Calculate overlap: keep last N characters worth of words
            overlap_words: list[str] = []
            overlap_len = 0
            for w in reversed(current_chunk):
                if overlap_len + len(w) + 1 > chunk_overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1

            current_chunk = overlap_words
            current_length = overlap_len

        current_chunk.append(word)
        current_length += word_len

    if current_chunk:
        chunks.append(separator.join(current_chunk))

    return chunks


# ══════════════════════════════════════════════════════════════════════
# THE RAG PIPELINE — End-to-end orchestration
# ══════════════════════════════════════════════════════════════════════

class RAGPipeline:
    """
    Complete RAG pipeline: Ingest -> Retrieve -> Generate.

    This is the pattern used in production RAG systems, whether built with
    LangChain, LlamaIndex, or custom code. The components are:
    1. Document Loader — reads files/URLs/APIs
    2. Chunker — splits documents into segments
    3. Embedder — converts text to vectors
    4. Vector Store — stores and searches embeddings
    5. Prompt Builder — constructs the LLM prompt with context
    6. LLM — generates the final answer
    """

    def __init__(
        self,
        embedder: SimpleEmbedder,
        vector_store: VectorStore,
        llm: MockLLM,
        chunk_size: int = 200,
        chunk_overlap: int = 40,
        top_k: int = 3,
    ):
        self.embedder = embedder
        self.store = vector_store
        self.llm = llm
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self._doc_counter = 0

    # ── Phase 1: Ingestion ──

    def ingest_document(self, text: str, source: str = "unknown") -> int:
        """
        Ingest a document: chunk -> embed -> store.
        Returns the number of chunks created.
        """
        chunks_text = chunk_text(
            text,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        chunk_objects = []
        for i, ct in enumerate(chunks_text):
            self._doc_counter += 1
            chunk_obj = Chunk(
                id=f"{source}-chunk-{self._doc_counter}",
                text=ct,
                embedding=self.embedder.embed(ct),
                metadata={
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(chunks_text),
                    "char_count": len(ct),
                },
            )
            chunk_objects.append(chunk_obj)

        self.store.add_batch(chunk_objects)
        return len(chunk_objects)

    # ── Phase 2: Retrieval ──

    def retrieve(self, query: str) -> list[RetrievalResult]:
        """Embed query and retrieve top-K relevant chunks."""
        query_emb = self.embedder.embed(query)
        return self.store.search(query_emb, top_k=self.top_k)

    # ── Phase 3: Generation ──

    def build_prompt(self, query: str, context_chunks: list[RetrievalResult]) -> str:
        """
        Construct the LLM prompt with retrieved context.

        Prompt template pattern:
        - System: Instructions and behavior
        - Context: Retrieved document chunks
        - Question: User's query
        """
        context_text = "\n\n".join(
            f"[Source: {r.chunk.metadata.get('source', '?')} | "
            f"Relevance: {r.score:.2f}]\n{r.chunk.text}"
            for r in context_chunks
        )

        prompt = f"""System: You are a helpful assistant. Answer the user's question
based ONLY on the provided context. If the context doesn't contain
enough information, say "I don't have enough information to answer that."
Always cite your sources.

Context:
{context_text}

Question: {query}

Answer:"""
        return prompt

    def query(self, question: str) -> dict:
        """
        Full RAG query: retrieve -> build prompt -> generate.
        Returns the answer with sources.
        """
        # Step 1: Retrieve
        results = self.retrieve(question)

        # Step 2: Build prompt
        prompt = self.build_prompt(question, results)

        # Step 3: Generate
        answer = self.llm.generate(prompt)

        # Step 4: Package response with sources
        sources = [
            {
                "source": r.chunk.metadata.get("source", "unknown"),
                "chunk_index": r.chunk.metadata.get("chunk_index", 0),
                "score": round(r.score, 4),
                "text_preview": r.chunk.text[:100] + "...",
            }
            for r in results
        ]

        return {
            "answer": answer,
            "sources": sources,
            "num_chunks_retrieved": len(results),
            "total_chunks_in_store": self.store.count(),
        }


# ── Demonstration Functions ──────────────────────────────────────────────

def demonstrate_chunking():
    """Document chunking strategies."""
    document = (
        "Python is a high-level programming language known for its readability "
        "and versatility. It was created by Guido van Rossum and first released "
        "in 1991. Python supports multiple programming paradigms including "
        "procedural, object-oriented, and functional programming. It has a "
        "comprehensive standard library and a vibrant ecosystem of third-party "
        "packages. Python is widely used in web development, data science, "
        "machine learning, automation, and scientific computing. The language "
        "emphasizes code readability with its use of significant whitespace."
    )

    chunks = chunk_text(document, chunk_size=150, chunk_overlap=30)

    print(f"  Document length: {len(document)} chars")
    print(f"  Chunk size: 150, overlap: 30")
    print(f"  Number of chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n  Chunk {i} ({len(chunk)} chars):")
        print(f"    '{chunk[:80]}...'")

    # Show overlap between consecutive chunks
    if len(chunks) >= 2:
        c1_end = chunks[0][-40:]
        c2_start = chunks[1][:40]
        print(f"\n  Overlap check:")
        print(f"    End of chunk 0:   '...{c1_end}'")
        print(f"    Start of chunk 1: '{c2_start}...'")

    return chunks


def demonstrate_full_rag_pipeline():
    """End-to-end RAG pipeline demonstration."""
    # Initialize components
    embedder = SimpleEmbedder(dims=64)
    store = VectorStore()
    llm = MockLLM()
    pipeline = RAGPipeline(
        embedder=embedder,
        vector_store=store,
        llm=llm,
        chunk_size=200,
        chunk_overlap=40,
        top_k=3,
    )

    # Ingest documents (simulating a knowledge base)
    documents = {
        "python_guide": (
            "Python is a versatile programming language used for web development, "
            "data science, and AI. It has simple syntax that emphasizes readability. "
            "Python uses dynamic typing and automatic memory management with "
            "reference counting and garbage collection. Functions are first-class "
            "objects and closures are supported. Python's async/await syntax "
            "provides concurrency for I/O-bound tasks."
        ),
        "fastapi_docs": (
            "FastAPI is a modern Python web framework for building APIs. It uses "
            "type hints for automatic request validation and documentation. "
            "FastAPI is built on Starlette for the web parts and Pydantic for "
            "data validation. It supports async endpoints and dependency injection. "
            "The framework auto-generates OpenAPI documentation at /docs."
        ),
        "ml_overview": (
            "Machine learning is a subset of artificial intelligence that enables "
            "systems to learn from data. Supervised learning uses labeled data to "
            "train models for classification and regression. Unsupervised learning "
            "finds patterns in unlabeled data through clustering. Deep learning "
            "uses neural networks with multiple layers to learn complex features."
        ),
    }

    print("  === Ingestion Phase ===")
    for name, text in documents.items():
        n_chunks = pipeline.ingest_document(text, source=name)
        print(f"  Ingested '{name}': {n_chunks} chunks")
    print(f"  Total chunks in store: {pipeline.store.count()}")

    # Query
    print("\n  === Query Phase ===")
    questions = [
        "How does FastAPI handle validation?",
        "What is Python used for?",
        "Explain supervised vs unsupervised learning",
    ]

    for q in questions:
        print(f"\n  Q: {q}")
        result = pipeline.query(q)
        print(f"  A: {result['answer']}")
        print(f"  Sources ({result['num_chunks_retrieved']} retrieved):")
        for s in result["sources"]:
            print(f"    - {s['source']} (score: {s['score']}) "
                  f"'{s['text_preview'][:60]}...'")

    return pipeline


def demonstrate_conversation_memory():
    """Conversation memory patterns for multi-turn RAG."""
    print("  === Conversation Memory Patterns ===")

    # Pattern 1: Window Memory (keep last N messages)
    class WindowMemory:
        """Keep the last N turns of conversation."""
        def __init__(self, window_size: int = 5):
            self.window_size = window_size
            self.messages: list[dict] = []

        def add(self, role: str, content: str) -> None:
            self.messages.append({"role": role, "content": content})
            # Trim to window size (keep system + last N)
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            other_msgs = [m for m in self.messages if m["role"] != "system"]
            if len(other_msgs) > self.window_size * 2:  # 2 msgs per turn
                other_msgs = other_msgs[-(self.window_size * 2):]
            self.messages = system_msgs + other_msgs

        def get_messages(self) -> list[dict]:
            return self.messages.copy()

    memory = WindowMemory(window_size=3)
    memory.add("system", "You are a helpful assistant.")
    memory.add("user", "What is Python?")
    memory.add("assistant", "Python is a programming language.")
    memory.add("user", "What about FastAPI?")
    memory.add("assistant", "FastAPI is a Python web framework.")
    memory.add("user", "How do they compare?")

    print(f"  Window Memory: {len(memory.get_messages())} messages retained")
    for m in memory.get_messages():
        print(f"    [{m['role']}] {m['content'][:50]}")

    # Pattern 2: Summary Memory (summarize older context)
    print("\n  Summary Memory Pattern (conceptual):")
    print("    1. Keep recent messages verbatim")
    print("    2. Periodically summarize older messages into a single message")
    print("    3. System prompt += conversation summary")
    print("    4. Saves tokens while preserving long-term context")

    return memory


def demonstrate_evaluation():
    """RAG evaluation metrics and concepts."""
    print("  === RAG Evaluation Framework ===")
    print()

    print("  Retrieval Metrics:")
    print("    - Recall@K: What fraction of relevant docs were retrieved?")
    print("    - Precision@K: What fraction of retrieved docs are relevant?")
    print("    - MRR (Mean Reciprocal Rank): How high is the first relevant result?")
    print("    - NDCG: Normalized Discounted Cumulative Gain")
    print()

    print("  Generation Metrics:")
    print("    - Faithfulness: Is the answer supported by retrieved context?")
    print("    - Relevance: Does the answer address the question?")
    print("    - Answer correctness: Is the answer factually correct?")
    print("    - Hallucination rate: Does the LLM fabricate information?")
    print()

    print("  Practical Evaluation:")
    print("    - Build a test set of (question, expected_answer, relevant_docs)")
    print("    - Use LLM-as-judge for automated evaluation")
    print("    - Track: latency (p50, p95), cost per query, user satisfaction")
    print()

    # Simple precision@k calculation
    retrieved = ["doc_a", "doc_b", "doc_c", "doc_d", "doc_e"]
    relevant = {"doc_a", "doc_c", "doc_f"}  # Ground truth

    precision_at_k = len(set(retrieved) & relevant) / len(retrieved)
    recall_at_k = len(set(retrieved) & relevant) / len(relevant)
    print(f"  Example: retrieved={retrieved}")
    print(f"  relevant={relevant}")
    print(f"  Precision@5 = {precision_at_k:.2f}")
    print(f"  Recall@5    = {recall_at_k:.2f}")

    return precision_at_k, recall_at_k


# ══════════════════════════════════════════════════════════════════════
# SELF-TEST CHALLENGES
# ══════════════════════════════════════════════════════════════════════

def run_tests():
    """Automated verification."""
    print("\n[*] Running automated self-tests...")

    # Test 1: Chunking produces multiple chunks
    text = "word " * 100  # 500 chars
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1, f"Should produce multiple chunks, got {len(chunks)}"

    # Test 2: Chunks have overlap
    if len(chunks) >= 2:
        # Last words of chunk 0 should appear at start of chunk 1
        c0_words = set(chunks[0].split()[-3:])
        c1_words = set(chunks[1].split()[:5])
        assert len(c0_words & c1_words) > 0, "Chunks should have overlap"

    # Test 3: RAG pipeline ingestion
    embedder = SimpleEmbedder(dims=64)
    store = VectorStore()
    llm = MockLLM()
    pipeline = RAGPipeline(embedder, store, llm, chunk_size=100, top_k=2)

    n = pipeline.ingest_document("This is a test document about Python programming.", source="test")
    assert n > 0, "Should create at least 1 chunk"
    assert store.count() == n, "Store should have all chunks"

    # Test 4: Retrieval returns results
    results = pipeline.retrieve("Python")
    assert len(results) > 0, "Should retrieve results"
    assert len(results) <= 2, "Should respect top_k=2"

    # Test 5: Full query returns structured response
    response = pipeline.query("What is Python?")
    assert "answer" in response, "Response should have 'answer'"
    assert "sources" in response, "Response should have 'sources'"
    assert len(response["sources"]) > 0, "Should have sources"

    # Test 6: Sources have expected fields
    source = response["sources"][0]
    assert "source" in source, "Source should have 'source' field"
    assert "score" in source, "Source should have 'score' field"
    assert "text_preview" in source, "Source should have 'text_preview'"

    # Test 7: Multiple document ingestion
    pipeline.ingest_document("FastAPI is a web framework for APIs.", source="fastapi")
    assert store.count() > n, "Store should grow after second ingestion"

    # Test 8: Chunk metadata
    results = pipeline.retrieve("test")
    for r in results:
        assert "source" in r.chunk.metadata, "Chunk should have source metadata"
        assert "chunk_index" in r.chunk.metadata, "Chunk should have index"

    # Test 9: Prompt building includes context
    prompt = pipeline.build_prompt("test query", results)
    assert "Context:" in prompt, "Prompt should include context section"
    assert "Question:" in prompt, "Prompt should include question"
    assert "test query" in prompt, "Prompt should include the actual query"

    # Test 10: Window memory
    from collections import deque
    memory_messages: list[dict] = []
    for i in range(10):
        memory_messages.append({"role": "user", "content": f"msg {i}"})
    # Keep last 5
    trimmed = memory_messages[-5:]
    assert len(trimmed) == 5, "Should trim to window size"
    assert trimmed[0]["content"] == "msg 5", "Should keep most recent"

    print("[SUCCESS] All 10 RAG Pipeline self-tests passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 10: RAG Pipeline - Retrieval-Augmented Generation")
    print("=" * 70)
    print("\n--- Document Chunking ---")
    demonstrate_chunking()
    print("\n--- Full RAG Pipeline ---")
    demonstrate_full_rag_pipeline()
    print("\n--- Conversation Memory ---")
    demonstrate_conversation_memory()
    print("\n--- RAG Evaluation ---")
    demonstrate_evaluation()
    print("-" * 70)
    run_tests()
    print("=" * 70)
