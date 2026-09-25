"""
Project P2: API Data Collector - Domain Models
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class FetchResult:
    """Represents the outcome of an individual HTTP endpoint collection."""
    url: str
    status_code: int | None
    latency_ms: float
    data: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 1
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_success(self) -> bool:
        return self.status_code is not None and 200 <= self.status_code < 300 and self.error is None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollectionBatchSummary:
    """Aggregated metrics across a concurrent collection batch."""
    total_requested: int
    successful: int
    failed: int
    total_elapsed_ms: float
    avg_latency_ms: float
    success_rate_pct: float
