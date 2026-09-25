# 🧗 Project P1: CLI Expense Tracker
> **Roadmap Target**: Synthesizes Python Fundamentals, OOP, Exceptions, and Files (Phases 1–4).

---

## 🏛️ Architecture & Component Design

The expense tracker is organized following Clean Layered Architecture:

```text
p1_expense_tracker/
├── models.py       # Domain Entities (Expense, Category Enum)
├── exceptions.py   # Explicit domain errors (ExpenseNotFoundError, InvalidExpenseError)
├── storage.py      # Durability: Atomic JSON persistence (tempfile + os.replace)
├── service.py      # Business use-cases (create, filter, aggregate, export)
├── cli.py          # User interface (argparse CLI with subcommands)
└── tests/          # Pytest verification suite
```

---

## ⚡ Technical Highlights

1. **Atomic File Persistence (`storage.py`)**:
   Standard file writing (`open('file.json', 'w')`) corrupts existing data if interrupted midway. P1 implements atomic writes via:
   - Writing to a temporary file on the same filesystem.
   - Calling `os.fsync()` to force OS buffers to disk.
   - Performing an atomic `os.replace()` to swap directory pointers without data loss.

2. **Domain-Driven Design (DDD)**:
   - Data validation in `models.py` (`__post_init__`).
   - Pure business logic in `service.py` completely decoupled from CLI argument parsing.
   - Dependency inversion: `ExpenseService` receives an `ExpenseRepository` Protocol.

---

## 🚀 Usage Guide

```bash
# Add expenses
python -m projects.p1_expense_tracker.cli add --title "Dinner" --amount 45.50 --category food
python -m projects.p1_expense_tracker.cli add --title "Metro Pass" --amount 60.00 --category transport

# List with filters
python -m projects.p1_expense_tracker.cli list
python -m projects.p1_expense_tracker.cli list --category food --min 20.0

# Financial Analytics Report
python -m projects.p1_expense_tracker.cli report

# Export to CSV
python -m projects.p1_expense_tracker.cli export --format csv --output expenses.csv
```

---

## 🎙️ Senior Interview Script: Atomic Writes & Filesystem Safety

- **Interview Question**: *"How do you guarantee data consistency and prevent corruption when writing files in Python?"*
- **60-Second Verbal Answer Script**:
  * *"In a production service, I never directly write or overwrite active JSON or database files with `open(path, 'w')`. If the process crashes or gets killed by an OOM killer during `json.dump()`, the file is left truncated and corrupted."*
  * *"Instead, I write to a temporary file in the same directory using `tempfile.NamedTemporaryFile`, explicitly flush and call `os.fsync(fileno)` to force OS kernel cache to physical storage."*
  * *"Then, I execute `os.replace(temp_path, target_path)`. On modern OS filesystems (POSIX and Windows NTFS), a file rename within the same volume is an atomic inode/directory entry update. This guarantees the file is either 100% updated or 100% intact."*
