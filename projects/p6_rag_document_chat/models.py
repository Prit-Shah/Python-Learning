"""
Project P6: RAG Domain Models
"""
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_name: str
    chunk_index: int
    text: str
    embedding: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    chunk: DocumentChunk
    similarity_score: float


@dataclass
class SourceCitation:
    doc_name: str
    chunk_index: int
    relevance_score: float
    snippet: str


@dataclass
class ChatResponse:
    answer: str
    citations: list[SourceCitation]
    retrieved_chunks_count: int
    latency_ms: float
