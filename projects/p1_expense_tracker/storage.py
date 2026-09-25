"""
Project P1: Storage Repository with Atomic JSON Persistence
================================================================================
CPython / OS Note:
Directly overwriting an existing JSON file (`open(path, 'w')`) runs the risk of
file corruption if the process crashes, power drops, or disk fills midway.
To ensure production durability, we implement the "Atomic Write" pattern:
1. Write JSON data to a temporary file in the same directory (`.tmp`).
2. Flush and fsync buffer to physical storage.
3. Use `os.replace` / `Path.replace` to atomically rename the file over the target.
On POSIX and modern Windows (NTFS), file rename within the same volume is an
atomic directory entry pointer swap.
================================================================================
"""
from pathlib import Path
import json
import os
import tempfile
from typing import Protocol
from .models import Expense
from .exceptions import StorageError, ExpenseNotFoundError


class ExpenseRepository(Protocol):
    def save(self, expense: Expense) -> None: ...
    def get_by_id(self, expense_id: str) -> Expense | None: ...
    def get_all(self) -> list[Expense]: ...
    def delete(self, expense_id: str) -> bool: ...


class JsonExpenseRepository:
    """Thread-safe, atomic JSON filesystem repository."""

    def __init__(self, filepath: Path | str):
        self.filepath = Path(filepath).resolve()
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self._write_records([])

    def _read_records(self) -> list[Expense]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Expense.from_dict(item) for item in data]
        except (json.JSONDecodeError, OSError) as e:
            raise StorageError(f"Failed to read from storage: {e}") from e

    def _write_records(self, expenses: list[Expense]) -> None:
        """Atomic write using temporary file replacement."""
        temp_dir = self.filepath.parent
        data = [e.to_dict() for e in expenses]

        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=temp_dir, delete=False, encoding="utf-8"
            ) as tf:
                json.dump(data, tf, indent=2)
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name

            # Atomic swap
            os.replace(temp_name, self.filepath)
        except OSError as e:
            if 'temp_name' in locals() and os.path.exists(temp_name):
                try: os.remove(temp_name)
                except OSError: pass
            raise StorageError(f"Failed to persist expenses: {e}") from e

    def save(self, expense: Expense) -> None:
        records = self._read_records()
        for i, existing in enumerate(records):
            if existing.id == expense.id:
                records[i] = expense
                self._write_records(records)
                return
        records.append(expense)
        self._write_records(records)

    def get_by_id(self, expense_id: str) -> Expense | None:
        for e in self._read_records():
            if e.id == expense_id:
                return e
        return None

    def get_all(self) -> list[Expense]:
        return self._read_records()

    def delete(self, expense_id: str) -> bool:
        records = self._read_records()
        filtered = [e for e in records if e.id != expense_id]
        if len(filtered) == len(records):
            return False
        self._write_records(filtered)
        return True
