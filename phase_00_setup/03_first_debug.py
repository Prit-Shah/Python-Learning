"""
03_first_debug.py

============================================================
1. CONCEPT
============================================================

Debugging in Python spans interactive step-debugging, programmatic call-stack
inspection, custom traceback extraction, and defensive verification:

1. The Modern Breakpoint Hook (PEP 553):
   - Python 3.7+ introduced the `breakpoint()` built-in function.
   - Calls `sys.breakpointhook()`, which defaults to importing `pdb` and calling
     `pdb.set_trace()`.
   - Environment Variable Override (`PYTHONBREAKPOINT`):
     - `PYTHONBREAKPOINT=0`: Completely disables all `breakpoint()` calls in production
       with zero overhead.
     - `PYTHONBREAKPOINT=ipdb.set_trace`: Drops into IPython debugger automatically.

2. CPython Stack Frame Introspection (`sys._getframe`):
   - At runtime, every active function execution is represented by a `frame` object.
   - Key Frame Attributes:
     - `frame.f_code.co_name`: Current function name.
     - `frame.f_lineno`: Current executing line number.
     - `frame.f_locals`: Local variables dictionary snapshot.
     - `frame.f_back`: Pointer to the caller's stack frame (enables walking the stack).

3. Traceback Formatting & Exception Analysis:
   - The standard library `traceback` module parses and formats active exceptions:
     `traceback.format_exc()`, `traceback.extract_tb()`.
   - `sys.exc_info()` returns a 3-tuple `(type, value, traceback)` for the currently
     handled exception.

4. The Assert Statement & Optimization Flag (-O):
   - `assert <expression>, <message>`: Evaluates expression; if false, raises `AssertionError`.
   - CRITICAL WARNING: When Python is executed with the `-O` (optimize) flag, CPython's
     bytecode compiler completely strips out all `assert` statements!
   - Rule: Never use `assert` for user input validation or security gates.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| Breakpoint Statement         | `breakpoint()`                     | `debugger;`                        |
| Disabling Breakpoints        | `PYTHONBREAKPOINT=0`               | Ignored when DevTools closed       |
| Stack Trace Inspection       | `traceback.format_exc()`           | `err.stack` / `console.trace()`    |
| Stack Frame Object           | `sys._getframe()`                  | V8 Stack Trace API (`Error.prepareStackTrace`)|
| Interactive Debugger         | `pdb` / `ipdb` / `pdb++`           | Node.js `--inspect` / Chrome DevTools|
| Stripped Assertions          | `assert` stripped in `python -O`   | No built-in stripped keyword       |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Debugging Differences:
- In JavaScript, `debugger;` is a language keyword. In Python, `breakpoint()` is a
  built-in callable function routing through `sys.breakpointhook`, making it
  dynamically pluggable and reconfigurable.
- JavaScript `err.stack` is a formatted string. Python exposes live `traceback` objects
  pointing to the exact linked list of `frame` objects across the call stack.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyFrameObject Architecture:
   - Stack frames in CPython are represented by `PyFrameObject`:
     ```c
     struct _frame {
         PyObject_VAR_HEAD
         struct _frame *f_back;      // Previous frame in call stack
         PyCodeObject *f_code;       // Bytecode container
         PyObject *f_localsplus[1];  // Fast locals + evaluation stack
         int f_lineno;               // Current line number
         ...
     };
     ```
   - Tracing overhead: Setting a trace hook via `sys.settrace()` causes CPython to
     switch from fast opcode evaluation into trace mode, executing the callback
     on every single bytecode instruction line.

2. Bytecode Generation for `assert`:
   - `assert condition, message` compiles to:
     - `POP_JUMP_FORWARD_IF_TRUE` -> skips error construction.
     - `LOAD_GLOBAL AssertionError`, `LOAD_CONST message`, `CALL`, `RAISE_VARARGS`.
   - With `python -O`: The compiler completely bypasses this AST node, generating
     zero bytecode instructions!


============================================================
4. COMMON GOTCHAS
============================================================

1. Using Assert for Business Logic / Validation:
   - Writing `assert user.is_authenticated, "Unauthorized"`
   - If deployed with `python -O app.py`, the assertion is completely removed,
     leaving the endpoint completely unprotected!
   - Fix: Always use explicit conditional checks: `if not user.is_authenticated: raise PermissionError()`.

2. Catch-All Exception Swallowing:
   - Anti-pattern:
     ```python
     try:
         complex_calculation()
     except Exception:
         pass  # Swallows typos, NameErrors, and bugs during debugging!
     ```
   - Always log or inspect tracebacks using `traceback.format_exc()`.

3. Leaving Breakpoints in Committed Code:
   - Leaving `breakpoint()` in code deployed to a non-interactive server causes the
     application worker to hang indefinitely waiting for stdin!

4. Tuple Syntax Trap with Assert:
   - Writing `assert (x > 0, "x must be positive")`
   - In Python, a non-empty tuple is always TRUTHY!
   - This assertion NEVER fails, even if `x = -100`!
   - Fix: Omit parentheses: `assert x > 0, "x must be positive"`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does the breakpoint() built-in work in Python 3.7+, and how can it be configured?"
Script:
"`breakpoint()` is a built-in function introduced in PEP 553 that delegates to
`sys.breakpointhook()`. By default, it imports `pdb` and starts an interactive debugging
session at the point of invocation. Its primary strength lies in its configurability:
by setting the environment variable `PYTHONBREAKPOINT=0`, all breakpoint calls throughout
the codebase are disabled with zero runtime performance cost. In local development, it can
be redirected to third-party debuggers, such as `PYTHONBREAKPOINT=ipdb.set_trace` or
debugpy for remote VS Code debugging, without modifying application source code."

Q2: "Why is it an anti-pattern to use Python assert statements for input validation or business rules?"
Script:
"In Python, the `assert` statement is designed exclusively for internal invariant checks
and unit testing. When the Python interpreter is launched with the `-O` optimization flag,
the bytecode compiler completely ignores and strips all `assert` statements from the
compiled `.pyc` files. If an application relies on `assert` to validate user input, authentication,
or permissions, running in optimized mode will silently eliminate those checks, creating
catastrophic security vulnerabilities. Production validation must always use explicit `if`
conditions that raise standard exceptions like `ValueError` or `PermissionError`."

Q3: "How can you programmatically inspect the call stack and identify a calling function in Python?"
Script:
"Python provides direct stack introspection through the `sys._getframe()` API and the
standard library `inspect` module. Calling `sys._getframe(1)` retrieves the frame object of
the immediate caller. From this frame, we can inspect `f_code.co_name` to retrieve the
calling function's name, `f_lineno` for the line number, and `f_locals` for its local variable
dictionary. Additionally, the `traceback` module allows extracting formatted stack traces
via `traceback.extract_stack()`, which is invaluable for building custom telemetry, logging,
and debugging utilities."
"""

