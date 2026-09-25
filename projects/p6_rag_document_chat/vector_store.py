"""
Project P6: In-Memory Vector Database
"""
import numpy as np
from .models import DocumentChunk, SearchResult
from .embedder import Embedder


class VectorStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self.chunks: list[DocumentChunk] = []

    def add_chunk(self, chunk: DocumentChunk) -> None:
        if chunk.embedding is None:
            chunk.embedding = self.embedder.embed(chunk.text)
        self.chunks.append(chunk)

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        for c in chunks:
            self.add_chunk(c)

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        if not self.chunks:
            return []

        query_vec = self.embedder.embed(query)
        matrix = np.array([c.embedding for c in self.chunks])
        scores = matrix @ query_vec

        sorted_indices = np.argsort(scores)[::-1][:top_k]

        return [
            SearchResult(chunk=self.chunks[idx], similarity_score=float(scores[idx]))
            for idx in sorted_indices
        ]

    def count(self) -> int:
        return len(self.chunks)
