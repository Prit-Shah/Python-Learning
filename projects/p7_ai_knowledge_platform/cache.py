"""
Project P7: Semantic Caching Layer
"""
import numpy as np


class SemanticCache:
    def __init__(self, threshold: float = 0.88):
        self.threshold = threshold
        self.entries: list[tuple[str, np.ndarray, str]] = []
        self.hits = 0
        self.misses = 0

    def _embed(self, text: str) -> np.ndarray:
        np.random.seed(hash(text.strip().lower()) % (2**31))
        vec = np.random.randn(32).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def get(self, query: str) -> str | None:
        q_vec = self._embed(query)
        for original_query, vec, response in self.entries:
            sim = float(np.dot(q_vec, vec))
            if sim >= self.threshold:
                self.hits += 1
                return response
        self.misses += 1
        return None

    def set(self, query: str, response: str):
        self.entries.append((query, self._embed(query), response))


semantic_cache = SemanticCache()
