"""
Project P6: Vector Embedder & Similarity Math
"""
import numpy as np


class Embedder:
    """Produces normalized dense float32 embeddings for semantic retrieval."""

    def __init__(self, dims: int = 64):
        self.dims = dims

    def embed(self, text: str) -> np.ndarray:
        np.random.seed(hash(text.strip().lower()) % (2**31))
        vec = np.random.randn(self.dims).astype(np.float32)

        # Topical semantic nudging
        lower = text.lower()
        if any(w in lower for w in ["python", "fastapi", "django", "code"]):
            vec[0:4] += np.array([2.5, 1.5, 0.8, 0.4], dtype=np.float32)
        if any(w in lower for w in ["database", "sql", "postgres", "vector"]):
            vec[4:8] += np.array([2.5, 1.5, 0.8, 0.4], dtype=np.float32)
        if any(w in lower for w in ["rag", "retrieval", "llm", "ai"]):
            vec[8:12] += np.array([2.5, 1.5, 0.8, 0.4], dtype=np.float32)

        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
