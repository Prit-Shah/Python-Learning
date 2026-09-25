"""
Project P1: Expense Service (Business Logic Layer)
"""
from datetime import datetime
from typing import Any
import uuid
import csv
import io
from .models import Expense, Category
from .storage import JsonExpenseRepository
from .exceptions import ExpenseNotFoundError, InvalidExpenseError


class ExpenseService:
    def __init__(self, repo: JsonExpenseRepository):
        self.repo = repo

    def create_expense(
        self,
        title: str,
        amount: float,
        category: str | Category,
        notes: str = "",
    ) -> Expense:
        title = title.strip()
        if not title:
            raise InvalidExpenseError("Title cannot be blank.")
        if amount <= 0:
            raise InvalidExpenseError(f"Amount must be strictly positive, got {amount}")

        cat = category if isinstance(category, Category) else Category.from_str(category)
        expense = Expense(
            id=str(uuid.uuid4())[:8],
            title=title,
            amount=round(float(amount), 2),
            category=cat,
            notes=notes.strip(),
        )
        self.repo.save(expense)
        return expense

    def list_expenses(
        self,
        category: str | Category | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        search_query: str | None = None,
    ) -> list[Expense]:
        records = self.repo.get_all()
        target_cat = (
            Category.from_str(category)
            if isinstance(category, str)
            else category
        )

        filtered = []
        for e in records:
            if target_cat and e.category != target_cat:
                continue
            if min_amount is not None and e.amount < min_amount:
                continue
            if max_amount is not None and e.amount > max_amount:
                continue
            if search_query:
                q = search_query.lower()
                if q not in e.title.lower() and q not in e.notes.lower():
                    continue
            filtered.append(e)

        return sorted(filtered, key=lambda x: x.created_at, reverse=True)

    def delete_expense(self, expense_id: str) -> None:
        deleted = self.repo.delete(expense_id)
        if not deleted:
            raise ExpenseNotFoundError(expense_id)

    def generate_report(self) -> dict[str, Any]:
        """Calculates total spend, category distribution, and top expenses."""
        expenses = self.repo.get_all()
        total_amount = sum(e.amount for e in expenses)

        cat_breakdown: dict[str, float] = {}
        for c in Category:
            cat_breakdown[c.value] = 0.0

        for e in expenses:
            cat_breakdown[e.category.value] += e.amount

        # Sort category breakdown by spend descending
        sorted_breakdown = dict(
            sorted(cat_breakdown.items(), key=lambda kv: kv[1], reverse=True)
        )

        top_expenses = sorted(expenses, key=lambda x: x.amount, reverse=True)[:3]

        return {
            "total_expenses_count": len(expenses),
            "total_amount": round(total_amount, 2),
            "category_breakdown": {k: round(v, 2) for k, v in sorted_breakdown.items() if v > 0},
            "top_expenses": [e.to_dict() for e in top_expenses],
        }

    def export_csv(self) -> str:
        """Exports all expenses to CSV format."""
        expenses = self.repo.get_all()
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "title", "amount", "category", "created_at", "notes"],
        )
        writer.writeheader()
        for e in expenses:
            writer.writerow(e.to_dict())
        return output.getvalue()
