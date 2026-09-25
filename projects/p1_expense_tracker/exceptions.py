"""
Project P1: Custom Domain Exceptions
"""

class ExpenseTrackerError(Exception):
    """Base exception for all expense tracker domain errors."""
    pass


class ExpenseNotFoundError(ExpenseTrackerError):
    def __init__(self, expense_id: str):
        super().__init__(f"Expense with ID '{expense_id}' was not found.")
        self.expense_id = expense_id


class InvalidExpenseError(ExpenseTrackerError):
    pass


class StorageError(ExpenseTrackerError):
    pass
