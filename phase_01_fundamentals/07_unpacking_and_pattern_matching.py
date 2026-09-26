"""
07_unpacking_and_pattern_matching.py

============================================================
1. CONCEPT
============================================================

Python provides two interconnected, extremely expressive paradigms for
destructuring and handling structured data:

1. Iterable & Sequence Unpacking:
   - Basic Unpacking: Assigning elements from any iterable to multiple targets
     in a single statement: `a, b = (1, 2)`.
   - Variable Swapping: Idiomatic in-place swap without a temp variable:
     `a, b = b, a`.
   - Extended Iterable Unpacking (PEP 3132): Using `*` to capture variable
     number of elements into a `list`: `first, *middle, last = items`.
   - Dictionary Unpacking (PEP 448): Using `**` to unpack and merge key-value
     mappings, or `|` / `|=` union operators (PEP 584).
   - Nested Unpacking: Deconstructing compound nested data structures directly.

2. Structural Pattern Matching (PEP 634, 635, 636 - Python 3.10+):
   - Introduced via `match <subject>:` and `case <pattern>:` statements.
   - Far more powerful than a traditional `switch/case` statement: matches
     against the *shape* (type, sequence length, dict keys, object attributes)
     of data, extracts values into variables, and enforces constraints.
   - Pattern Types:
     - Literal Patterns: Exact values (`case 200:`, `case "OK":`).
     - Or-Patterns: Multiple alternatives via `|` (`case 401 | 403:`).
     - Wildcard Pattern: `_` matches anything without binding a variable.
     - Capture Patterns: `case var_name:` matches anything and BINDS it.
     - Value Patterns: `case Class.ATTR:` (must be dotted to avoid capture).
     - Sequence Patterns: `case [x, y, *rest]:` matches lists or tuples.
     - Mapping Patterns: `case {"id": uid, "role": role}:` matches dicts.
     - Class Patterns: `case Point(x=x, y=y):` matches object types.
     - Guard Clauses: `case pattern if condition:` for boolean constraints.
     - As Patterns: `case pattern as name:` to capture matched sub-elements.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+-----------------------------------+------------------------------------+
| Feature                      | Python                            | JavaScript / TypeScript            |
+------------------------------+-----------------------------------+------------------------------------+
| Array/Tuple Unpacking        | `a, b = items`                    | `const [a, b] = items;`            |
| Rest / Extended Unpacking    | `head, *tail = items`             | `const [head, ...tail] = items;`   |
| Starred Target in Middle     | `first, *mid, last = items`       | NOT SUPPORTED in JS (must be last) |
| In-place Swapping            | `a, b = b, a`                     | `[a, b] = [b, a];`                 |
| Dict Unpacking / Merging     | `{**d1, **d2}` or `d1 | d2`       | `{ ...d1, ...d2 }`                 |
| Multi-branch Dispatch        | `match / case` (3.10+)            | `switch (val) { case ... }`        |
| Structural Decomposition     | Built into `match/case`           | No native equivalent (manual `if`) |
| Guard Clauses on Cases       | `case [x, y] if x > 0:`           | No native equivalent in switch     |
+------------------------------+-----------------------------------+------------------------------------+

Key JS vs Python Structural Differences:
1. Python's extended unpacking allows the `*` star operator ANYWHERE in the
   target sequence:
   Python: `first, *middle, last = [1, 2, 3, 4, 5]` -> middle is `[2, 3, 4]`.
   JavaScript: `const [first, ...middle, last] = [1, 2, 3, 4, 5];` -> SyntaxError!
   In JS, `...rest` MUST be the last element.

2. JS `switch` vs Python `match/case`:
   A JS `switch` only checks value equality (`===`) against a scalar expression
   and requires `break` to prevent fallthrough.
   Python's `match/case` has NO fallthrough (no `break` needed), deconstructs
   complex nested data, validates types, and binds extracted variables.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Bytecode for Unpacking:
   - Fixed unpacking (`a, b = pair`) compiles directly to:
     - `UNPACK_SEQUENCE 2`: pops the top of the stack, verifies its length
       equals 2, and pushes the items onto the stack in reverse order.
     - `STORE_FAST a`, `STORE_FAST b`: binds the items to local variables.
   - Extended unpacking (`first, *rest, last = seq`) compiles to:
     - `UNPACK_EX (before_count, after_count)`: a dedicated CPython opcode that
       allocates a new `list` for the middle slice and extracts the exact head
       and tail items in $O(N)$ time.

2. Starred Unpacking Always Yields a List:
   - Regardless of whether the source iterable is a tuple, set, generator,
     or string, the starred target variable is ALWAYS instantiated as a `list`.

3. Structural Pattern Matching Optimization:
   - Pattern matching compiles into specialized opcodes:
     - `MATCH_SEQUENCE`: checks if the object is a sequence and not a str/bytes.
     - `MATCH_MAPPING`: checks if the object is a `collections.abc.Mapping`.
     - `MATCH_CLASS`: inspects `__match_args__` and type attributes.
     - `GET_LEN`: checks sequence length before unpacking.
   - CPython optimizes patterns so that redundant type and length checks are
     not repeated across consecutive case branches.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Variable Capture Trap in `case`:
   - In a `case` statement, a bare identifier is NOT an equality check against
     an existing variable! It is a CAPTURE variable that matches ANYTHING and
     rebinds that name:
     ```python
     EXPECTED = 200
     match status:
         case EXPECTED:  # BUG! Matches EVERYTHING and binds status to EXPECTED!
             print("Matches anything!")
     ```
   - Fix: Use a dotted name (e.g. `case Status.OK:` or `case constants.EXPECTED:`)
     or use a guard: `case code if code == EXPECTED:`.

2. Dict Pattern Matching is Partial:
   - In `case {"status": 200}:`, this pattern matches if the dictionary contains
     `"status": 200`, EVEN IF the dictionary has 50 other keys!
   - By contrast, sequence matching (`case [a, b]:`) requires an EXACT length match
     unless `*rest` is explicitly included.

3. Multiple Starred Targets in Unpacking:
   - Only ONE starred target is allowed in an assignment:
     `*a, *b = [1, 2, 3]` -> `SyntaxError: two starred expressions in assignment`.

4. Value Mismatch on Fixed Unpacking:
   - `x, y = [1, 2, 3]` raises `ValueError: too many values to unpack (expected 2)`.
   - `x, y, z = [1]` raises `ValueError: not enough values to unpack (expected 3, got 1)`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Python 3.10+ match/case differs from a traditional switch statement."
Script:
"Python 3.10's structural pattern matching via `match/case` is fundamentally different
from a C or JavaScript switch statement. While a switch statement simply evaluates
scalar equality with fallthrough semantics, `match/case` performs deep structural
decomposition without fallthrough. It can validate types, check sequence lengths,
extract specific keys from mappings, deconstruct custom class attributes using
`__match_args__`, and evaluate arbitrary boolean conditions via `if` guard clauses.
It acts as both a control flow mechanism and a data destructuring pipeline."

Q2: "What is the capture variable trap in Python pattern matching and how do you avoid it?"
Script:
"In a `case` clause, an unqualified identifier is treated as a capture pattern,
meaning it matches any value unconditionally and re-binds that identifier to the
subject. If a developer attempts to match against an existing variable like
`case STATUS_OK:`, it will unintentionally match every input and overwrite `STATUS_OK`.
To match against a constant, CPython requires the identifier to be a dotted name,
such as `case HttpStatus.OK:`, or alternatively, handled with an explicit guard clause
like `case code if code == STATUS_OK:`."

Q3: "How does Python's extended iterable unpacking work, and how does it differ from JavaScript destructuring?"
Script:
"Extended iterable unpacking allows unpacking an arbitrary iterable using the `*`
starred operator to collect remaining items into a list. Unlike JavaScript, where the
rest operator `...` must strictly appear as the final element in an array destructuring
assignment, Python allows the starred target to appear anywhere in the sequence—at the
beginning, middle, or end. For example, `first, *middle, last = items` cleanly splits
the head, inner elements, and tail in a single expressive statement. CPython executes
this via the specialized `UNPACK_EX` bytecode instruction."
"""

