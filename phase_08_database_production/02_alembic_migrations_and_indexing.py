r"""
02_alembic_migrations_and_indexing.py

============================================================
1. CONCEPT
============================================================

Database schema evolution and query performance optimization form the foundation
of production backend engineering. This module covers Alembic migration architecture
and advanced PostgreSQL indexing strategies:

1. Alembic Migration Architecture:
   - Alembic is the official database migration tool for SQLAlchemy.
   - Core Components:
     * `env.py`: Python script executed during migrations. Configures the connection engine,
       imports SQLAlchemy `target_metadata`, and delegates to offline or online migration modes.
     * `script.py.mako`: Template used to generate new migration scripts.
     * Version Table (`alembic_version`): Single-row table in the database tracking the
       current applied revision hash.
     * Revision DAG (Directed Acyclic Graph): Migrations form a linked graph via `revision`
       and `down_revision` pointers, supporting branching and merging (`alembic merge`).

2. Migration Modes:
   - Online Mode (`alembic upgrade head`): Connects directly to the live database and applies
     DDL statements inside atomic transactions.
   - Offline Mode (`alembic upgrade head --sql`): Generates raw, sequential SQL scripts without
     connecting to the database, enabling Enterprise DBA review and governance approval.

3. Advanced PostgreSQL Indexing Strategies:
   - Standard B-Tree: Balanced tree providing $O(\log N)$ search, range queries, and prefix matching.
   - Composite (Multi-Column) Index: An index across multiple columns `(A, B, C)`.
     * The Leftmost Prefix Rule: Queries can utilize the index ONLY if their filter predicates
       start with the leading columns of the index definition (`A`, or `A AND B`, or `A AND B AND C`).
       A query filtering solely on `B` or `C` cannot use the composite index!
     * Column Ordering Principle: Equality filters (highest cardinality) -> Range filters -> Sort orders.
   - Partial Indexes: `CREATE INDEX ... WHERE status = 'ACTIVE'`.
     * Dramatically reduces index size in RAM and disk by indexing only a hot fraction of the table.
   - Covering Indexes (`INCLUDE` clause):
     * Appends non-search payload columns to leaf pages (`CREATE INDEX ... ON orders(user_id) INCLUDE (total_amount)`).
     * Enables Index-Only Scans: The database engine retrieves requested columns directly from
       the index without accessing the table heap pages!


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Alembic / SQLAlchemy)      | JavaScript / TypeScript (Prisma)   |
+------------------------------+------------------------------------+------------------------------------+
| Migration Generation         | `alembic revision --autogenerate`  | `prisma migrate dev`               |
| Schema Metadata Source       | `Base.metadata` in Python code     | `schema.prisma` DSL file           |
| Version Tracking             | `alembic_version` table (hash ID)  | `_prisma_migrations` table         |
| Migration Up/Down Code       | Python functions `upgrade/downgrade`| Raw SQL scripts in directories     |
| Raw SQL Generation           | `alembic upgrade head --sql`       | `prisma migrate diff`              |
| Index Declaration            | `Index('idx_name', col1, col2)`    | `@@index([col1, col2])`            |
| Partial Index Support        | Native (`postgresql_where=...`)    | Raw SQL migration override         |
| Covering Index Support       | Native (`postgresql_include=...`)  | Raw SQL migration override         |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. Prisma uses a proprietary declarative Domain Specific Language (`schema.prisma`) and
   generates raw SQL migration files. Alembic uses pure Python scripts (`upgrade()` and `downgrade()`)
   exposing SQLAlchemy's `op` namespace (`op.create_table`, `op.add_column`), allowing dynamic Python
   logic, data migrations, and environment lookups inside migration scripts.
2. In TypeScript ORMs, creating advanced PostgreSQL structures (partial indexes, expression indexes,
   or `CONCURRENTLY` modifiers) often requires abandoning the ORM DSL and writing manual SQL scripts.
   SQLAlchemy and Alembic support these advanced dialect-specific features natively in Python.


============================================================
3. UNDER THE HOOD (Database Internals & Reflection)
============================================================

1. Alembic Autogenerate Engine Mechanics:
   - When `alembic revision --autogenerate` runs:
     1. Alembic reflects the live database schema into memory using SQLAlchemy's `Inspector`.
     2. It inspects `target_metadata` (the Python model definitions).
     3. It executes a schema diff comparison: detecting missing tables, missing columns, changed
        nullability, altered types, and index differences.
     4. It renders Python AST nodes corresponding to `op.create_table`, `op.add_column`, etc.

2. Zero-Downtime Index Creation (`CONCURRENTLY`):
   - In PostgreSQL, standard `CREATE INDEX` acquires a `SHARE` lock on the target table,
     blocking all incoming `INSERT`, `UPDATE`, and `DELETE` operations until the build finishes.
     On a 100M row table, this can cause minutes of application downtime and connection pool spikes.
   - `CREATE INDEX CONCURRENTLY` builds the index in multiple passes without holding an exclusive lock,
     allowing concurrent writes to continue without service degradation.

3. Index-Only Scans vs Heap Lookups:
   - Normally, an index scan finds matching row pointers (`ctid`) in the index tree, and then
     must perform random I/O reads against the table heap pages to retrieve un-indexed columns.
   - With Covering Indexes (`INCLUDE`), all columns requested by the query exist inside the index leaf page.
     PostgreSQL uses the Visibility Map to confirm rows are visible to active transactions,
     serving queries with zero heap page lookups.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Column Rename Data-Loss Trap:
   - Alembic autogenerate cannot detect table or column renames!
   - If you rename `user_name` to `username` in your model, autogenerate emits:
     `op.drop_column('users', 'user_name')` followed by `op.add_column('users', sa.Column('username', ...))`.
   - Running this blindly will PERMANENTLY DROP all existing data in that column!
   - FIX: Always inspect generated migration files. Replace `drop_column` + `add_column` with
     `op.alter_column('users', 'user_name', new_column_name='username')`.

2. The Empty `env.py` Drop-All Disaster:
   - If model classes are not imported into `migrations/env.py`, `target_metadata` remains empty.
   - Running `alembic revision --autogenerate` will generate instructions to DROP EVERY SINGLE TABLE
     in your database!
   - FIX: Always ensure `from myapp.models import Base; target_metadata = Base.metadata` is configured in `env.py`.

3. Leftmost Prefix Failure on Composite Indexes:
   - Defining a composite index `(tenant_id, created_at, status)` does NOT speed up queries that
     filter only on `status` or only on `created_at`.
   - FIX: Design indexes around actual application query access patterns, placing equality filters first.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does Alembic detect database schema differences, and what are its critical autogenerate blind spots?"
A1: "Alembic uses SQLAlchemy's schema reflection API to compare the live database catalog against the
     `Base.metadata` registry declared in Python. It detects table and column additions, deletions,
     and basic constraint changes. However, it has major blind spots:
     First, it cannot distinguish a column or table rename from a DROP plus ADD operation; executing
     unreviewed migrations can drop production data columns.
     Second, it does not automatically detect custom Postgres check constraints or table partitions.
     For enterprise production, all autogenerated scripts must be manually audited and tested against
     a shadow database in CI before running in production."

Q2: "Explain the Leftmost Prefix Rule and how you determine column ordering in a composite index."
A2: "In a B-Tree composite index on columns `(A, B, C)`, entries are sorted primarily by A, then by B,
     then by C. The database query planner can use this index to satisfy search filters on `A`, `(A, B)`,
     or `(A, B, C)`. However, if a query filters on `B` or `C` alone without `A`, the sorted hierarchy
     cannot be traversed, forcing a sequential table scan.
     When determining column order:
     1. Place columns used in exact equality filters (`=`) first, ordered by highest selectivity.
     2. Follow with columns used in range or inequality filters (`>`, `<`, `BETWEEN`).
     3. Place columns used for `ORDER BY` sorting last to enable index-based sorting without an
        in-memory sort operation."

Q3: "What is the purpose of PostgreSQL Partial Indexes and Covering Indexes?"
A3: "A Partial Index uses a `WHERE` clause to index only a subset of table rows—for example, indexing
     orders where `status = 'PENDING'`. In a database with 100 million archived orders and only 5,000 pending
     orders, a partial index is 99% smaller, stays permanently cached in RAM, and speeds up write operations
     for completed orders.
     A Covering Index uses the `INCLUDE` clause to attach non-search payload columns to the index leaf nodes.
     This enables PostgreSQL to perform an Index-Only Scan: all requested data is resolved within the index
     pages without reading the underlying table heap pages, eliminating random disk I/O."
"""

