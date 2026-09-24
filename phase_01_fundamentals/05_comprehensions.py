"""
1. CONCEPT & JS/TS ANALOGY
Comprehensions provide a concise way to create lists, sets, or dicts from iterables.
JS/TS Analogy: They replace `Array.prototype.map()` and `Array.prototype.filter()` chains in JavaScript.

2. UNDER THE HOOD (CPython & Memory)
List comprehensions are heavily optimized at the C level. Python compiles them into a special function call under the hood, running the loop faster than an equivalent `for` loop with `.append()`.

3. COMMON GOTCHA
Using comprehensions for side-effects (like printing) is considered an anti-pattern. They should only be used for creating new collections. Nested comprehensions can quickly become unreadable.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "What are comprehensions and when should you NOT use them?"
Script: "Comprehensions are a concise syntax to create lists, dicts, or sets by transforming or filtering elements from an iterable. They are generally faster than normal for-loops due to C-level optimizations. However, you should NOT use them when the logic is too complex, leading to unreadable one-liners, or when the operation produces side effects instead of a new collection. In those cases, a standard for-loop is better."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # List comp
    evens = [x for x in range(10) if x % 2 == 0]
    assert evens == [0, 2, 4, 6, 8]

    # Dict comp
    squares = {x: x**2 for x in range(3)}
    assert squares == {0: 0, 1: 1, 2: 4}

    # Set comp
    unique_chars = {c for c in "hello"}
    assert unique_chars == {'h', 'e', 'l', 'o'}

if __name__ == '__main__':
    run_tests()
    print("05_comprehensions.py tests passed!")