import sys
from dataclasses import dataclass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class Point:
    x: float
    y: float


@dataclass
class ActionCommand:
    action: str
    target: str
    amount: int = 1


def run_tests():
    # ============================================================
    # 1. BASIC SEQUENCE UNPACKING
    # ============================================================
    # Any iterable can be unpacked into comma-separated variables.

    # ------------------------------------------------------------
    # Tuple and list unpacking
    # ------------------------------------------------------------
    coordinates = (10, 20)
    x, y = coordinates
    assert x == 10
    assert y == 20

    data = ["Alice", 28, "Engineer"]
    name, age, title = data
    assert name == "Alice"
    assert age == 28
    assert title == "Engineer"

    # ------------------------------------------------------------
    # Idiomatic variable swap
    # Evaluates RHS into temporary tuple, then unpacks into LHS
    # ------------------------------------------------------------
    a, b = 100, 200
    a, b = b, a
    assert a == 200
    assert b == 100

    # ------------------------------------------------------------
    # Value mismatch errors (ValueError)
    # ------------------------------------------------------------
    too_many_raised = False
    try:
        x, y = [1, 2, 3]
    except ValueError:
        too_many_raised = True
    assert too_many_raised is True

    too_few_raised = False
    try:
        x, y, z = [1]
    except ValueError:
        too_few_raised = True
    assert too_few_raised is True


    # ============================================================
    # 2. EXTENDED ITERABLE UNPACKING (*starred expressions)
    # ============================================================
    # PEP 3132: Starred variable collects remaining elements as a LIST.

    # ------------------------------------------------------------
    # Capturing middle elements (Impossible in JavaScript!)
    # ------------------------------------------------------------
    numbers = [1, 2, 3, 4, 5, 6]
    first, *middle, last = numbers

    assert first == 1
    assert middle == [2, 3, 4, 5]
    assert last == 6
    assert isinstance(middle, list)

    # ------------------------------------------------------------
    # Head and Tail decomposition
    # ------------------------------------------------------------
    head, *tail = (10, 20, 30)
    assert head == 10
    assert tail == [20, 30]  # Note: tail is a list even though source was a tuple!

    # ------------------------------------------------------------
    # Starred unpacking on empty remainder
    # If no elements remain, starred variable becomes an empty list []
    # ------------------------------------------------------------
    x, *extra = [42]
    assert x == 42
    assert extra == []

    # ------------------------------------------------------------
    # Ignoring elements with dummy target `*_`
    # ------------------------------------------------------------
    first_item, *_, last_item = [10, 20, 30, 40, 50, 60]
    assert first_item == 10
    assert last_item == 60


    # ============================================================
    # 3. DICTIONARY UNPACKING & MERGING
    # ============================================================
    # Unpacking mappings with ** and the union operator |

    # ------------------------------------------------------------
    # Merging dicts with ** unpacking
    # Later keys override earlier keys
    # ------------------------------------------------------------
    base_config = {"env": "prod", "debug": False, "timeout": 30}
    override_config = {"debug": True, "timeout": 60, "port": 8080}

    merged = {**base_config, **override_config, "version": "v1.2"}
    assert merged == {
        "env": "prod",
        "debug": True,
        "timeout": 60,
        "port": 8080,
        "version": "v1.2",
    }

    # ------------------------------------------------------------
    # Python 3.9+ Union operators (| and |=)
    # ------------------------------------------------------------
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 99, "c": 3}
    d3 = d1 | d2
    assert d3 == {"a": 1, "b": 99, "c": 3}

    d1 |= {"d": 4}
    assert d1 == {"a": 1, "b": 2, "d": 4}


    # ============================================================
    # 4. NESTED STRUCTURE UNPACKING
    # ============================================================
    # Deep destructuring mirrors the source structure.

    # ------------------------------------------------------------
    # Unpacking nested tuples and lists
    # ------------------------------------------------------------
    record = ("ServerA", ("192.168.1.1", 443), ["tcp", "udp"])
    server_name, (ip, port), (proto1, proto2) = record

    assert server_name == "ServerA"
    assert ip == "192.168.1.1"
    assert port == 443
    assert proto1 == "tcp"
    assert proto2 == "udp"

    # ------------------------------------------------------------
    # Unpacking inside loop constructs
    # ------------------------------------------------------------
    points = [("Origin", 0, 0), ("Target", 10, 20)]
    collected_points = []
    for label, px, py in points:
        collected_points.append(f"{label}=({px},{py})")

    assert collected_points == ["Origin=(0,0)", "Target=(10,20)"]


    # ============================================================
    # 5. STRUCTURAL PATTERN MATCHING: LITERALS & OR-PATTERNS
    # ============================================================
    # Python 3.10+ match/case

    def handle_status(code):
        match code:
            case 200 | 201:
                return "Success"
            case 400:
                return "Bad Request"
            case 401 | 403:
                return "Unauthorized"
            case 404:
                return "Not Found"
            case 500:
                return "Server Error"
            case _:
                return "Other"

    assert handle_status(200) == "Success"
    assert handle_status(201) == "Success"
    assert handle_status(403) == "Unauthorized"
    assert handle_status(404) == "Not Found"
    assert handle_status(999) == "Other"


    # ============================================================
    # 6. PATTERN MATCHING: SEQUENCE PATTERNS
    # ============================================================
    # Matches sequence lengths, items, and starred rests.

    def parse_cli_command(command_parts):
        match command_parts:
            case ["quit"]:
                return "Exiting application"
            case ["load", filename]:
                return f"Loading file: {filename}"
            case ["save", filename, "--force"]:
                return f"Force saving to: {filename}"
            case ["process", *files]:
                return f"Processing {len(files)} files: {', '.join(files)}"
            case _:
                return "Unknown command"

    assert parse_cli_command(["quit"]) == "Exiting application"
    assert parse_cli_command(["load", "data.csv"]) == "Loading file: data.csv"
    assert parse_cli_command(["save", "out.txt", "--force"]) == "Force saving to: out.txt"
    assert parse_cli_command(["process", "a.py", "b.py", "c.py"]) == "Processing 3 files: a.py, b.py, c.py"
    assert parse_cli_command(["unknown"]) == "Unknown command"


    # ============================================================
    # 7. PATTERN MATCHING: MAPPING (DICT) PATTERNS
    # ============================================================
    # Note: Mapping patterns perform PARTIAL matching!
    # They succeed if the specified keys exist, ignoring extra keys.

    def route_event(event):
        match event:
            case {"type": "click", "x": x_pos, "y": y_pos}:
                return f"Click at ({x_pos}, {y_pos})"
            case {"type": "keypress", "key": key_pressed}:
                return f"Key: {key_pressed}"
            case {"type": "hover"}:
                return "Hover detected"
            case _:
                return "Unhandled event"

    # Exact keys
    assert route_event({"type": "keypress", "key": "Enter"}) == "Key: Enter"

    # Partial match: extra keys ("timestamp", "button") do NOT fail the pattern!
    click_event = {"type": "click", "x": 120, "y": 450, "timestamp": 1699999, "button": "left"}
    assert route_event(click_event) == "Click at (120, 450)"


    # ============================================================
    # 8. PATTERN MATCHING: CLASS PATTERNS & DATACLASSES
    # ============================================================
    # Destructuring objects and extracting attributes.

    def evaluate_shape(obj):
        match obj:
            case Point(x=0, y=0):
                return "At Origin"
            case Point(x=0, y=y_val):
                return f"On Y-axis at {y_val}"
            case Point(x=x_val, y=0):
                return f"On X-axis at {x_val}"
            case Point(x=x_val, y=y_val):
                return f"Quadrant point ({x_val}, {y_val})"
            case _:
                return "Not a point"

    assert evaluate_shape(Point(0, 0)) == "At Origin"
    assert evaluate_shape(Point(0, 15)) == "On Y-axis at 15"
    assert evaluate_shape(Point(25, 0)) == "On X-axis at 25"
    assert evaluate_shape(Point(3, 7)) == "Quadrant point (3, 7)"
    assert evaluate_shape("just a string") == "Not a point"

    # Positional class matching via __match_args__ (automatically generated by dataclass)
    def dispatch_action(cmd):
        match cmd:
            case ActionCommand("BUY", ticker, qty) if qty > 100:
                return f"Large order: Buy {qty} of {ticker}"
            case ActionCommand("BUY", ticker, qty):
                return f"Standard order: Buy {qty} of {ticker}"
            case ActionCommand("SELL", ticker, _):
                return f"Liquidating {ticker}"
            case _:
                return "Invalid command"

    assert dispatch_action(ActionCommand("BUY", "AAPL", 500)) == "Large order: Buy 500 of AAPL"
    assert dispatch_action(ActionCommand("BUY", "MSFT", 50)) == "Standard order: Buy 50 of MSFT"
    assert dispatch_action(ActionCommand("SELL", "GOOG")) == "Liquidating GOOG"


    # ============================================================
    # 9. PATTERN MATCHING: GUARDS AND 'AS' CAPTURES
    # ============================================================
    # Guard: `if condition` evaluated after structural match succeeds
    # 'as' pattern: binds matched sub-pattern to an alias

    def classify_numbers(numbers):
        match numbers:
            # Sequence with guard checking identical values
            case [x, y] if x == y:
                return f"Identical pair of {x}"
            # Sequence with guard checking ascending order
            case [x, y] if x < y:
                return f"Ascending pair ({x}, {y})"
            # Using 'as' to capture the entire sub-sequence while extracting elements
            case [int() as first_n, *rest] as full_list if len(full_list) > 3:
                return f"Long list starting with {first_n}, length {len(full_list)}"
            case _:
                return "Unclassified"

    assert classify_numbers([5, 5]) == "Identical pair of 5"
    assert classify_numbers([3, 8]) == "Ascending pair (3, 8)"
    assert classify_numbers([10, 20, 30, 40]) == "Long list starting with 10, length 4"
    assert classify_numbers([9, 2]) == "Unclassified"


    # ============================================================
    # 10. CONSTANT MATCHING WITH DOTTED NAMES
    # ============================================================
    # Dotted names avoid the variable capture trap.

    class HttpStatus:
        OK = 200
        NOT_FOUND = 404

    def check_http_constant(status_val):
        match status_val:
            case HttpStatus.OK:
                return "Status is OK"
            case HttpStatus.NOT_FOUND:
                return "Status is Not Found"
            case _:
                return "Other Status"

    assert check_http_constant(200) == "Status is OK"
    assert check_http_constant(404) == "Status is Not Found"
    assert check_http_constant(500) == "Other Status"


if __name__ == "__main__":
    run_tests()
    print("07_unpacking_and_pattern_matching.py tests passed!")
