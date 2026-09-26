"""
03_control_flow.py

============================================================
1. CONCEPT
============================================================

Control flow structures dictate the order in which Python code executes.
Python provides standard branching and looping constructs with distinct,
idiomatic design choices:

1. Branching:
   - `if`, `elif`, `else` statements.
   - Ternary conditional expressions: `x if condition else y`.
   - Structural truthiness evaluation (implicit boolean conversion).
   - Chained comparison operators (e.g., `1 < x < 10`).

2. Iteration (Loops):
   - `for ... in iterable`: Iterates over ANY iterable (sequences, generators,
     mappings, sets). Python has no C-style `for (int i=0; i<n; i++)`.
   - `while condition`: Repeatedly executes as long as condition evaluates to True.
   - Lazy sequence iteration via `range(start, stop, step)`.
   - Index-tracking iteration via `enumerate(iterable, start=0)`.
   - Parallel multi-sequence iteration via `zip(*iterables, strict=False)`.

3. Loop Control:
   - `break`: Terminates the innermost loop immediately.
   - `continue`: Skips remainder of current iteration and proceeds to next.
   - `pass`: Syntactic no-op placeholder.
   - `else` clause on loops: Executes ONLY if the loop finishes without
     encountering a `break`.

4. Assignment Expressions (Walrus Operator `:=`):
   - Introduced in Python 3.8 (PEP 572).
   - Allows assigning a value to a variable within an expression context
     (e.g., inside `if` or `while` conditions).

5. Scoping Mechanics:
   - Python DOES NOT have block-level scope. Variables defined inside `if`,
     `elif`, `else`, `for`, or `while` blocks leak into the surrounding
     function or module scope.


============================================================
2. JS / TS ANALOGY
============================================================

Python and JavaScript / TypeScript handle control flow with key structural
differences:

+----------------------------+-----------------------------------+------------------------------------+
| Feature                    | Python                            | JavaScript / TypeScript            |
+----------------------------+-----------------------------------+------------------------------------+
| Block syntax               | Indentation (whitespace)          | Curly braces `{ ... }`             |
| Else-if                    | `elif condition:`                 | `else if (condition) { ... }`      |
| Ternary Operator           | `val if cond else other`          | `cond ? val : other`               |
| Sequence Looping           | `for item in items:`              | `for (const item of items) { ... }`|
| Index-based Looping        | `for i in range(n):`              | `for (let i = 0; i < n; i++) { ... }|
| Index + Item Looping       | `for i, item in enumerate(items):`| `items.forEach((item, i) => ...)`  |
| Parallel Looping           | `for a, b in zip(list1, list2):`  | `list1.map((a, i) => [a, list2[i]])`|
| Loop Else Clause           | `for ... else:` (runs if no break)| No native equivalent               |
| Assignment in Expression   | `if (n := len(x)) > 0:`           | `if ((n = x.length) > 0)`          |
| Block Scope                | NO: vars leak out of if/for       | YES: `let` / `const` are block-scoped|
+----------------------------+-----------------------------------+------------------------------------+

Key JS/TS Translation Differences:
1. Ternary syntax order is inverted:
   JS:     `result = isValid ? "OK" : "Error";`
   Python: `result = "OK" if is_valid else "Error"`

2. No C-style for loops in Python:
   JS:     `for (let i = 0; i < 10; i += 2) { ... }`
   Python: `for i in range(0, 10, 2):`

3. The loop `else` construct has no direct JS keyword:
   In JS, you must manually track a boolean flag (e.g., `let found = false;`).


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Bytecode & Jump Instructions:
   - Python code is compiled to CPython bytecode instructions.
   - An `if` statement compiles into conditional jump opcodes:
     `POP_JUMP_FORWARD_IF_FALSE` or `POP_JUMP_IF_FALSE`.
   - A `for` loop compiles into:
     - `GET_ITER`: Calls `iter()` on the target object to obtain an iterator.
     - `FOR_ITER`: Calls `next()` on the iterator. If values remain, pushes the
       value onto the evaluation stack. If `StopIteration` is raised, it jumps
       past the loop body (and directly into the `else` block if present).
     - `JUMP_BACKWARD`: Loops back to `FOR_ITER`.

2. How `range` works:
   - `range` is NOT a function that generates a list in memory.
   - It is an immutable sequence type (`class range`).
   - CPython stores only three fields: `start`, `stop`, and `step` (each a C long / PyObject).
   - Memory footprint is strictly $O(1)$ regardless of size:
     `sys.getsizeof(range(10))` == `sys.getsizeof(range(10_000_000_000))`.
   - Indexing (`range(100)[5]`) and membership testing (`50 in range(100)`)
     are computed mathematically in $O(1)$ time without traversing elements.

3. Scoping & Symbol Tables:
   - CPython parses variables during AST and symbol table construction into three
     storage categories: Fast local array (`FAST_LOCAL`), Cell/Free variables (closures),
     and Global/Builtin dict.
   - Because `if`, `while`, and `for` blocks DO NOT create a new stack frame or
     symbol table scope, any variable assigned inside them is placed into the
     function's local variable array (`co_fastlocal`).
   - Therefore, the variable remains accessible anywhere later in that same function.


============================================================
4. COMMON GOTCHAS
============================================================

1. Variable Leakage from Loops and Branches:
   - In Python, the loop variable retains its final value after the loop completes:
     ```python
     for i in range(5):
         pass
     print(i)  # Prints 4!
     ```
   - If an `if` branch defines a variable but that branch does not execute,
     referencing it later raises `UnboundLocalError` or `NameError`.

2. Modifying a Sequence While Iterating Over It:
   - Mutating a list (e.g., `remove()`, `append()`, `pop()`) while looping over it
     causes the internal index pointer to skip elements or repeat iterations.
   - Rule: Always iterate over a shallow copy (`for item in items[:]:`) or use a list
     comprehension to produce a filtered new list.

3. Misunderstanding the Loop `else` Clause:
   - The `else` block on a `for` or `while` loop does NOT execute when the loop is
     "empty" or "false".
   - It executes when the loop finishes NATURALLY (exhaustion of the iterable or
     the while condition becoming False).
   - If `break` is hit, the `else` block is completely SKIPPED.

4. The Walrus Operator Parentheses Gotcha:
   - Operator precedence: `:=` has very low precedence.
   - `if x := 5 > 2:` assigns `True` to `x`, because `>` takes precedence over `:=`!
   - To assign the result of an inner computation: `if (x := 5) > 2:` assigns `5` to `x`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does Python's loop else block work, and when would you use it?"
Script:
"In Python, both `for` and `while` loops support an optional `else` clause.
The `else` block runs only if the loop terminates normally without encountering
a `break` statement. The canonical use case is the search-and-fallback pattern:
searching an iterable for an item that satisfies a condition, executing a `break`
when found, and using the `else` block to handle the 'not found' condition. This
eliminates the need for temporary boolean flag variables like `found = False`
commonly seen in JavaScript or Java."

Q2: "What is the memory and time complexity of range() in Python 3?"
Script:
"In Python 3, `range()` returns an immutable sequence type, not an in-memory list
or generator. It stores only three integers: start, stop, and step. As a result,
its memory complexity is strictly $O(1)$, whether representing ten elements or ten
billion. Furthermore, its lookup and membership testing using the `in` operator
operate in $O(1)$ time because Python calculates whether a number falls on the arithmetic
progression using arithmetic checks rather than scanning through values."

Q3: "How does variable scoping work in Python control structures compared to JavaScript?"
Script:
"Unlike JavaScript with `let` and `const`, Python does not possess block scope.
Constructs like `if`, `elif`, `else`, `for`, `while`, and `with` do not create
new execution contexts or scopes. Variables assigned inside these blocks belong to the
enclosing function scope (or module scope if at top level). For example, a loop
variable in a `for` loop persists and remains accessible with its terminal value after
the loop concludes."
"""