import sys
import warnings
warnings.filterwarnings("ignore")
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, DateTime, Index, func
from sqlalchemy.dialects import postgresql

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. ADVANCED INDEX DECLARATIONS VIA SQLALCHEMY METADATA
# ==============================================================================

metadata = MetaData()

# Multi-tenant enterprise accounts table demonstrating advanced indexing
accounts_table = Table(
    "accounts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", Integer, nullable=False),
    Column("email", String(120), nullable=False),
    Column("status", String(30), nullable=False),  # 'ACTIVE', 'SUSPENDED', 'PENDING'
    Column("is_verified", Boolean, default=False),
    Column("api_key", String(64), nullable=True),
    Column("created_at", DateTime, default=func.now()),

    # 1. Composite Index: Follows Leftmost Prefix Rule
    # Ordered: tenant_id (equality) -> status (equality) -> created_at (range/sort)
    Index("idx_accounts_tenant_status_created", "tenant_id", "status", "created_at"),

    # 2. Partial Index: Indexes ONLY active verified users for ultra-fast auth lookup
    Index(
        "idx_accounts_active_verified_email",
        "email",
        postgresql_where=(Column("status") == "ACTIVE")
    ),

    # 3. Covering Index: Accelerates API Key authentication via Index-Only Scan
    # The API key is in the B-Tree search key, while tenant_id & is_verified are payload in leaf nodes
    Index(
        "idx_accounts_api_key_covering",
        "api_key",
        postgresql_include=["tenant_id", "is_verified"]
    )
)


