"""
Phase 4: Errors, Files, HTTP & Stdlib - Exceptions & Error Handling
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Python's try/except block has 4 clauses:
     * 'try': Code that may raise an exception.
     * 'except <ExceptionClass> as e': Catches matching exception types.
     * 'else': Executes ONLY if NO exception was raised in the try block (JS has no equivalent!).
     * 'finally': ALWAYS executes, regardless of whether an exception occurred or was handled (cleanup).
   - Custom Exceptions: Inherit from 'Exception' (never BaseException directly).
   - Exception Chaining: 'raise NewException("msg") from original_err' preserves the original
     traceback and attaches it to '__cause__'.
   - JS/TS Analogy:
     * In JS, you can throw anything: 'throw "error"' or 'throw 404'. In Python, you can ONLY raise
       instances of classes inheriting from BaseException ('raise ValueError("...")').
     * In JS, 'try...catch' catches all types indiscriminately. In Python, you catch specific
       exception classes: 'except (ValueError, KeyError) as e:'.

2. UNDER THE HOOD (CPython & Memory):
   - CPython implements zero-cost exception handling (PEP 654 / Python 3.11+). Code inside 'try'
     runs at full speed without setup overhead; cost is paid only when an exception is raised.
   - When an exception occurs, CPython builds a traceback object containing a linked list of frame objects.
   - Using 'raise ... from err' sets '__cause__ = err' on the new exception, enabling full root-cause introspection.

3. COMMON GOTCHA:
   - Bare 'except:' or catching 'BaseException':
     try:
         do_work()
     except: # BUG: Also catches KeyboardInterrupt (Ctrl+C) and SystemExit!
         pass
     # FIX: Always catch 'except Exception:' or specific domain exceptions.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does exception handling in Python differ from JavaScript, what is the role
       of the 'else' clause in try/except, and what is exception chaining?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Specific Catching & The 'else' Clause:
      "In JavaScript, catch blocks handle any thrown value indiscriminately. In Python,
       exceptions are class-based, allowing you to catch precise exception hierarchies.
       A unique Python feature is the 'else' clause: code inside 'else' runs only if the
       'try' block succeeded without exceptions. This keeps the 'try' block minimal and prevents
       accidentally catching errors that occur during post-success processing."
   2. Exception Chaining ('raise from'):
      "When building production microservices, we often catch low-level library errors
       (like a database connection timeout) and wrap them in a domain exception (like UserServiceError).
       By writing 'raise UserServiceError('Failed to fetch user') from db_err', Python preserves the
       original stack trace under the '__cause__' attribute. This provides full root-cause visibility
       in production observability tools without exposing raw DB internals to the API caller."
   3. The Senior Clean-Up Rule:
      "Always prefer Context Managers ('with' statements) for resource clean-up over manual
       try/finally blocks whenever possible."
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
# 1. CUSTOM DOMAIN EXCEPTION HIERARCHY
# ==============================================================================

class AppError(Exception):
    """Base application exception for domain errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class EntityNotFoundError(AppError):
    """Raised when a requested resource does not exist."""
    def __init__(self, entity_type: str, entity_id: int):
        super().__init__(f"{entity_type} with ID {entity_id} was not found.", error_code="ENTITY_NOT_FOUND")
        self.entity_type = entity_type
        self.entity_id = entity_id


class InsufficientFundsError(AppError):
    """Raised when an account does not have enough balance."""
    def __init__(self, current_balance: float, requested_amount: float):
        super().__init__(
            f"Insufficient funds: balance ${current_balance:.2f} < requested ${requested_amount:.2f}",
            error_code="INSUFFICIENT_FUNDS"
        )
        self.current_balance = current_balance
        self.requested_amount = requested_amount


# ==============================================================================
# 2. DEMONSTRATIONS: try / except / else / finally & Chaining
# ==============================================================================

def demonstrate_try_except_else_finally(value: str):
    print(f"\nProcessing input: '{value}'")
    result = None
    try:
        # Step 1: Keep try block minimal
        num = int(value)
        result = 100 / num
    except ValueError as e:
        print(f"  [EXCEPT - ValueError] Could not convert to integer: {e}")
    except ZeroDivisionError as e:
        print(f"  [EXCEPT - ZeroDivisionError] Division by zero attempted: {e}")
    else:
        # Step 2: Runs ONLY when no exceptions occurred
        print(f"  [ELSE - Success] Calculation succeeded: 100 / {num} = {result}")
    finally:
        # Step 3: Always runs (e.g. closing socket/file)
        print("  [FINALLY] Cleanup executed.")
    return result


def demonstrate_exception_chaining(raw_user_id: str):
    print(f"\n--- Exception Chaining for raw_user_id='{raw_user_id}' ---")
    try:
        try:
            user_id = int(raw_user_id)
            if user_id <= 0:
                raise ValueError("User ID must be a positive integer.")
            # Simulating DB lookup failure
            raise KeyError("Record missing in DB")
        except (ValueError, KeyError) as low_level_err:
            # Wrap low-level error in high-level domain error while preserving cause!
            raise EntityNotFoundError("User", -1 if not raw_user_id.isdigit() else int(raw_user_id)) from low_level_err
    except EntityNotFoundError as domain_err:
        print(f"  Caught Domain Exception: [{domain_err.error_code}] {domain_err}")
        print(f"  Underlying root cause (__cause__): {repr(domain_err.__cause__)}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def safe_parse_int(val, default_val=0):
    """Parses val to int; returns default_val on ValueError."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default_val


def withdraw(balance: float, amount: float) -> float:
    """Raises InsufficientFundsError if amount > balance, otherwise returns new balance."""
    if amount > balance:
        raise InsufficientFundsError(balance, amount)
    return balance - amount


def run_tests():
    print("\n[*] Running automated self-tests for 01_exceptions_and_custom_errors.py...")
    assert safe_parse_int("42") == 42
    assert safe_parse_int("invalid", 10) == 10
    assert safe_parse_int(None, -1) == -1
    
    # Test withdrawal logic and custom exception
    assert withdraw(100.0, 40.0) == 60.0
    
    try:
        withdraw(50.0, 100.0)
        assert False, "Should raise InsufficientFundsError"
    except InsufficientFundsError as e:
        assert e.error_code == "INSUFFICIENT_FUNDS"
        assert e.current_balance == 50.0
        assert e.requested_amount == 100.0

    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 4 - Exceptions & Custom Errors")
    print("=" * 65)
    demonstrate_try_except_else_finally("10")
    demonstrate_try_except_else_finally("0")
    demonstrate_try_except_else_finally("not_a_number")
    demonstrate_exception_chaining("abc")
    print("-" * 65)
    run_tests()
    print("=" * 65)
