"""
02_pytest_fundamentals_and_fixtures.py

============================================================
1. CONCEPT
============================================================

Pytest is the dominant testing framework in the Python ecosystem, replacing
boilerplate-heavy xUnit-style inheritance with dependency-injected fixtures,
standard assert statements, and AST-driven diagnostics:

1. Plain Assert Statements & AST Rewriting:
   - Pytest uses standard Python `assert a == b` statements instead of cumbersome
     assertions like `self.assertEqual(a, b)`.
   - Under the hood, pytest rewrites the Abstract Syntax Tree (AST) during module
     import to intercept assertions and produce granular failure diffs.

2. Fixtures as Dependency Injection (`@pytest.fixture`):
   - Rather than relying on class-based `setUp()` and `tearDown()`, test functions
     request resources explicitly by including fixture names in their parameter list.
   - Fixture Scopes:
     - `function` (default): Created fresh for each test function invocation.
     - `class`: Shared across all test methods in a test class.
     - `module`: Created once per test module file.
     - `session`: Created once across the entire test suite execution run (e.g. Docker container).

3. The "Yield" Fixture Pattern:
   - Replaces separate setup/teardown methods with a single generator:
     - Code BEFORE `yield`: Setup logic (e.g. establishing database connection).
     - The `yield` expression: Hands the resource to the executing test.
     - Code AFTER `yield`: Teardown logic (runs unconditionally, even if the test fails).

4. Parametrization (`@pytest.mark.parametrize`):
   - Generates distinct, isolated test cases from tabular input datasets.
   - Stacking multiple `@pytest.mark.parametrize` decorators creates a combinatorial
     Cartesian product of test inputs.

5. Testing Exceptions (`pytest.raises`):
   - Context manager verifying that expected exceptions are raised:
     `with pytest.raises(ValueError, match=r"negative balance") as exc_info:`
   - Validates exception type, message content, and attributes.

6. Built-in Standard Fixtures:
   - `tmp_path`: Provides an isolated, auto-cleaned `pathlib.Path` temporary folder.
   - `monkeypatch`: Safely mutates environment variables, system attributes, or dicts.
   - `capsys`: Captures text written to `sys.stdout` and `sys.stderr`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (Pytest)                    | JavaScript / TypeScript (Vitest)   |
+------------------------------+------------------------------------+------------------------------------+
| Test Declaration             | `def test_feature():`              | `test("feature", () => { ... })`   |
| Assertion Syntax             | Plain `assert a == b`              | `expect(a).toBe(b)`                |
| Setup & Teardown             | `@pytest.fixture` with `yield`     | `beforeEach()` / `afterEach()`     |
| Dependency Injection         | Fixture names in test parameters   | Context objects or global hooks    |
| Table-Driven Tests           | `@pytest.mark.parametrize(...)`    | `test.each([ ... ])`               |
| Exception Testing            | `with pytest.raises(Err, match=..):`| `expect(() => fn()).toThrow(Err)`  |
| Temporary Filesystem         | `tmp_path` fixture (`Path`)        | Manual `fs.mkdtemp`                |
| Environment Variable Mocking | `monkeypatch.setenv("K", "V")`     | `vi.stubEnv("K", "V")`             |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Testing Nuances:
1. In Jest/Vitest, tests are registered as callbacks: `it("should calculate", () => ...)`.
   In Pytest, any function prefixed with `test_` is automatically discovered by
   convention without an enclosing callback wrapper.
2. In Pytest, setup and teardown are coupled in the same fixture function via `yield`,
   preventing variable leaks between `beforeEach` and `afterEach`.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Pytest Import Hook & AST Rewriting:
   - Pytest installs a custom `MetaPathFinder` in `sys.meta_path`.
   - When importing a test file, it parses the source code into an AST and traverses
     all `Assert` nodes.
   - It rewrites `assert left == right` into an expanded bytecode structure that
     evaluates `left` and `right`, records intermediate sub-expressions into local
     variables, and formats rich comparison diffs if the boolean test fails.

2. Fixture Dependency Graph Resolution:
   - Pytest constructs a Directed Acyclic Graph (DAG) of fixtures before executing
     each test function.
   - Fixtures can depend on other fixtures (e.g. `client` depends on `db_session`,
     which depends on `db_engine`).
   - Pytest topological-sorts the fixture graph, executing setup in dependency order
     and unwinding teardown in exact reverse order.


============================================================
4. COMMON GOTCHAS
============================================================

1. Modifying State in Higher-Scoped Fixtures (Session/Module):
   - If a `session`-scoped fixture returns a mutable object (e.g. a list or DB session),
     and Test A mutates it, Test B receives dirty state!
   - Rule: Higher-scoped fixtures must only provide immutable or read-only resources.

2. Fixture Name Misspelling:
   - Pytest resolves fixtures by exact argument name.
   - If a test expects `db_session` but writes `def test_user(session):`, Pytest
     raises `FixtureLookupError: fixture 'session' not found`.

3. Forgetting Context Manager on `pytest.raises`:
   - Writing `pytest.raises(ValueError, func())` calls `func()` BEFORE `pytest.raises`
     is entered, failing the test!
   - Always use the context manager: `with pytest.raises(ValueError): func()`.

4. Yield Fixture Without Teardown Guard:
   - If an exception occurs in the setup code BEFORE `yield`, the teardown code
     after `yield` is NEVER executed!
   - Place risky setup code inside a `try...finally` block if teardown must always run.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does Pytest's fixture system work, and how does it compare to xUnit setUp/tearDown?"
Script:
"Unlike legacy xUnit or `unittest` which rely on class inheritance and monolithic `setUp()`
and `tearDown()` methods, Pytest implements a modular dependency injection architecture.
Fixtures are declared as standalone functions decorated with `@pytest.fixture`. Test functions
simply declare the fixture names they need as arguments, and Pytest builds and resolves
a Directed Acyclic Graph of dependencies. For lifecycle management, Pytest uses the `yield`
fixture pattern: code before `yield` performs setup, the yielded value is injected into
the test, and code after `yield` executes teardown unconditionally, mirroring Python's
context manager pattern."

Q2: "What is AST assertion rewriting in Pytest and how does it improve debugging?"
Script:
"In standard Python, executing `assert a == b` simply raises an uninformative `AssertionError`
if the expression evaluates to False. Frameworks like `unittest` worked around this by
introducing dozens of assertion methods like `self.assertEqual` or `self.assertDictEqual`.
Pytest solves this at the language level by installing an import hook that intercepts test
modules and rewrites the Abstract Syntax Tree (AST) before compilation. It transforms simple
`assert` expressions to capture intermediate values and compute detailed structural diffs.
When an assertion fails, Pytest prints the exact evaluation steps, dict/list diffs, and
variable values without requiring custom assertion APIs."

Q3: "How does @pytest.mark.parametrize simplify testing complex business logic?"
Script:
"`@pytest.mark.parametrize` enables table-driven testing by running the same test function
across multiple sets of arguments and expectations. Each parameter tuple generates a separate,
uniquely identified test case in the test execution report. If one scenario fails, the other
test cases continue running independently, pinpointing exact boundary or edge-case failures.
Furthermore, chaining multiple `@pytest.mark.parametrize` decorators computes a full
Cartesian product of test inputs, providing exhaustive test coverage across multi-variable
permutation matrices."
"""

