"""
03_mocking_and_external_services.py

============================================================
1. CONCEPT
============================================================

Unit testing requires rigorous isolation of code under test from external side
effects (HTTP endpoints, database connections, filesystems, and clocks) using
Python's standard library `unittest.mock`:

1. Mock vs MagicMock vs AsyncMock:
   - `Mock`: Core callable test double that records call counts, arguments, and returns values.
   - `MagicMock`: Subclass of `Mock` pre-configured with implementations for all
     Python Data Model dunder methods (`__enter__`, `__exit__`, `__iter__`, `__len__`, `__getitem__`).
     Ideal for mocking context managers, file streams, and collections.
   - `AsyncMock` (Python 3.8+): Specifically designed to mock asynchronous coroutine functions
     (`async def`), returning awaitables when invoked.

2. Controlling Mock Behavior:
   - `return_value`: The static value returned when the mock is called.
   - `side_effect`:
     - An exception class or instance: raises the exception when invoked.
     - An iterable (e.g. `[10, 20, 30]`): returns sequential items on consecutive calls.
     - A custom callable: dynamically computes and returns a result based on input args.

3. The `@patch` Context Manager & Decorator:
   - Temporarily intercepts and replaces a target attribute in a module namespace.
   - Automatically restores the original attribute when the `with` block exits or
     the decorated test function finishes.
   - `patch.object(target_instance, "method_name")`: Patches an attribute directly on an object.
   - `patch.dict(target_dict, {"KEY": "val"})`: Safely mutates dictionaries (e.g. `os.environ`).

4. The Golden Rule of Mocking ("Where to Patch"):
   - "Patch where an object is LOOKED UP, not where it is DEFINED!"
   - If `service.py` executes `from payment_gateway import process_charge`, the name
     `process_charge` is bound inside `service`'s namespace. Patching
     `payment_gateway.process_charge` will NOT affect `service.py`. You must patch
     `service.process_charge`.

5. Autospeccing (`autospec=True` / `spec`):
   - Standard mocks accept ANY attribute access and ANY argument signature without complaint.
   - Setting `spec=RealClass` or `@patch(..., autospec=True)` forces the mock to mirror
     the real class/function interface, raising `AttributeError` or `TypeError` if non-existent
     methods are called or arguments mismatch.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (unittest.mock)             | JavaScript / TypeScript (Vitest)   |
+------------------------------+------------------------------------+------------------------------------+
| Mock Function                | `Mock()` / `MagicMock()`           | `vi.fn()` / `jest.fn()`            |
| Spy / Method Replacement     | `@patch.object(obj, "method")`     | `vi.spyOn(obj, "method")`          |
| Module Namespace Mocking     | `@patch("module.function_name")`   | `vi.mock("./module", () => ...)`   |
| Sequential Returns           | `mock.side_effect = [val1, val2]`  | `fn.mockReturnValueOnce(val1)...`  |
| Async Mock                   | `AsyncMock()`                      | `vi.fn().mockResolvedValue(...)`   |
| Call Verification            | `mock.assert_called_once_with(...)`| `expect(fn).toHaveBeenCalledWith()`|
| Call Count Check             | `mock.call_count == 2`             | `expect(fn).toHaveBeenCalledTimes(2)`|
| File I/O Mocking             | `mock_open(read_data="...")`       | `vi.mock("fs", ...)`               |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Mocking Nuances:
1. In JS module systems (ESM), mocking modules is evaluated before imports via
   hoisting (`vi.mock`). In Python, `@patch` dynamically alters the target module's
   `__dict__` dictionary at runtime during test execution.
2. In Python, forgetting to set `spec=True` can create insidious false-positive tests
   where a test passes even though the production code calls a non-existent method!


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Dynamic Module Dictionary Interception:
   - When `@patch("app.services.fetch_data")` runs:
     1. It imports or retrieves `app.services` from `sys.modules`.
     2. It saves the original attribute: `original = app.services.__dict__["fetch_data"]`.
     3. It rebinds the attribute: `app.services.__dict__["fetch_data"] = MagicMock()`.
     4. Upon test completion, `patch`'s `__exit__` restores:
        `app.services.__dict__["fetch_data"] = original`.

2. Call Tracking Representation (`call` object):
   - Every call to a mock appends a `_Call` tuple `(name, args, kwargs)` to `mock.mock_calls`.
   - `assert_called_with` compares expected positional and keyword arguments using standard
     equality against the last entry in `mock.call_args`.


============================================================
4. COMMON GOTCHAS
============================================================

1. The "Where to Patch" Mistake:
   - In `order_service.py`: `from datetime import datetime`.
   - Test runs `@patch("datetime.datetime.now")` -> Fails to intercept `order_service`!
   - Correct patch target: `@patch("order_service.datetime.now")`.

2. The Silent Typo Trap (Why You Need `spec=True`):
   - Suppose `mailer.send_email()` is renamed to `mailer.send_notification()`.
   - If test uses an unspecced `mock_mailer = Mock()`, calling `mock_mailer.send_email()`
     silently succeeds and returns another Mock! The test passes while production breaks.
   - Fix: Use `Mock(spec=Mailer)` or `patch(..., autospec=True)`.

3. Leaking Patches:
   - Using `patcher = patch(...)` and calling `patcher.start()` without a corresponding
     `patcher.stop()` in teardown contaminates all subsequent tests in the process.
   - Always use the context manager (`with patch(...):`) or pytest's `monkeypatch` fixture.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the rule 'patch where an object is looked up, not where it is defined'."
Script:
"When Python imports a function using `from module_a import helper_fn`, it creates a new
binding named `helper_fn` in the importing module's local namespace (`module_b.__dict__`).
If you patch `module_a.helper_fn`, `module_b` will continue executing its already-bound
local reference completely unaffected. Therefore, you must always patch the reference where
the code under test looks it up—meaning `@patch('module_b.helper_fn')` rather than the
module where `helper_fn` was originally declared."

Q2: "What is the difference between Mock and MagicMock, and when is AsyncMock needed?"
Script:
"`MagicMock` is a subclass of `Mock` that comes with pre-configured implementations of all
Python dunder methods—such as `__enter__` and `__exit__` for context managers, `__len__`,
`__getitem__`, and `__iter__`. In general application development, `MagicMock` is the default
choice whenever mocking objects that interact with Python's data model protocols. `AsyncMock`
was introduced in Python 3.8 specifically for asynchronous code; when invoked, it returns an
awaitable coroutine, which is essential for testing async functions in FastAPI or asyncio
without raising `TypeError: object can't be used in 'await' expression`."

Q3: "Why is autospeccing critical when mocking in Python?"
Script:
"By default, Python `Mock` objects are completely dynamic: accessing any attribute or calling
any method automatically creates and returns a new Mock instance without validation. If a
developer refactors a method name or changes a function's parameter list, an un-specced mock
will silently accept the old method call, causing the test suite to pass with false confidence
while production code crashes. By enabling `autospec=True` on `@patch` or specifying `spec=TargetClass`,
the mock strictly enforces the real object's API surface. Any calls to non-existent methods
or mismatched arguments immediately raise `AttributeError` or `TypeError` during test runs."
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, call, mock_open, patch

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# DOMAIN COMPONENTS UNDER TEST
# ============================================================

class EmailSender:
    """Production email sending service interface."""
    def send_email(self, recipient: str, subject: str, body: str) -> bool:
        raise ConnectionError("Cannot reach real SMTP server in unit test!")


class UserService:
    """Business logic service depending on EmailSender."""
    def __init__(self, email_sender: EmailSender):
        self._email_sender = email_sender

    def register_user(self, email: str, username: str) -> bool:
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        # Send confirmation email
        return self._email_sender.send_email(
            recipient=email,
            subject="Welcome!",
            body=f"Hello {username}, welcome to Apex!",
        )


def query_remote_database(query_str: str) -> list[dict]:
    """Module-level function simulating network DB query."""
    raise ConnectionError("Live DB cluster unreachable!")


def fetch_active_user_names() -> list[str]:
    """Function under test that depends on query_remote_database."""
    records = query_remote_database("SELECT username FROM users WHERE active = true")
    return [r["username"] for r in records]


def run_tests():
    # ============================================================
    # 1. Mock vs MagicMock CAPABILITIES
    # ============================================================

    # Plain Mock: Basic return values and call assertions
    calculator_mock = Mock()
    calculator_mock.multiply.return_value = 50

    res = calculator_mock.multiply(5, 10)
    assert res == 50
    assert calculator_mock.multiply.call_count == 1
    calculator_mock.multiply.assert_called_once_with(5, 10)

    # MagicMock: Context Manager protocol (__enter__ and __exit__)
    magic_resource = MagicMock()
    with magic_resource as res:
        assert res is not None

    magic_resource.__enter__.assert_called_once()
    magic_resource.__exit__.assert_called_once()


    # ============================================================
    # 2. CONTROLLING BEHAVIOR WITH side_effect
    # ============================================================

    # side_effect with exception raising
    error_mock = Mock()
    error_mock.side_effect = TimeoutError("Network timed out")

    caught_timeout = False
    try:
        error_mock()
    except TimeoutError:
        caught_timeout = True
    assert caught_timeout is True

    # side_effect with sequential values (Iterable)
    sequence_mock = Mock()
    sequence_mock.side_effect = ["first_token", "second_token", "third_token"]

    assert sequence_mock() == "first_token"
    assert sequence_mock() == "second_token"
    assert sequence_mock() == "third_token"

    # side_effect with dynamic callable
    dynamic_mock = Mock()
    dynamic_mock.side_effect = lambda x, y: x * y + 1
    assert dynamic_mock(3, 4) == 13


    # ============================================================
    # 3. INTERFACE VERIFICATION WITH spec
    # ============================================================

    # Spec prevents calling non-existent methods
    specced_mock = Mock(spec=EmailSender)
    specced_mock.send_email.return_value = True

    service = UserService(specced_mock)
    success = service.register_user("alice@apex.internal", "alice")

    assert success is True
    specced_mock.send_email.assert_called_once_with(
        recipient="alice@apex.internal",
        subject="Welcome!",
        body="Hello alice, welcome to Apex!",
    )

    # Calling a non-existent method on a specced mock raises AttributeError
    non_existent_caught = False
    try:
        specced_mock.non_existent_method()
    except AttributeError:
        non_existent_caught = True
    assert non_existent_caught is True


    # ============================================================
    # 4. PATCHING MODULE NAMESPACES ("WHERE TO PATCH")
    # ============================================================

    # Patch query_remote_database in current module's namespace
    target_patch_name = f"{__name__}.query_remote_database"

    mock_db_data = [{"username": "alice"}, {"username": "bob"}]
    with patch(target_patch_name, return_value=mock_db_data) as patched_db:
        user_names = fetch_active_user_names()
        assert user_names == ["alice", "bob"]
        patched_db.assert_called_once_with("SELECT username FROM users WHERE active = true")


    # ============================================================
    # 5. ASYNC MOCKING (AsyncMock)
    # ============================================================

    async def run_async_test():
        async_service_mock = AsyncMock()
        async_service_mock.fetch_async_payload.return_value = {"status": "ok"}

        # Awaiting the async mock returns the value cleanly
        result = await async_service_mock.fetch_async_payload("session_123")
        assert result == {"status": "ok"}
        async_service_mock.fetch_async_payload.assert_awaited_once_with("session_123")

    asyncio.run(run_async_test())


    # ============================================================
    # 6. MOCKING FILESYSTEM (mock_open)
    # ============================================================

    fake_file_content = "api_key=secret_12345\nenv=staging"
    with patch("builtins.open", mock_open(read_data=fake_file_content)) as mocked_file:
        with open("/etc/config.env", mode="r") as f:
            content_read = f.read()

        assert content_read == fake_file_content
        mocked_file.assert_called_once_with("/etc/config.env", mode="r")


    # ============================================================
    # 7. PATCHING DICTIONARIES (patch.dict for os.environ)
    # ============================================================

    test_env = {"CLUSTER_ID": "cls_999", "DEBUG_MODE": "1"}
    with patch.dict(os.environ, test_env, clear=False):
        assert os.environ.get("CLUSTER_ID") == "cls_999"
        assert os.environ.get("DEBUG_MODE") == "1"

    # Restores original environment state outside with block
    assert "CLUSTER_ID" not in os.environ


if __name__ == "__main__":
    run_tests()
    print("03_mocking_and_external_services.py tests passed!")
