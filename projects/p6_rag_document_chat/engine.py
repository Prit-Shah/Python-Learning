"""
Project P6: Retrieval-Augmented Generation Orchestrator
"""
import time
from pathlib import Path
from .models import DocumentChunk, SourceCitation, ChatResponse
from .chunker import chunk_text
from .embedder import Embedder
from .vector_store import VectorStore


class RAGEngine:
    def __init__(self, vector_store: VectorStore | None = None):
        self.embedder = Embedder()
        self.store = vector_store or VectorStore(self.embedder)

    def ingest_document(self, doc_name: str, content: str) -> int:
        """Chunks, embeds, and stores a document into the vector index."""
        raw_chunks = chunk_text(content, chunk_size=80, chunk_overlap=15)
        doc_chunks = [
            DocumentChunk(
                chunk_id=f"{doc_name}-chunk-{i}",
                doc_name=doc_name,
                chunk_index=i,
                text=text,
            )
            for i, text in enumerate(raw_chunks)
        ]
        self.store.add_chunks(doc_chunks)
        return len(doc_chunks)

    def ingest_file(self, filepath: Path | str) -> int:
        p = Path(filepath)
        content = p.read_text(encoding="utf-8")
        return self.ingest_document(p.name, content)

    def query(self, question: str, top_k: int = 3) -> ChatResponse:
        t0 = time.perf_counter()
        results = self.store.search(question, top_k=top_k)

        citations = [
            SourceCitation(
                doc_name=r.chunk.doc_name,
                chunk_index=r.chunk.chunk_index,
                relevance_score=round(r.similarity_score, 4),
                snippet=r.chunk.text[:100] + ("..." if len(r.chunk.text) > 100 else ""),
            )
            for r in results
        ]

        # Context assembly & simulated LLM answer generation
        if not results or results[0].similarity_score < 0.10:
            answer = "I could not find sufficient grounded information in the ingested documents to answer that question."
        else:
            top_snippet = results[0].chunk.text
            answer = f"Based on {citations[0].doc_name} (relevance {citations[0].relevance_score}): {top_snippet}"

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return ChatResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks_count=len(results),
            latency_ms=round(elapsed_ms, 2),
        )