import sys
import pytest

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# DOMAIN CLASSES FOR TESTING
# ============================================================

class BankAccount:
    """Simple domain class to test with fixtures and parametrization."""
    def __init__(self, owner: str, balance: float = 0.0):
        if balance < 0:
            raise ValueError("Initial balance cannot be negative")
        self.owner = owner
        self.balance = float(balance)

    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        return self.balance

    def withdraw(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        return self.balance


# ============================================================
# PYTEST FIXTURES
# ============================================================

@pytest.fixture
def empty_account() -> BankAccount:
    """Function-scoped fixture providing an account with zero balance."""
    return BankAccount("Alice", 0.0)


@pytest.fixture
def funded_account() -> BankAccount:
    """Function-scoped fixture providing an account with $100 balance."""
    return BankAccount("Bob", 100.0)


@pytest.fixture
def managed_transaction_account():
    """Demonstrates the YIELD fixture pattern with setup and teardown."""
    # Setup phase
    account = BankAccount("Charlie", 500.0)
    audit_events = ["SETUP_OPENED"]

    # Yield control and resource to test function
    yield account, audit_events

    # Teardown phase (guaranteed cleanup)
    audit_events.append("TEARDOWN_CLOSED")


# ============================================================
# PYTEST TEST FUNCTIONS (Discovered by pytest runner)
# ============================================================

def test_initial_account_state(empty_account: BankAccount):
    """Test standard initial state."""
    assert empty_account.owner == "Alice"
    assert empty_account.balance == 0.0


def test_deposit(empty_account: BankAccount):
    """Test deposit increases balance."""
    new_bal = empty_account.deposit(50.0)
    assert new_bal == 50.0
    assert empty_account.balance == 50.0


def test_withdrawal(funded_account: BankAccount):
    """Test withdrawal decreases balance."""
    new_bal = funded_account.withdraw(40.0)
    assert new_bal == 60.0
    assert funded_account.balance == 60.0


def test_insufficient_funds_raises(funded_account: BankAccount):
    """Test exception raising via pytest.raises with regex matching."""
    with pytest.raises(ValueError, match=r"Insufficient funds"):
        funded_account.withdraw(200.0)


@pytest.mark.parametrize(
    "initial, deposit_amt, expected_total",
    [
        (0.0, 10.0, 10.0),
        (50.0, 25.0, 75.0),
        (100.0, 0.50, 100.50),
    ],
)
def test_parametrized_deposits(initial: float, deposit_amt: float, expected_total: float):
    """Table-driven test using @pytest.mark.parametrize."""
    acc = BankAccount("Tester", initial)
    acc.deposit(deposit_amt)
    assert acc.balance == expected_total


def run_tests():
    """Runs all test cases using pytest programmatic runner."""
    exit_code = pytest.main(["-q", __file__])
    assert exit_code == 0, f"Pytest suite failed with code {exit_code}"


if __name__ == "__main__":
    run_tests()
    print("02_pytest_fundamentals_and_fixtures.py tests passed!")
