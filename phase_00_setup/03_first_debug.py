"""
1. CONCEPT & JS/TS ANALOGY
Debugging Python code.
JS/TS Analogy: Using `pdb` or `breakpoint()` is similar to using the `debugger` statement in JavaScript.

2. UNDER THE HOOD (CPython & Memory)
The `breakpoint()` built-in calls `sys.breakpointhook()`, which by default imports `pdb` and starts the debugger. This pauses CPython's bytecode evaluation loop.

3. COMMON GOTCHA
Leaving `breakpoint()` or bare `print()` statements in production code. Using broad `except Exception:` blocks that swallow critical errors during debugging.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "How do you debug Python code?"
Script: "For simple issues, I might use structured print statements or logging. For complex logic, I drop a `breakpoint()` in the code to open the `pdb` interactive debugger, allowing me to step through execution and inspect variables. Most often, I rely on my IDE's visual debugger (like VS Code or PyCharm), which lets me set graphical breakpoints, watch variables, and evaluate expressions on the fly without modifying code."

5. SELF-TESTS
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError as e:
        print(f"Debug: Caught division by zero - {e}")
        return None

def run_tests():
    res1 = divide(10, 2)
    assert res1 == 5.0, f"Expected 5.0, got {res1}"
    
    res2 = divide(10, 0)
    assert res2 is None, "Expected None for zero division"
    
    print("Tests passed for 03_first_debug.py")

if __name__ == "__main__":
    run_tests()
