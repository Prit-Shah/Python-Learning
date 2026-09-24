"""
1. CONCEPT & JS/TS ANALOGY
Unpacking assigns elements of an iterable to multiple variables. Pattern matching (`match/case` in 3.10+) allows structural matching of data.
JS/TS Analogy: Unpacking is similar to JS destructuring `const [a, b] = arr`. `match/case` looks like JS `switch`, but is far more powerful, similar to Rust's pattern matching.

2. UNDER THE HOOD (CPython & Memory)
`UNPACK_SEQUENCE` is a highly optimized bytecode instruction in CPython. `match/case` compiles down to efficient branching structures rather than chained `if/elif` statements.

3. COMMON GOTCHA
`match/case` is not just a switch statement checking for equality. It attempts to bind variables. For example, `case x:` acts as a catch-all that binds the value to the variable `x`.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "What is structural pattern matching in Python 3.10+?"
Script: "Structural pattern matching, introduced in Python 3.10 via `match` and `case`, allows you to match the structure of data against patterns, not just value equality. You can match against specific types, extract values from sequences or dictionaries, and use guard clauses (`if` conditions) within the pattern. It is much more powerful than a traditional switch statement because it structurally destructures objects."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # Unpacking
    a, b = 1, 2
    a, b = b, a # Swap
    assert a == 2 and b == 1

    first, *rest, last = [1, 2, 3, 4, 5]
    assert first == 1
    assert rest == [2, 3, 4]
    assert last == 5

    # Pattern matching
    def http_status(status):
        match status:
            case 200 | 201:
                return "OK"
            case 404:
                return "Not Found"
            case _:
                return "Unknown"
    
    assert http_status(200) == "OK"
    assert http_status(404) == "Not Found"
    assert http_status(500) == "Unknown"

if __name__ == '__main__':
    run_tests()
    print("07_unpacking_and_pattern_matching.py tests passed!")
