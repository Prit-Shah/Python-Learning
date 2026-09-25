"""
Automated Pytest Suite for Project P1: Expense Tracker
"""
import pytest
import tempfile
import os
from pathlib import Path
from ..models import Expense, Category
from ..storage import JsonExpenseRepository
from ..service import ExpenseService
from ..exceptions import InvalidExpenseError, ExpenseNotFoundError
from ..cli import main


@pytest.fixture
def temp_repo():
    """Provides an isolated clean repository for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_expenses.json"
        repo = JsonExpenseRepository(db_path)
        yield repo


@pytest.fixture
def service(temp_repo):
    return ExpenseService(temp_repo)


def test_create_expense_success(service):
    exp = service.create_expense(
        title="Lunch at Deli",
        amount=18.50,
        category="food",
        notes="Sandwich & coffee",
    )
    assert exp.id is not None
    assert exp.title == "Lunch at Deli"
    assert exp.amount == 18.50
    assert exp.category == Category.FOOD
    assert exp.notes == "Sandwich & coffee"


def test_create_expense_validation(service):
    with pytest.raises(InvalidExpenseError):
        service.create_expense(title="", amount=10.0, category="food")

    with pytest.raises(InvalidExpenseError):
        service.create_expense(title="Coffee", amount=-5.0, category="food")

    with pytest.raises(InvalidExpenseError):
        service.create_expense(title="Free item", amount=0.0, category="food")


def test_list_and_filter(service):
    service.create_expense(title="Groceries", amount=50.0, category="food")
    service.create_expense(title="Metro pass", amount=30.0, category="transport")
    service.create_expense(title="Dinner out", amount=75.0, category="food")

    # Filter by category
    food_items = service.list_expenses(category="food")
    assert len(food_items) == 2
    assert all(e.category == Category.FOOD for e in food_items)

    # Filter by min/max amount
    mid_items = service.list_expenses(min_amount=40.0, max_amount=60.0)
    assert len(mid_items) == 1
    assert mid_items[0].title == "Groceries"


def test_delete_expense(service):
    exp = service.create_expense(title="Movie", amount=14.0, category="entertainment")
    assert len(service.list_expenses()) == 1

    service.delete_expense(exp.id)
    assert len(service.list_expenses()) == 0

    with pytest.raises(ExpenseNotFoundError):
        service.delete_expense("nonexistent-id")


def test_generate_report(service):
    service.create_expense(title="Rent", amount=1200.0, category="housing")
    service.create_expense(title="Internet", amount=80.0, category="utilities")
    service.create_expense(title="Dinner", amount=120.0, category="food")

    report = service.generate_report()
    assert report["total_expenses_count"] == 3
    assert report["total_amount"] == 1400.0
    assert report["category_breakdown"]["housing"] == 1200.0
    assert len(report["top_expenses"]) == 3
    assert report["top_expenses"][0]["title"] == "Rent"


def test_export_csv(service):
    service.create_expense(title="Book", amount=25.0, category="education")
    csv_data = service.export_csv()
    assert "Book" in csv_data
    assert "25.0" in csv_data
    assert "education" in csv_data


def test_cli_integration(tmp_path):
    db_file = str(tmp_path / "cli_db.json")

    # Add expense via CLI
    code = main(["--db", db_file, "add", "--title", "Gym", "--amount", "40.0", "--category", "health"])
    assert code == 0

    # List expenses via CLI
    code = main(["--db", db_file, "list"])
    assert code == 0

    # Report via CLI
    code = main(["--db", db_file, "report"])
    assert code == 0
