"""
1. CONCEPT & JS/TS ANALOGY
Strings in Python are sequences of characters. They are immutable.
JS/TS Analogy: Python's f-strings are like JS template literals (``). Python string slicing `[start:stop:step]` replaces JS `String.prototype.slice()`.

2. UNDER THE HOOD (CPython & Memory)
CPython intern strings (short strings that look like identifiers) to save memory. Since strings are immutable, modifying a string always creates a new object in memory.

3. COMMON GOTCHA
Strings are immutable. You cannot do `s[0] = 'X'`. You must create a new string: `s = 'X' + s[1:]`.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "What are f-strings and how do they differ from other string formatting?"
Script: "f-strings (introduced in Python 3.6) provide a concise and readable way to embed expressions inside string literals. Unlike older `%`-formatting or `.format()`, f-strings evaluate expressions at runtime and are generally faster because they are evaluated down to efficient C-level string concatenation operations during parsing. They make string formatting much more readable, avoiding the verbosity of `.format()`."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # Slicing
    text = "Python"
    assert text[0:2] == "Py"
    assert text[::-1] == "nohtyP" # reverse
    assert text[-3:] == "hon"

    # f-strings
    version = 3.12
    assert f"Python {version}" == "Python 3.12"
    assert f"{version * 2}" == "6.24"
    
    # Immutability check (conceptually, we just know we can't assign)
    try:
        text[0] = 'J'
        assert False, "Should raise TypeError"
    except TypeError:
        pass

if __name__ == '__main__':
    run_tests()
    print("02_strings_and_fstrings.py tests passed!")