# ==============================================================================
# 2. QUERY PLANNER EVALUATION SIMULATOR (LEFTMOST PREFIX ENGINE)
# ==============================================================================

class IndexSimulator:
    """
    Simulates database query planner index selection logic to mathematically
    validate whether query predicates adhere to the Leftmost Prefix Rule.
    """

    @staticmethod
    def evaluate_composite_index(
        index_columns: List[str],
        query_equality_filters: Set[str],
        query_range_filters: Set[str] = set()
    ) -> Tuple[bool, int, str]:
        """
        Determines whether a query can use a composite B-Tree index and how many
        leading columns are actively matched.
        """
        if not index_columns:
            return False, 0, "Index contains no columns."

        matched_columns = 0
        all_filters = query_equality_filters.union(query_range_filters)

        # Check leftmost leading column
        leading_col = index_columns[0]
        if leading_col not in all_filters:
            return False, 0, f"Violates Leftmost Prefix Rule: Query does not filter on leading column '{leading_col}'."

        for col in index_columns:
            if col in query_equality_filters:
                matched_columns += 1
            elif col in query_range_filters:
                matched_columns += 1
                # Range scan stops further index column utilization for equality
                break
            else:
                # Discontinuity encountered
                break

        return True, matched_columns, f"Successfully utilizes index matching {matched_columns} leading column(s)."

    @staticmethod
    def evaluate_partial_index(
        index_column: str,
        index_predicate: Dict[str, Any],
        query_filter: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a query predicate satisfies a Partial Index WHERE clause.
        """
        if index_column not in query_filter:
            return False, f"Query does not filter on indexed column '{index_column}'."

        # Check if query guarantees the index predicate condition
        for pred_key, pred_val in index_predicate.items():
            if query_filter.get(pred_key) != pred_val:
                return False, f"Query condition '{pred_key}={query_filter.get(pred_key)}' does not satisfy partial index WHERE clause '{pred_key}={pred_val}'."

        return True, "Query conditions satisfy partial index predicate; partial index is eligible."


# ==============================================================================
# 3. ALEMBIC MIGRATION GRAPH (DAG) RESOLVER
# ==============================================================================

class MigrationRevision:
    def __init__(self, revision_id: str, down_revision: Optional[str], description: str):
        self.revision_id = revision_id
        self.down_revision = down_revision
        self.description = description

    def __repr__(self) -> str:
        return f"<Rev {self.revision_id} (down={self.down_revision})>"


class MigrationGraphResolver:
    """Simulates Alembic's DAG ordering and topological revision resolution."""

    def __init__(self) -> None:
        self.revisions: Dict[str, MigrationRevision] = {}

    def add_revision(self, rev: MigrationRevision) -> None:
        self.revisions[rev.revision_id] = rev

    def get_linear_upgrade_path(self, target_head: str) -> List[MigrationRevision]:
        """Traces back from head to root and returns execution order (root -> head)."""
        if target_head not in self.revisions:
            raise ValueError(f"Revision '{target_head}' not found in migration graph.")

        path: List[MigrationRevision] = []
        current: Optional[str] = target_head

        visited: Set[str] = set()
        while current is not None:
            if current in visited:
                raise RuntimeError(f"Cyclic dependency detected at revision {current}!")
            visited.add(current)

            rev = self.revisions[current]
            path.append(rev)
            current = rev.down_revision

        # Reverse so root is executed first
        path.reverse()
        return path


# ==============================================================================
# 4. SELF-TESTING SUITE
# ==============================================================================

def run_tests() -> None:
    print("\n[*] Starting automated test suite for 02_alembic_migrations_and_indexing.py...")

    # ------------------------------------------------------------
    # Test 1: SQLAlchemy Table Index Definitions
    # ------------------------------------------------------------
    print("  -> Testing SQLAlchemy table and index schema definitions...")
    indexes = {idx.name: idx for idx in accounts_table.indexes}
    assert "idx_accounts_tenant_status_created" in indexes
    assert "idx_accounts_active_verified_email" in indexes
    assert "idx_accounts_api_key_covering" in indexes

    # Verify composite index column ordering
    comp_idx = indexes["idx_accounts_tenant_status_created"]
    col_names = [col.name for col in comp_idx.columns]
    assert col_names == ["tenant_id", "status", "created_at"], f"Unexpected column ordering: {col_names}"

    # ------------------------------------------------------------
    # Test 2: Composite Index Leftmost Prefix Rule Validation
    # ------------------------------------------------------------
    print("  -> Testing Leftmost Prefix Rule simulator across query variations...")
    comp_cols = ["tenant_id", "status", "created_at"]

    # Case A: Queries with leading column 'tenant_id' -> MUST USE INDEX
    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"tenant_id"}
    )
    assert can_use is True and matched == 1

    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"tenant_id", "status"}
    )
    assert can_use is True and matched == 2

    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"tenant_id", "status", "created_at"}
    )
    assert can_use is True and matched == 3

    # Case B: Equality on tenant_id, Range on status
    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols,
        query_equality_filters={"tenant_id"},
        query_range_filters={"status"}
    )
    assert can_use is True and matched == 2

    # Case C: Discontinuity (tenant_id + created_at without status) -> Uses only 1 column
    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"tenant_id", "created_at"}
    )
    assert can_use is True and matched == 1, "Discontinuity should only match leading column"

    # Case D: Missing leading column -> MUST FAIL (Full Table Scan)
    can_use, matched, msg = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"status", "created_at"}
    )
    assert can_use is False and matched == 0
    assert "Violates Leftmost Prefix" in msg

    can_use, matched, _ = IndexSimulator.evaluate_composite_index(
        comp_cols, query_equality_filters={"created_at"}
    )
    assert can_use is False

    # ------------------------------------------------------------
    # Test 3: Partial Index Predicate Matching
    # ------------------------------------------------------------
    print("  -> Testing Partial Index eligibility conditions...")
    # Index: email WHERE status = 'ACTIVE'
    partial_pred = {"status": "ACTIVE"}

    # Eligible query: filters on email and guarantees status='ACTIVE'
    query_ok = {"email": "user@domain.com", "status": "ACTIVE"}
    eligible, _ = IndexSimulator.evaluate_partial_index("email", partial_pred, query_ok)
    assert eligible is True

    # Ineligible query: status='SUSPENDED'
    query_bad = {"email": "user@domain.com", "status": "SUSPENDED"}
    eligible, _ = IndexSimulator.evaluate_partial_index("email", partial_pred, query_bad)
    assert eligible is False

    # Ineligible query: email filtered but status omitted (could match inactive rows)
    query_missing = {"email": "user@domain.com"}
    eligible, _ = IndexSimulator.evaluate_partial_index("email", partial_pred, query_missing)
    assert eligible is False

    # ------------------------------------------------------------
    # Test 4: Alembic DAG Revision Resolution
    # ------------------------------------------------------------
    print("  -> Testing Alembic DAG migration chain resolution...")
    dag = MigrationGraphResolver()
    dag.add_revision(MigrationRevision("rev_001_init", None, "Initial schema"))
    dag.add_revision(MigrationRevision("rev_002_accounts", "rev_001_init", "Add accounts table"))
    dag.add_revision(MigrationRevision("rev_003_indexes", "rev_002_accounts", "Add composite indexes"))
    dag.add_revision(MigrationRevision("rev_004_covering", "rev_003_indexes", "Add covering index"))

    upgrade_path = dag.get_linear_upgrade_path("rev_004_covering")
    assert len(upgrade_path) == 4
    assert [r.revision_id for r in upgrade_path] == [
        "rev_001_init",
        "rev_002_accounts",
        "rev_003_indexes",
        "rev_004_covering"
    ]

    # Test error handling on missing target revision
    try:
        dag.get_linear_upgrade_path("rev_non_existent")
        assert False, "Should raise ValueError on missing revision"
    except ValueError:
        pass

    print("[SUCCESS] All 4 Alembic & Advanced Indexing tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 8 - 02: Alembic Migrations & Advanced Indexing Architecture")
    print("=" * 70)
    run_tests()
    print("=" * 70)