import sys
import traceback

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def helper_function():
    """Function used to demonstrate caller stack frame inspection."""
    # sys._getframe(0) is current frame; sys._getframe(1) is caller frame
    caller_frame = sys._getframe(1)
    return {
        "caller_function_name": caller_frame.f_code.co_name,
        "caller_filename": caller_frame.f_code.co_filename,
    }


def caller_function():
    return helper_function()


def run_tests():
    # ============================================================
    # 1. STACK FRAME INTROSPECTION (sys._getframe)
    # ============================================================

    # Verify caller stack inspection
    info = caller_function()
    assert info["caller_function_name"] == "caller_function"

    # Current execution frame attributes
    current_frame = sys._getframe(0)
    assert current_frame.f_code.co_name == "run_tests"
    assert isinstance(current_frame.f_lineno, int)
    assert "current_frame" in current_frame.f_locals


    # ============================================================
    # 2. TRACEBACK PARSING & EXCEPTION EXTRACTION
    # ============================================================

    formatted_trace = ""
    try:
        # Simulate an intentional exception for traceback capture
        _ = 10 / 0
    except ZeroDivisionError:
        # Extract exception info without re-raising
        exc_type, exc_val, exc_tb = sys.exc_info()
        assert exc_type is ZeroDivisionError
        assert "division by zero" in str(exc_val)
        assert exc_tb is not None

        # Format traceback using traceback module
        formatted_trace = traceback.format_exc()

    assert "ZeroDivisionError: division by zero" in formatted_trace
    assert "03_first_debug.py" in formatted_trace


    # ============================================================
    # 3. BREAKPOINT HOOK BEHAVIOR (sys.breakpointhook)
    # ============================================================

    # Verify breakpointhook is configured and callable
    assert callable(sys.breakpointhook)

    # Custom breakpointhook simulation
    hook_triggered = False

    def custom_test_breakpointhook():
        nonlocal hook_triggered
        hook_triggered = True

    original_hook = sys.breakpointhook
    try:
        sys.breakpointhook = custom_test_breakpointhook
        # Calling breakpoint() invokes the custom hook
        breakpoint()
        assert hook_triggered is True
    finally:
        # Restore original hook
        sys.breakpointhook = original_hook


    # ============================================================
    # 4. ASSERTION SEMANTICS & TUPLE TRAP AWARENESS
    # ============================================================

    # Valid assertion passing
    expected_status = 200
    assert expected_status == 200, "Status must equal 200"

    # Failing assertion raises AssertionError
    assertion_caught = False
    try:
        assert expected_status == 404, "Invalid status detected"
    except AssertionError as err:
        assertion_caught = True
        assert str(err) == "Invalid status detected"

    assert assertion_caught is True


if __name__ == "__main__":
    run_tests()
    print("03_first_debug.py tests passed!")
