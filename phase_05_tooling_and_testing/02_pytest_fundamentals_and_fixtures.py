"""
Phase 5: Professional Python Tooling - Pytest Fundamentals & Fixtures
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Pytest is the de-facto testing framework in modern Python.
   - Core Features:
     * Plain 'assert' statements: No need for 'self.assertEqual()'; pytest rewrites Python's
       abstract syntax tree (AST) to provide detailed expression diffs upon failure.
     * Fixtures ('@pytest.fixture'): Dependency injection for reusable setup and teardown.
     * The 'yield' fixture pattern: Code before 'yield' runs during setup; code after 'yield'
       executes during teardown!
     * Fixture Scopes:
       - 'function' (default): Fresh instance per test function.
       - 'class': Shared across tests within a class.
       - 'module': Shared across all tests in a file.
       - 'session': Shared across the entire test suite run (e.g. Docker DB container).
     * Parametrization ('@pytest.mark.parametrize'): Generates separate test cases from data tables.
   - JS/TS Analogy:
     * In Jest/Vitest: 'beforeEach()', 'afterEach()', and 'test.each()'.
     * In Pytest: Named fixture injection into function parameters and '@pytest.mark.parametrize'.

2. UNDER THE HOOD (CPython & Memory):
   - Pytest intercepts Python's module import mechanism and uses an AST (Abstract Syntax Tree)
     rewriter to transform simple 'assert a == b' into rich diagnostic inspections showing
     intermediate sub-expression values without third-party assertion libraries.

3. COMMON GOTCHA:
   - Fixture Name Mismatch: Pytest matches fixtures by exact argument name:
     @pytest.fixture
     def db(): ...
     def test_query(database): # BUG: Name error! Must match 'def test_query(db):'
   - Mutable Session Fixture: Mutating state inside a session-scoped fixture leaks dirty data into
     subsequent tests, causing non-deterministic test failures!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How do pytest fixtures work, what is the 'yield' fixture pattern, and how does
       pytest compare to standard unittest or Jest?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Fixture Architecture:
      "Unlike legacy unittest which relies on class inheritance and setUp/tearDown methods,
       pytest uses explicit, modular dependency injection via fixtures. You define a fixture with
       the '@pytest.fixture' decorator, and any test function requests it simply by including
       the fixture name as an argument."
   2. The Yield Fixture Pattern:
      "For setup and teardown, pytest uses generator functions with 'yield':
       - Everything before 'yield' executes before the test runs (e.g. creating a test database record or opening a client).
       - The 'yield' statement hands the resource to the test.
       - Everything after 'yield' executes after the test finishes, even if the test fails.
       This mirrors context managers and ensures guaranteed resource cleanup."
   3. Parametrization:
      "With '@pytest.mark.parametrize', we can test edge cases, boundaries, and validation errors
       across tabular datasets without duplicating test logic, with each row executing as an
       independent test case in test reports."
================================================================================
"""

import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# DEMONSTRATION OF LOGICAL PATTERNS (Runnable standalone)
# ==============================================================================

class MemoryDatabase:
    """Mock database simulating setup, operations, and teardown."""
    def __init__(self):
        self.connected = False
        self.records = {}

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False
        self.records.clear()

    def insert(self, key: str, value: str):
        if not self.connected:
            raise RuntimeError("Database not connected!")
        self.records[key] = value

    def get(self, key: str):
        return self.records.get(key)


def demonstrate_yield_fixture_lifecycle():
    print("\n--- 1. Yield Fixture Setup & Teardown Lifecycle ---")
    
    # Simulating what pytest does under the hood with a yield fixture
    def db_fixture():
        # Setup phase
        db = MemoryDatabase()
        db.connect()
        print("  [Setup] Database connected.")
        try:
            yield db
        finally:
            # Teardown phase
            db.disconnect()
            print("  [Teardown] Database disconnected and cleaned up.")

    # Execute simulation
    gen = db_fixture()
    db_instance = next(gen)
    
    # Test executes with resource
    db_instance.insert("user:1", "Alice")
    print(f"  [Test Execution] Record inserted: user:1 -> {db_instance.get('user:1')}")
    
    # Teardown triggered by completing generator
    try:
        next(gen)
    except StopIteration:
        pass


def demonstrate_parametrization_concept():
    print("\n--- 2. Tabular Parametrized Logic ---")
    def calculate_discount(price: float, tier: str) -> float:
        discounts = {"STANDARD": 0.0, "VIP": 0.15, "ENTERPRISE": 0.30}
        return price * (1.0 - discounts.get(tier, 0.0))

    # Test cases table: (price, tier, expected_final)
    test_cases = [
        (100.0, "STANDARD", 100.0),
        (100.0, "VIP", 85.0),
        (200.0, "ENTERPRISE", 140.0),
        (50.0, "UNKNOWN", 50.0),
    ]

    for price, tier, expected in test_cases:
        actual = calculate_discount(price, tier)
        assert abs(actual - expected) < 1e-6
        print(f"  [PASS] Price ${price}, Tier '{tier}' -> ${actual:.2f} (Expected: ${expected:.2f})")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def validate_username(username: str) -> bool:
    """Username must be alphanumeric, between 3 and 16 characters."""
    if not isinstance(username, str):
        return False
    return 3 <= len(username) <= 16 and username.isalnum()


def run_tests():
    print("\n[*] Running automated self-tests for 02_pytest_fundamentals_and_fixtures.py...")
    # Parametrized test table for username validation
    test_matrix = [
        ("alice", True),
        ("dev123", True),
        ("ab", False),               # Too short
        ("this_is_way_too_long_name", False), # Too long
        ("user!name", False),         # Non-alphanumeric
        ("", False),                  # Empty
        (12345, False),               # Invalid type
    ]

    for uname, expected in test_matrix:
        assert validate_username(uname) is expected, f"Failed for username: {uname}"

    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 5 - Pytest Fundamentals & Fixtures")
    print("=" * 65)
    demonstrate_yield_fixture_lifecycle()
    demonstrate_parametrization_concept()
    print("-" * 65)
    run_tests()
    print("=" * 65)
