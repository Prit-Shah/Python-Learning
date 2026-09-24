"""
1. CONCEPT & JS/TS ANALOGY
Control flow includes if/elif/else, for loops over iterables, while loops, and range(). The walrus operator (`:=`) allows assignment within expressions.
JS/TS Analogy: Python uses indentation instead of curly braces `{}`. `elif` instead of `else if`. Python's `for item in iterable` is like JS `for...of`. Python has no `for (let i=0; i<n; i++)`; use `for i in range(n)`.

2. UNDER THE HOOD (CPython & Memory)
Python scopes variables to functions, classes, and modules, NOT to blocks (like `if` or `for`). The bytecode evaluation loop jumps between instructions based on these constructs.

3. COMMON GOTCHA
No block scope! Variables defined inside an `if` block or `for` loop are accessible outside of it in the same function.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "Explain Python control flow differences from JavaScript"
Script: "The main differences are syntactic and scoping. Python uses indentation rather than braces for code blocks. For looping over sequences, Python uses `for item in collection`, analogous to JS's `for...of`, whereas JS's `for...in` iterates over keys. Most importantly, Python does not have block-level scoping. Variables created inside a `for` loop or `if` statement persist in the surrounding function scope, unlike JS `let` or `const`."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # Scope test
    for i in range(3):
        x = i
    assert x == 2  # x leaks out of the loop

    # Walrus operator
    if (n := len([1, 2, 3])) > 2:
        assert n == 3

if __name__ == '__main__':
    run_tests()
    print("03_control_flow.py tests passed!")
