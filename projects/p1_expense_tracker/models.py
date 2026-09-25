"""
Project P1: Expense Tracker - Domain Models
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


class Category(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    HOUSING = "housing"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    EDUCATION = "education"
    MISC = "misc"

    @classmethod
    def from_str(cls, value: str) -> "Category":
        try:
            return cls(value.strip().lower())
        except ValueError:
            return cls.MISC


@dataclass
class Expense:
    """Core domain model representing a single financial transaction."""
    id: str
    title: str
    amount: float
    category: Category
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError(f"Expense amount must be strictly positive, got {self.amount}")
        if isinstance(self.category, str):
            self.category = Category.from_str(self.category)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expense":
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            amount=float(data["amount"]),
            category=Category.from_str(data.get("category", "misc")),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            notes=str(data.get("notes", "")),
        )
