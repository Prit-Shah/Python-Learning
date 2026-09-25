"""
Project P1: CLI Application Entrypoint
================================================================================
CLI command interface for expense tracking.
Usage:
  python cli.py add --title "Dinner" --amount 45.50 --category food
  python cli.py list
  python cli.py report
  python cli.py delete <id>
  python cli.py export --format csv --output expenses.csv
================================================================================
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

import argparse
from pathlib import Path
from .models import Category
from .storage import JsonExpenseRepository
from .service import ExpenseService
from .exceptions import ExpenseTrackerError


DEFAULT_DB = Path.home() / ".expenses.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expenses",
        description="P1: Production CLI Expense Tracker with Atomic Persistence",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DEFAULT_DB),
        help="Path to expenses JSON database file",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: add
    add_parser = subparsers.add_parser("add", help="Record a new expense")
    add_parser.add_argument("--title", "-t", required=True, help="Expense title/description")
    add_parser.add_argument("--amount", "-a", type=float, required=True, help="Cost amount (e.g. 15.50)")
    add_parser.add_argument(
        "--category", "-c",
        choices=[c.value for c in Category],
        default="misc",
        help="Expense category classification",
    )
    add_parser.add_argument("--notes", "-n", default="", help="Optional notes or details")

    # Command: list
    list_parser = subparsers.add_parser("list", help="List recorded expenses")
    list_parser.add_argument("--category", "-c", choices=[c.value for c in Category], help="Filter by category")
    list_parser.add_argument("--min", type=float, help="Minimum amount filter")
    list_parser.add_argument("--max", type=float, help="Maximum amount filter")
    list_parser.add_argument("--search", "-s", help="Text search filter")

    # Command: report
    subparsers.add_parser("report", help="Show financial summary & category distribution")

    # Command: delete
    del_parser = subparsers.add_parser("delete", help="Delete an expense by ID")
    del_parser.add_argument("id", help="The 8-character ID of the expense")

    # Command: export
    export_parser = subparsers.add_parser("export", help="Export expenses to file")
    export_parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    export_parser.add_argument("--output", "-o", required=True, help="Destination file path")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    repo = JsonExpenseRepository(args.db)
    service = ExpenseService(repo)

    try:
        if args.command == "add":
            item = service.create_expense(
                title=args.title,
                amount=args.amount,
                category=args.category,
                notes=args.notes,
            )
            print(f"[SUCCESS] Recorded expense '{item.title}' (${item.amount:.2f}) with ID: {item.id}")

        elif args.command == "list":
            expenses = service.list_expenses(
                category=args.category,
                min_amount=args.min,
                max_amount=args.max,
                search_query=args.search,
            )
            if not expenses:
                print("No expenses found matching the criteria.")
                return 0

            print(f"{'ID':<10} {'DATE':<22} {'CATEGORY':<14} {'AMOUNT':>10}  {'TITLE'}")
            print("-" * 75)
            for e in expenses:
                print(f"{e.id:<10} {e.created_at[:19]:<22} {e.category.value:<14} ${e.amount:>9.2f}  {e.title}")

        elif args.command == "report":
            report = service.generate_report()
            print("========================================")
            print(" FINANCIAL EXPENSE REPORT SUMMARY")
            print("========================================")
            print(f"Total Transactions: {report['total_expenses_count']}")
            print(f"Total Expenditure:  ${report['total_amount']:.2f}")
            print("
Category Breakdown:")
            for cat, amount in report["category_breakdown"].items():
                pct = (amount / report["total_amount"]) * 100 if report["total_amount"] > 0 else 0
                print(f"  - {cat:<14}: ${amount:>8.2f} ({pct:5.1f}%)")

            if report["top_expenses"]:
                print("
Top 3 Largest Transactions:")
                for top in report["top_expenses"]:
                    print(f"  * [{top['id']}] ${top['amount']:.2f} - {top['title']} ({top['category']})")

        elif args.command == "delete":
            service.delete_expense(args.id)
            print(f"[SUCCESS] Deleted expense {args.id}")

        elif args.command == "export":
            if args.format == "csv":
                content = service.export_csv()
            else:
                import json
                content = json.dumps([e.to_dict() for e in repo.get_all()], indent=2)

            Path(args.output).write_text(content, encoding="utf-8")
            print(f"[SUCCESS] Exported expenses to {args.output}")

    except ExpenseTrackerError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