import sys

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tests():
    # ============================================================
    # 1. CONDITIONAL STATEMENTS (if, elif, else)
    # ============================================================
    # Python uses indentation (standard 4 spaces) to define blocks.
    # Evaluation stops as soon as the first truthy condition is found.

    # ------------------------------------------------------------
    # Basic if / elif / else branching
    # ------------------------------------------------------------
    score = 85
    grade = ""

    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    else:
        grade = "F"

    assert grade == "B"

    # ------------------------------------------------------------
    # Truthiness in conditional checks
    # Empty containers, zero, None, and False evaluate to False
    # ------------------------------------------------------------
    empty_list = []
    non_empty_string = "Antigravity"
    zero_val = 0
    none_val = None

    evaluated_branches = []

    if empty_list:
        evaluated_branches.append("list")
    if non_empty_string:
        evaluated_branches.append("string")
    if zero_val:
        evaluated_branches.append("zero")
    if not none_val:
        evaluated_branches.append("none_handled")

    assert evaluated_branches == ["string", "none_handled"]

    # ------------------------------------------------------------
    # Short-circuit logical operators: and, or, not
    # 'and' returns first falsy value or last value
    # 'or' returns first truthy value or last value
    # ------------------------------------------------------------
    side_effects = []

    def probe(name, return_val):
        side_effects.append(name)
        return return_val

    # With 'and', if first operand is False, second operand is never evaluated
    result_and = probe("A", False) and probe("B", True)
    assert result_and is False
    assert side_effects == ["A"]  # "B" was never evaluated!

    side_effects.clear()

    # With 'or', if first operand is True, second operand is never evaluated
    result_or = probe("X", True) or probe("Y", False)
    assert result_or is True
    assert side_effects == ["X"]  # "Y" was never evaluated!

    # ------------------------------------------------------------
    # Chained comparison operators
    # Python allows mathematical chaining: `a < b < c` is equivalent
    # to `(a < b) and (b < c)` with `b` evaluated only once.
    # ------------------------------------------------------------
    x = 15
    assert 10 < x < 20
    assert 10 < x <= 15
    assert 20 > x > 5

    # Multi-value equality chaining
    a = b = c = 42
    assert a == b == c == 42


    # ============================================================
    # 2. TERNARY CONDITIONAL EXPRESSION
    # ============================================================
    # Syntax: <true_expression> if <condition> else <false_expression>
    # Analogous to JS: <condition> ? <true_expr> : <false_expr>

    # ------------------------------------------------------------
    # Standard ternary assignment
    # ------------------------------------------------------------
    is_authenticated = True
    status_msg = "Welcome" if is_authenticated else "Please log in"
    assert status_msg == "Welcome"

    is_admin = False
    access_level = "Full" if is_admin else "Guest"
    assert access_level == "Guest"

    # ------------------------------------------------------------
    # Ternary inline within expressions and function calls
    # ------------------------------------------------------------
    count = 1
    label = f"{count} item{'s' if count != 1 else ''}"
    assert label == "1 item"

    count = 5
    label = f"{count} item{'s' if count != 1 else ''}"
    assert label == "5 items"

    # ------------------------------------------------------------
    # Nested ternary (possible, though PEP 8 advises moderation)
    # ------------------------------------------------------------
    val = 0
    sign = "positive" if val > 0 else ("negative" if val < 0 else "zero")
    assert sign == "zero"


    # ============================================================
    # 3. FOR LOOPS & ITERATION
    # ============================================================
    # Python `for` is an iterator consumer, not a counting loop.
    # Works over any object implementing __iter__() or __getitem__().

    # ------------------------------------------------------------
    # Iterating over sequence types
    # ------------------------------------------------------------
    fruits = ["apple", "banana", "cherry"]
    collected = []
    for fruit in fruits:
        collected.append(fruit.upper())
    assert collected == ["APPLE", "BANANA", "CHERRY"]

    # Iterating over characters in a string
    chars = []
    for ch in "Code":
        chars.append(ch)
    assert chars == ["C", "o", "d", "e"]

    # ------------------------------------------------------------
    # Iterating over dictionaries
    # ------------------------------------------------------------
    user_roles = {"alice": "admin", "bob": "editor", "charlie": "viewer"}

    # Default iteration yields KEYS
    keys = []
    for user in user_roles:
        keys.append(user)
    assert keys == ["alice", "bob", "charlie"]

    # Iterating over values
    values = []
    for role in user_roles.values():
        values.append(role)
    assert values == ["admin", "editor", "viewer"]

    # Iterating over key-value pairs using .items()
    pairs = []
    for user, role in user_roles.items():
        pairs.append(f"{user}:{role}")
    assert pairs == ["alice:admin", "bob:editor", "charlie:viewer"]


    # ============================================================
    # 4. THE range() FUNCTION
    # ============================================================
    # range(stop)
    # range(start, stop)
    # range(start, stop, step)
    # Note: `stop` is non-inclusive (half-open interval [start, stop))

    # ------------------------------------------------------------
    # range variations
    # ------------------------------------------------------------
    assert list(range(4)) == [0, 1, 2, 3]
    assert list(range(2, 6)) == [2, 3, 4, 5]
    assert list(range(0, 10, 2)) == [0, 2, 4, 6, 8]
    assert list(range(10, 0, -2)) == [10, 8, 6, 4, 2]

    # ------------------------------------------------------------
    # range object properties: Lazy, O(1) memory, O(1) membership
    # ------------------------------------------------------------
    huge_range = range(0, 1_000_000_000, 5)
    # Memory size is tiny (holds only start, stop, step)
    assert sys.getsizeof(huge_range) < 100

    # O(1) Indexing support
    assert huge_range[0] == 0
    assert huge_range[1] == 5
    assert huge_range[10] == 50

    # O(1) Membership test (arithmetic calculation, not scanning)
    assert 500 in huge_range
    assert 501 not in huge_range

    # Slicing a range produces another range
    sub_range = huge_range[2:5]
    assert list(sub_range) == [10, 15, 20]


    # ============================================================
    # 5. enumerate() FOR INDEX-AWARE ITERATION
    # ============================================================
    # Yields tuples of (index, item). Replaces manual counter incrementing.

    # ------------------------------------------------------------
    # Default start index is 0
    # ------------------------------------------------------------
    languages = ["Python", "TypeScript", "Rust"]
    indexed_langs = []

    for index, lang in enumerate(languages):
        indexed_langs.append((index, lang))

    assert indexed_langs == [(0, "Python"), (1, "TypeScript"), (2, "Rust")]

    # ------------------------------------------------------------
    # Custom start index (e.g., 1-based indexing for display)
    # ------------------------------------------------------------
    ranked_langs = []
    for rank, lang in enumerate(languages, start=1):
        ranked_langs.append(f"#{rank} {lang}")

    assert ranked_langs == ["#1 Python", "#2 TypeScript", "#3 Rust"]


    # ============================================================
    # 6. zip() AND zip(strict=True)
    # ============================================================
    # Iterates over multiple iterables in parallel, pairing elements into tuples.

    # ------------------------------------------------------------
    # Standard zip (truncates to length of shortest iterable)
    # ------------------------------------------------------------
    names = ["Alice", "Bob", "Charlie", "Diana"]
    salaries = [120000, 95000, 105000]  # Note: only 3 items

    paired = list(zip(names, salaries))
    # Diana is truncated because salaries only has 3 items
    assert paired == [("Alice", 120000), ("Bob", 95000), ("Charlie", 105000)]

    # ------------------------------------------------------------
    # zip() for dictionary construction
    # ------------------------------------------------------------
    keys = ["id", "username", "email"]
    vals = [101, "py_dev", "dev@example.com"]
    user_dict = dict(zip(keys, vals))
    assert user_dict == {"id": 101, "username": "py_dev", "email": "dev@example.com"}

    # ------------------------------------------------------------
    # Python 3.10+ zip(..., strict=True)
    # Raises ValueError if iterables are not of equal length
    # ------------------------------------------------------------
    items_a = [1, 2, 3]
    items_b = ["a", "b", "c"]
    items_c_short = ["x", "y"]

    # Equal lengths work normally
    strict_pairs = list(zip(items_a, items_b, strict=True))
    assert strict_pairs == [(1, "a"), (2, "b"), (3, "c")]

    # Unequal lengths raise ValueError
    strict_error_raised = False
    try:
        list(zip(items_a, items_c_short, strict=True))
    except ValueError:
        strict_error_raised = True
    assert strict_error_raised is True


    # ============================================================
    # 7. WHILE LOOPS
    # ============================================================
    # Repeatedly executes code block as long as boolean condition is True.

    # ------------------------------------------------------------
    # Standard while iteration
    # ------------------------------------------------------------
    count = 0
    accumulator = 0
    while count < 5:
        accumulator += count
        count += 1

    assert count == 5
    assert accumulator == 10  # 0 + 1 + 2 + 3 + 4


    # ============================================================
    # 8. LOOP CONTROL: break, continue, pass
    # ============================================================

    # ------------------------------------------------------------
    # break: Early termination
    # ------------------------------------------------------------
    found_num = None
    for n in [10, 20, 35, 40, 50]:
        if n % 7 == 0:
            found_num = n
            break

    assert found_num == 35

    # ------------------------------------------------------------
    # continue: Skip remainder of iteration
    # ------------------------------------------------------------
    evens = []
    for n in range(10):
        if n % 2 != 0:
            continue
        evens.append(n)

    assert evens == [0, 2, 4, 6, 8]

    # ------------------------------------------------------------
    # pass: Syntactic placeholder (no-op)
    # Useful when a syntax block is required but no action is needed
    # ------------------------------------------------------------
    stub_executed = False
    for i in range(3):
        if i == 1:
            pass  # Placeholder for future logic
        stub_executed = True

    assert stub_executed is True


    # ============================================================
    # 9. THE LOOP else CLAUSE (for...else and while...else)
    # ============================================================
    # Executes ONLY if the loop completes WITHOUT encountering a `break`.

    # ------------------------------------------------------------
    # Case 1: Search hits `break` -> `else` block is BYPASSED
    # ------------------------------------------------------------
    target = 3
    numbers = [1, 2, 3, 4, 5]
    search_result = ""

    for num in numbers:
        if num == target:
            search_result = f"Found {target}"
            break
    else:
        search_result = f"{target} not found"

    assert search_result == "Found 3"

    # ------------------------------------------------------------
    # Case 2: Loop exhausts without `break` -> `else` block RUNS
    # ------------------------------------------------------------
    missing_target = 99
    search_result_missing = ""

    for num in numbers:
        if num == missing_target:
            search_result_missing = f"Found {missing_target}"
            break
    else:
        search_result_missing = f"{missing_target} not found"

    assert search_result_missing == "99 not found"

    # ------------------------------------------------------------
    # while...else works identically
    # ------------------------------------------------------------
    n = 0
    while_else_ran = False
    while n < 3:
        n += 1
    else:
        while_else_ran = True

    assert while_else_ran is True


    # ============================================================
    # 10. THE WALRUS OPERATOR (:=) - ASSIGNMENT EXPRESSIONS
    # ============================================================
    # Allows variable assignment inside expressions (Python 3.8+).

    # ------------------------------------------------------------
    # In 'if' statements: compute, bind, and test simultaneously
    # ------------------------------------------------------------
    sample_text = "Python Engineering"
    if (str_len := len(sample_text)) > 10:
        length_captured = str_len
    else:
        length_captured = 0

    assert length_captured == 18
    assert str_len == 18  # Bound variable remains in scope!

    # ------------------------------------------------------------
    # In 'while' loops: stream / batch consumption pattern
    # Simulates reading chunks until empty sentinel
    # ------------------------------------------------------------
    stream_data = ["chunk_1", "chunk_2", "chunk_3", ""]
    stream_index = 0

    def mock_read_chunk():
        nonlocal stream_index
        val = stream_data[stream_index]
        stream_index += 1
        return val

    consumed_chunks = []
    # Loop continues while the assigned chunk is non-empty
    while (chunk := mock_read_chunk()) != "":
        consumed_chunks.append(chunk)

    assert consumed_chunks == ["chunk_1", "chunk_2", "chunk_3"]

    # ------------------------------------------------------------
    # Walrus operator precedence: Parentheses matter!
    # Without parens, comparison takes precedence over assignment.
    # ------------------------------------------------------------
    # Case with parentheses: binds 42 to num_val, then tests > 10
    if (num_val := 42) > 10:
        assert num_val == 42

    # Case WITHOUT parentheses: binds result of (42 > 100), which is False!
    # `bool_val := 42 > 100` assigns False to bool_val
    bool_val = (42 > 100)
    assert bool_val is False


    # ============================================================
    # 11. SCOPING MECHANICS IN CONTROL FLOW
    # ============================================================
    # Python has NO block scope. Blocks do not create new symbol frames.

    # ------------------------------------------------------------
    # Variable created in `if` is visible outside
    # ------------------------------------------------------------
    condition = True
    if condition:
        created_in_if = "I leaked out!"
    else:
        created_in_if = "Not reached"

    assert created_in_if == "I leaked out!"

    # ------------------------------------------------------------
    # Loop variable survives loop termination
    # ------------------------------------------------------------
    for loop_var in [10, 20, 30]:
        inner_computation = loop_var * 2

    # Both variables are still in scope and hold terminal values!
    assert loop_var == 30
    assert inner_computation == 60


    # ============================================================
    # 12. SAFE ITERATION: AVOIDING MUTATION WHILE LOOPING
    # ============================================================

    # ------------------------------------------------------------
    # Anti-pattern: Mutating while looping skips elements
    # Correct pattern: Iterate over a shallow copy with [:]
    # ------------------------------------------------------------
    items_to_clean = [1, 2, 2, 3, 4, 2, 5]

    # Iterating over slice copy allows safe deletion from original
    for item in items_to_clean[:]:
        if item == 2:
            items_to_clean.remove(item)

    assert items_to_clean == [1, 3, 4, 5]


if __name__ == "__main__":
    run_tests()
    print("03_control_flow.py tests passed!")
