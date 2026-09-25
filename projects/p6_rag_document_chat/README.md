# 🧗 Project P6: RAG Document Chat Engine
> **Roadmap Target**: Synthesizes Document Ingestion, Overlapping Chunking, Vector Embeddings, and Grounded Context Retrieval (Phase 10).

---

## 🏛️ Architecture & Component Design

```text
p6_rag_document_chat/
├── models.py       # Domain Entities (DocumentChunk, SearchResult, SourceCitation)
├── chunker.py      # Sliding window boundary-preserving text chunker
├── embedder.py     # Normalized float32 embedding generator
├── vector_store.py # In-Memory Vector Store with Cosine Nearest-Neighbor Search
├── engine.py       # RAGEngine orchestrating ingestion, retrieval & prompt injection
├── cli.py          # Interactive command-line interface
└── tests/          # Pytest verification suite
```

---

## ⚡ Technical Highlights

1. **Sliding Window Chunking with Boundary Protection**:
   Fixed-character splitting chops sentences mid-word. Our chunker operates on word boundaries with a configurable sliding overlap window (e.g. 80 words with 15-word overlap) to preserve semantic cohesion.

2. **Strict Grounded Attribution**:
   The engine returns explicit `SourceCitation` objects containing the source filename, chunk index, and cosine relevance score, eliminating ungrounded hallucinations.

---

## 🚀 Running the Engine

```bash
# Ingest and query
python -m projects.p6_rag_document_chat.cli --ingest sample.md --query "How does authentication work?"
```
