"""
01_exceptions_and_custom_errors.py

============================================================
1. CONCEPT
============================================================

Error handling in Python is built upon class-based exceptions, structured control
clauses (`try / except / else / finally`), explicit exception chaining, and the
Pythonic EAFP ("Easier to Ask for Forgiveness than Permission") design pattern:

1. The Complete try Block Lifecycle:
   - `try`: Encloses operations that might raise an exception. (Best practice: keep
     the `try` block as minimal as possible).
   - `except ExceptionType as err`: Intercepts matching exceptions. Can handle multiple
     exceptions via a tuple: `except (KeyError, ValueError) as err:`.
   - `else`: Executes ONLY if the `try` block completed without raising ANY exception.
     Separates successful computation logic from failure handling.
   - `finally`: Guarantees execution under ALL circumstances (whether an exception
     occurred, was caught, or was unhandled, or even if `return` was called).

2. Exception Hierarchy Architecture:
   - `BaseException`: The ultimate root of all exceptions.
     - `SystemExit`: Raised by `sys.exit()`.
     - `KeyboardInterrupt`: Raised when user presses Ctrl+C.
     - `GeneratorExit`: Raised when a generator is closed.
     - `Exception`: Root for all standard, non-system-exiting application exceptions.
   - Golden Rule: Never catch `BaseException` or use bare `except:`! Always catch
     `Exception` or specific subclasses.

3. Custom Exception Hierarchies:
   - Production applications define a domain base exception inheriting from `Exception`:
     `class DomainError(Exception): pass`.
   - Subclasses model specific failure domains (`NotFoundError`, `ValidationError`, `AuthError`),
     enriching exceptions with structured metadata (`error_code`, `status_code`, `details`).

4. Exception Chaining (`raise ... from` - PEP 3134):
   - Explicit chaining: `raise ServiceError("Failed") from db_err`.
     Attaches the original exception to `__cause__` and outputs both tracebacks.
   - Suppressing chaining: `raise ServiceError("Sanitized") from None`.
     Hides low-level internal stack traces (e.g. database credentials) from users.

5. Modern Exception Enhancements (Python 3.11+):
   - Exception Notes (PEP 678): `err.add_note("Context info")` attaches debugging
     metadata directly to existing exceptions without altering their type or message.
   - Exception Groups & `except*` (PEP 654): Groups multiple concurrent exceptions
     raised by task runners (such as `asyncio.TaskGroup`).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Throwing Errors              | `raise ValueError("msg")`          | `throw new Error("msg")`           |
| What can be thrown           | Only classes deriving BaseException| Any type (strings, numbers, objects)|
| Catch Block Type Filtering   | `except (KeyError, ValueError):`   | Single `catch (e)` (manual `instanceof`)|
| Success Branch               | `else:` (runs if no exception)     | No direct language equivalent      |
| Guaranteed Teardown          | `finally:`                         | `finally { ... }`                  |
| Exception Chaining           | `raise NewError() from orig_err`   | `new Error("msg", { cause: orig })`|
| Attaching Debug Context      | `err.add_note("text")` (3.11+)     | Manual property assignment         |
| Multiple Concurrent Errors   | `ExceptionGroup` + `except*`       | `AggregateError`                   |
| Programming Style            | EAFP (try/except)                  | LBYL (`if (typeof x !== 'undefined')`)|
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Error Handling Nuance:
1. JavaScript allows `throw "some error"` or `throw 404`. Python enforces strong typing:
   `raise 404` raises `TypeError: exceptions must derive from BaseException`.
2. Python's `else` clause eliminates the anti-pattern of wrapping both the risky
   code and post-processing code in the same `try` block, preventing accidental
   masking of secondary bugs.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Zero-Cost Exception Handling (Python 3.11+):
   - Historically, entering a `try` block executed bytecode instructions to set up
     an exception handler frame (`SETUP_FINALLY`).
   - In Python 3.11+, CPython uses static exception tables generated at compile time.
   - Entering a `try` block costs zero bytecode instructions and zero CPU cycles.
   - A performance penalty is incurred ONLY when an exception is actually raised,
     making EAFP significantly faster than manual LBYL conditional checks in normal paths.

2. Traceback Object Construction:
   - When `raise` executes, CPython traverses the C call stack frames, allocating
     a linked list of `PyTracebackObject` structs.
   - Each traceback node stores pointers to `tb_frame`, `tb_lasti` (last instruction),
     and `tb_lineno`.

3. Exception Chaining Storage:
   - `raise exc from cause` stores `cause` inside `exc.__cause__` and sets
     `exc.__suppress_context__ = True`.
   - If an exception occurs while handling another exception without `from`, CPython
     automatically sets `exc.__context__` to the active exception (implicit chaining).


============================================================
4. COMMON GOTCHAS
============================================================

1. The Bare `except:` Anti-Pattern:
   - Writing `try: ... except: pass` catches `KeyboardInterrupt` and `SystemExit`,
     preventing the user from terminating the process with Ctrl+C or Docker shutdown signals!
   - Always catch `except Exception:` at minimum.

2. Over-broad Exception Catching in `try`:
   - Putting 20 lines of code inside `try:` makes it impossible to know which line
     triggered a `ValueError` or `KeyError`.
   - Rule: Keep `try` to the exact statement that can fail; put following logic in `else:`.

3. Re-raising Exceptions Improperly:
   - Correct: `raise` (preserves existing traceback).
   - Anti-pattern: `except Exception as e: raise e` (overwrites the traceback origin line!).

4. Modifying Return Values Inside `finally`:
   - If a `finally` block executes an explicit `return` statement, it will swallow
     and overwrite any exception raised inside the `try` block!


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the Python try/except/else/finally construct and the purpose of the else clause."
Script:
"Python's exception handling statement consists of four distinct clauses. The `try` block
encapsulates the specific operation that might fail. The `except` block catches and handles
targeted exception classes. The `else` block runs only if the `try` block finishes successfully
without raising any exceptions. This is invaluable in production code because it lets us isolate
the risky operation in the `try` block while keeping post-success business logic in the `else`
block, ensuring we don't inadvertently catch unexpected exceptions from our own post-processing
logic. Finally, the `finally` block executes unconditionally, guaranteeing resource cleanup
regardless of whether exceptions were raised, caught, or unhandled."

Q2: "What is exception chaining in Python and when should you use 'from None'?"
Script:
"Exception chaining, introduced in PEP 3134, allows developers to wrap low-level exceptions
in high-level domain exceptions while preserving root-cause context. By writing `raise
AppServiceError('Action failed') from original_err`, Python explicitly links the original
error to the `__cause__` attribute of the new exception, displaying both tracebacks in logs
for debugging. Conversely, writing `from None` explicitly sets `__suppress_context__ = True`,
which suppresses the original traceback display. This is used in production APIs to prevent
internal implementation details—such as database connection strings, table schemas, or third-party
credentials—from leaking to external consumers."

Q3: "Compare Python's EAFP philosophy with JavaScript's LBYL approach."
Script:
"LBYL stands for 'Look Before You Leap'—testing preconditions with `if` statements before
performing an operation, which is standard in JavaScript and C. EAFP stands for 'Easier to
Ask for Forgiveness than Permission'—attempting the operation directly inside a `try` block
and catching the exception if it fails. In Python, EAFP is heavily favored for two reasons:
first, since Python 3.11's zero-cost exception tables, happy-path `try` blocks execute with
zero overhead, avoiding duplicate lookups. Second, EAFP prevents Time-of-Check to Time-of-Use
(TOCTOU) race conditions in concurrent and filesystem operations, such as checking if a file
exists before reading it versus opening it directly and catching `FileNotFoundError`."
"""

