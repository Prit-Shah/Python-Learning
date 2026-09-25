"""
Automated Pytest Suite for Project P6: RAG Document Chat
"""
import pytest
from ..chunker import chunk_text
from ..embedder import Embedder
from ..vector_store import VectorStore
from ..engine import RAGEngine


def test_chunker_sliding_window():
    text = "word " * 100
    chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)
    assert len(chunks) > 1
    # Check overlap: last words of chunk 0 exist in chunk 1
    c0_words = chunks[0].split()[-5:]
    c1_words = chunks[1].split()[:10]
    assert any(w in c1_words for w in c0_words)


def test_embedder_normalization():
    emb = Embedder(dims=32)
    vec = emb.embed("Python programming tutorial")
    assert vec.shape == (32,)
    import numpy as np
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-4


def test_rag_end_to_end_flow():
    engine = RAGEngine()

    doc1 = "FastAPI is a modern, high-performance web framework for building APIs with Python."
    doc2 = "PostgreSQL is a powerful open-source object-relational database system with pgvector support."

    engine.ingest_document("fastapi_docs.txt", doc1)
    engine.ingest_document("postgres_docs.txt", doc2)

    assert engine.store.count() >= 2

    # Query matching doc 1
    res1 = engine.query("What framework is used for Python APIs?")
    assert res1.retrieved_chunks_count > 0
    assert len(res1.citations) > 0
    assert "fastapi_docs.txt" in res1.citations[0].doc_name

    # Query matching doc 2
    res2 = engine.query("Tell me about PostgreSQL database vector storage")
    assert "postgres_docs.txt" in res2.citations[0].doc_name
