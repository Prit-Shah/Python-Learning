"""
02_strings_and_fstrings.py

============================================================
1. CONCEPT
============================================================

Strings (`str`) in Python are immutable sequences of Unicode characters.

Key Properties:
    - Immutable: Cannot be modified in-place once created.
    - Indexed: Zero-based positive indexing and negative indexing from the end.
    - Iterable: Can be looped over character by character.
    - Rich Built-in API: Comprehensive methods for transformation, search,
      splitting, joining, and validation.
    - f-Strings (Formatted String Literals): Evaluated at runtime, providing
      high-speed, highly-readable string interpolation and formatting.

============================================================
2. JS / TS ANALOGY
============================================================

1. Template Literals vs f-Strings:
   JavaScript:
       `Hello, ${name}! Total: $${price.toFixed(2)}`

   Python:
       f"Hello, {name}! Total: ${price:.2f}"

2. String Slicing:
   JavaScript:
       str.slice(0, 3)
       str.slice(-3)

   Python:
       str[0:3]
       str[-3:]
       str[::-1]   # Reverses string (No direct JS slice syntax)

3. Joining Arrays / Iterables (Crucial Difference!):
   JavaScript (Array method):
       ["a", "b", "c"].join(", ")

   Python (String method):
       ", ".join(["a", "b", "c"])
       # Why string-first in Python? Because join() works on ANY iterable
       # (lists, tuples, sets, generator expressions), not just lists!

4. Multiline Strings:
   JavaScript:
       `Line 1
        Line 2`

   Python:
       """Line 1
       Line 2"""

5. Prefix and Suffix Removal:
   JavaScript:
       str.replace(/^prefix/, "")

   Python 3.9+:
       str.removeprefix("prefix")
       str.removesuffix("suffix")

============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Flexible String Representation (PEP 393):
   CPython optimizes memory by using the smallest possible byte width
   per character depending on the characters contained in the string:
       - 1 byte per char  (Latin-1 / ASCII, up to U+00FF)
       - 2 bytes per char (UCS-2, up to U+FFFF)
       - 4 bytes per char (UCS-4, full Unicode / emojis, up to U+10FFFF)
   This saves up to 75% memory compared to fixed 4-byte Unicode strings.

2. Immutability & Reallocation:
   Because strings are immutable, repeated string concatenation using `+=`
   inside a loop allocates a new string in memory on each iteration,
   leading to O(N^2) complexity. The idiomatic Python approach is appending
   substrings to a list and joining them with `"".join(parts)` in O(N) time.

3. String Interning:
   CPython automatically interns short string literals that resemble valid
   identifiers (alphanumeric characters and underscores). Interned strings
   share the same PyObject memory address (`a is b` evaluates to True).

============================================================
4. COMMON GOTCHAS
============================================================

1. In-place modification attempt:
   `s = "hello"`
   `s[0] = "H"`  -> Raises TypeError!
   Fix: Slicing or replace: `s = "H" + s[1:]`

2. The `.strip("abc")` trap:
   `.strip()` removes ANY of the characters in the argument set from both ends,
   NOT the exact sequence!
   `"apple".strip("alep")` -> returns `""` because all letters are in the set!
   Fix for exact prefix removal: Use `.removeprefix()` (Python 3.9+).

3. `.split()` with no arguments vs `.split(" ")`:
   `"  a   b  ".split()`    -> `["a", "b"]` (collapses all consecutive whitespace)
   `"  a   b  ".split(" ")` -> `["", "", "a", "", "", "b", "", ""]`

4. `.find()` vs `.index()`:
   `.find()` returns -1 when the substring is not found.
   `.index()` raises `ValueError`.

============================================================
5. INTERVIEW RESPONSE
============================================================

Q: "What are f-strings, how do they differ under the hood from .format() and %,
    and why is ''.join() preferred over '+' in loops?"

Answer:
"f-strings, introduced in Python 3.6 and enhanced in 3.12, evaluate expressions
at runtime inside string literals. Unlike older %-formatting or str.format(),
f-strings are not parsed through a format function call at runtime; CPython compiles
them directly into specialized bytecode instructions (FORMAT_VALUE and BUILD_STRING),
making them significantly faster.

Regarding string manipulation performance: strings in Python are immutable PyObjects.
Using 's += chunk' inside a loop creates and discards intermediate string objects
at each step, producing O(N^2) time complexity and memory thrashing. The production
pattern is accumulating chunks into a list and calling ''.join(chunks), which
calculates total buffer size upfront and allocates memory in a single O(N) pass."

============================================================
"""