import sys
import types

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# CUSTOM DOMAIN EXCEPTION HIERARCHY
# ============================================================

class AppError(Exception):
    """Base domain exception for all application errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }


class EntityNotFoundError(AppError):
    """Raised when an entity is missing."""
    def __init__(self, entity_name: str, entity_id: str | int):
        msg = f"{entity_name} with identifier '{entity_id}' does not exist."
        super().__init__(msg, error_code="ENTITY_NOT_FOUND", status_code=404)
        self.entity_name = entity_name
        self.entity_id = entity_id


class InsufficientFundsError(AppError):
    """Raised when balance is insufficient."""
    def __init__(self, current_balance: float, requested: float):
        msg = f"Insufficient funds: available {current_balance}, requested {requested}."
        super().__init__(msg, error_code="INSUFFICIENT_FUNDS", status_code=400)
        self.current_balance = current_balance
        self.requested = requested


def run_tests():
    # ============================================================
    # 1. THE COMPLETE try / except / else / finally LIFECYCLE
    # ============================================================

    lifecycle_log = []

    def execute_flow(trigger_error: bool):
        nonlocal lifecycle_log
        lifecycle_log.clear()
        try:
            lifecycle_log.append("try_start")
            if trigger_error:
                raise ValueError("simulated_failure")
            lifecycle_log.append("try_end")
        except ValueError:
            lifecycle_log.append("except_caught")
        else:
            lifecycle_log.append("else_success")
        finally:
            lifecycle_log.append("finally_cleanup")

    # Case A: Success path -> executes try, else, finally
    execute_flow(trigger_error=False)
    assert lifecycle_log == [
        "try_start",
        "try_end",
        "else_success",
        "finally_cleanup",
    ]

    # Case B: Error path -> executes try, except, finally (else is skipped)
    execute_flow(trigger_error=True)
    assert lifecycle_log == [
        "try_start",
        "except_caught",
        "finally_cleanup",
    ]


    # ============================================================
    # 2. MULTIPLE EXCEPTION FILTERING IN TUPLE
    # ============================================================

    def parse_and_lookup(data: dict, key: str, index: int):
        try:
            val_str = data[key]
            num = int(val_str)
            return [10, 20, 30][index] / num
        except (KeyError, IndexError, ValueError, ZeroDivisionError) as err:
            return f"handled: {type(err).__name__}"

    assert parse_and_lookup({}, "missing", 0) == "handled: KeyError"
    assert parse_and_lookup({"k": "1"}, "k", 99) == "handled: IndexError"
    assert parse_and_lookup({"k": "not_a_num"}, "k", 0) == "handled: ValueError"
    assert parse_and_lookup({"k": "0"}, "k", 0) == "handled: ZeroDivisionError"
    assert parse_and_lookup({"k": "2"}, "k", 1) == 10.0


    # ============================================================
    # 3. EXCEPTION CHAINING (raise ... from cause)
    # ============================================================

    # Explicit chaining sets __cause__
    caught_app_error = None
    try:
        try:
            raise KeyError("db_connection_lost")
        except KeyError as db_err:
            raise EntityNotFoundError("Customer", 42) from db_err
    except EntityNotFoundError as err:
        caught_app_error = err

    assert caught_app_error is not None
    assert caught_app_error.status_code == 404
    assert isinstance(caught_app_error.__cause__, KeyError)
    assert str(caught_app_error.__cause__) == "'db_connection_lost'"

    # Suppressed chaining sets __suppress_context__ = True
    suppressed_error = None
    try:
        try:
            raise PermissionError("secret_db_credentials_invalid")
        except PermissionError:
            raise AppError("Authentication failed", error_code="AUTH_FAILED", status_code=401) from None
    except AppError as err:
        suppressed_error = err

    assert suppressed_error is not None
    assert suppressed_error.__cause__ is None
    assert suppressed_error.__suppress_context__ is True


    # ============================================================
    # 4. CUSTOM DOMAIN EXCEPTION STRUCTURE
    # ============================================================

    not_found = EntityNotFoundError("Invoice", "INV-2026-001")
    assert isinstance(not_found, AppError)
    assert isinstance(not_found, Exception)
    assert not_found.status_code == 404
    assert not_found.to_dict() == {
        "error": "ENTITY_NOT_FOUND",
        "message": "Invoice with identifier 'INV-2026-001' does not exist.",
        "status_code": 404,
    }

    insufficient = InsufficientFundsError(current_balance=25.0, requested=100.0)
    assert insufficient.status_code == 400
    assert insufficient.error_code == "INSUFFICIENT_FUNDS"


    # ============================================================
    # 5. PYTHON 3.11+ EXCEPTION NOTES (PEP 678)
    # ============================================================

    test_err = ValueError("Invalid payload format")
    # Attach diagnostic note
    test_err.add_note("Failed during request ID: req_99214")
    test_err.add_note("User IP: 192.168.1.100")

    assert hasattr(test_err, "__notes__")
    assert test_err.__notes__ == [
        "Failed during request ID: req_99214",
        "User IP: 192.168.1.100",
    ]


    # ============================================================
    # 6. EAFP VS LBYL VERIFICATION
    # ============================================================

    # EAFP pattern: Try to convert or fall back without pre-checking regex/isdigit
    def parse_port_eafp(port_val: str, default: int = 8080) -> int:
        try:
            return int(port_val)
        except (ValueError, TypeError):
            return default

    assert parse_port_eafp("3000") == 3000
    assert parse_port_eafp("invalid") == 8080
    assert parse_port_eafp(None) == 8080


if __name__ == "__main__":
    run_tests()
    print("01_exceptions_and_custom_errors.py tests passed!")