import sys
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_tests():

    # ============================================================
    # 1. STRING CREATION & IMMUTABILITY
    # ============================================================

    # Single, double, and multiline triple quotes
    s1 = 'hello'
    s2 = "world"
    multiline = """Line 1
Line 2"""

    assert s1 + " " + s2 == "hello world"
    assert len(multiline.splitlines()) == 2

    # Immutability: Attempting to modify a character raises TypeError
    text = "Python"
    try:
        text[0] = "J"
        assert False, "Should raise TypeError"
    except TypeError:
        pass

    # Creating a new string from existing one
    modified = "J" + text[1:]
    assert modified == "Jython"
    assert text == "Python"  # Original remains untouched


    # ============================================================
    # 2. INDEXING & SLICING [start:stop:step]
    # ============================================================
    # Syntax: text[start : stop : step]
    # - start: inclusive
    # - stop: exclusive
    # - step: step increment (default 1)
    # ============================================================

    s = "Developer"

    # Positive indexing
    assert s[0] == "D"
    assert s[3] == "e"

    # Negative indexing (from end)
    assert s[-1] == "r"
    assert s[-2] == "e"

    # Slicing
    assert s[0:3] == "Dev"
    assert s[:3] == "Dev"      # Omitting start defaults to 0
    assert s[4:] == "loper"    # Omitting stop goes to the end
    assert s[:] == "Developer" # Full copy

    # Step slicing
    assert s[::2] == "Dvlp"    # Every 2nd character

    # String reversal with negative step
    assert s[::-1] == "repoleveD"
    assert "radar"[::-1] == "radar"  # Palindrome check

    # Slice out of bounds does NOT raise IndexError (unlike direct indexing)
    assert s[0:100] == "Developer"
    assert s[50:100] == ""


    # ============================================================
    # 3. CASE TRANSFORMATIONS
    # ============================================================

    sample = "hello Python world"

    # upper() and lower()
    assert sample.upper() == "HELLO PYTHON WORLD"
    assert sample.lower() == "hello python world"

    # capitalize() -> Only first character capitalized
    assert "python programming".capitalize() == "Python programming"

    # title() -> First letter of each word capitalized
    assert "python programming language".title() == "Python Programming Language"

    # swapcase() -> Inverts casing
    assert "PyThOn".swapcase() == "pYtHoN"

    # casefold() -> Aggressive lowercase for caseless matching (handles Unicode)
    assert "der Fluß".casefold() == "der fluss"  # German ß converted to ss


    # ============================================================
    # 4. TRIMMING & STRIPPING
    # ============================================================

    # strip() removes leading and trailing whitespace
    messy = "   clean me   \n\t"
    assert messy.strip() == "clean me"
    assert messy.lstrip() == "clean me   \n\t"
    assert messy.rstrip() == "   clean me"

    # Stripping specific characters (removes any character in set from ends)
    url_messy = "...https://example.com/..."
    assert url_messy.strip(".") == "https://example.com/"

    # ------------------------------------------------------------
    # removeprefix() and removesuffix() (Python 3.9+)
    # Safely removes exact substrings without the set-based stripping trap!
    # ------------------------------------------------------------

    filename = "report_2026.pdf"
    assert filename.removesuffix(".pdf") == "report_2026"
    assert filename.removeprefix("report_") == "2026.pdf"

    # If prefix/suffix is not found, returns original copy
    assert filename.removeprefix("missing_") == "report_2026.pdf"


    # ============================================================
    # 5. SEARCHING & INSPECTION
    # ============================================================

    text = "the quick brown fox jumps over the lazy dog"

    # find() returns index of first match, or -1 if missing
    assert text.find("fox") == 16
    assert text.find("cat") == -1

    # index() returns index or raises ValueError
    assert text.index("fox") == 16
    try:
        text.index("cat")
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # rfind() and rindex() search from right to left
    assert text.find("the") == 0
    assert text.rfind("the") == 31

    # count() counts non-overlapping occurrences
    assert text.count("the") == 2
    assert "banana".count("an") == 2

    # startswith() and endswith()
    assert text.startswith("the")
    assert text.endswith("dog")

    # startswith() / endswith() with a TUPLE of allowed prefixes/suffixes!
    api_url = "https://api.github.com/v1"
    assert api_url.startswith(("http://", "https://"))
    assert "image.png".endswith((".png", ".jpg", ".jpeg", ".webp"))


    # ============================================================
    # 6. BOOLEAN CHARACTER VALIDATION METHODS
    # ============================================================

    assert "12345".isdigit() is True
    assert "123a5".isdigit() is False

    assert "Python".isalpha() is True
    assert "Python3".isalpha() is False

    assert "Python3".isalnum() is True
    assert "Python 3".isalnum() is False  # Space is not alphanumeric

    assert "   \t\n".isspace() is True
    assert "".isspace() is False

    assert "hello_world_1".isidentifier() is True
    assert "1_hello".isidentifier() is False  # Cannot start with digit


    # ============================================================
    # 7. SPLITTING, PARTITIONING & JOINING
    # ============================================================

    # split() without arguments collapses all whitespace
    line = "apple   banana\torange\npear"
    assert line.split() == ["apple", "banana", "orange", "pear"]

    # split() with explicit delimiter
    csv_row = "name,age,city"
    assert csv_row.split(",") == ["name", "age", "city"]

    # split() with maxsplit
    header = "KEY=VALUE=EXTRA"
    assert header.split("=", maxsplit=1) == ["KEY", "VALUE=EXTRA"]

    # partition() splits into a 3-tuple: (before, separator, after)
    user_email = "alice@example.com"
    username, sep, domain = user_email.partition("@")
    assert username == "alice"
    assert sep == "@"
    assert domain == "example.com"

    # join() string method
    words = ["Python", "is", "awesome"]
    assert " ".join(words) == "Python is awesome"
    assert "-".join(words) == "Python-is-awesome"
    assert "".join(words) == "Pythonisawesome"


    # ============================================================
    # 8. REPLACING & ALIGNMENT
    # ============================================================

    msg = "one fish, two fish, red fish, blue fish"
    assert msg.replace("fish", "bird") == "one bird, two bird, red bird, blue bird"

    # replace() with count limit
    assert msg.replace("fish", "bird", 2) == "one bird, two bird, red fish, blue fish"

    # zfill() pads with leading zeros
    assert "42".zfill(5) == "00042"

    # Alignment: ljust(), rjust(), center()
    word = "code"
    assert word.ljust(8, "-") == "code----"
    assert word.rjust(8, "-") == "----code"
    assert word.center(8, "*") == "**code**"


    # ============================================================
    # 9. F-STRINGS & ADVANCED FORMATTING
    # ============================================================

    name = "Prit"
    score = 98.4567

    # Expression evaluation
    assert f"Hello, {name.upper()}!" == "Hello, PRIT!"
    assert f"{2 * 21}" == "42"

    # Floating point precision: {val:.2f}
    assert f"{score:.2f}" == "98.46"
    assert f"{score:.0f}" == "98"

    # Thousands separators: {val:,} and {val:_}
    large_number = 12500000
    assert f"{large_number:,}" == "12,500,000"
    assert f"{large_number:_}" == "12_500_000"

    # Percentage formatting: {val:.1%}
    ratio = 0.8525
    assert f"{ratio:.1%}" == "85.2%"

    # Padding and alignment inside f-strings
    val = "API"
    assert f"{val:>8}" == "     API"      # Right aligned, width 8
    assert f"{val:<8}" == "API     "      # Left aligned, width 8
    assert f"{val:^7}" == "  API  "      # Center aligned, width 7
    assert f"{val:*^7}" == "**API**"      # Center with custom fill character

    # Escaping curly braces: {{ and }}
    assert f"{{hello}}" == "{hello}"

    # Self-documenting debugging f-strings (Python 3.8+): {expr=}
    x = 10
    assert f"{x=}" == "x=10"
    assert f"{x * 2=}" == "x * 2=20"


    # ============================================================
    # 10. RAW STRINGS & ESCAPE SEQUENCES
    # ============================================================

    # Standard escapes
    escaped = "Line 1\nLine 2\tTabbed"
    assert "\n" in escaped
    assert "\t" in escaped

    # Raw strings r"..." ignore escape sequences (essential for regex & file paths)
    normal_path = "C:\\new_folder\\test"
    raw_path = r"C:\new_folder\test"
    assert normal_path == raw_path

    raw_regex = r"\d+\.\d+"
    assert raw_regex == "\\d+\\.\\d+"


    # ============================================================
    # 11. STRING INTERNING (CPython Optimization)
    # ============================================================

    # Short identifier-like strings are interned automatically
    a = "python_language"
    b = "python_language"
    assert a is b  # Points to identical memory address in CPython

    # Explicit string interning with sys.intern
    s_dynamic_1 = sys.intern("dynamic_string_" + str(2026))
    s_dynamic_2 = sys.intern("dynamic_string_" + str(2026))
    assert s_dynamic_1 is s_dynamic_2


# ================================================================
# MAIN
# ================================================================

if __name__ == '__main__':
    run_tests()
    print("02_strings_and_fstrings.py tests passed!")
