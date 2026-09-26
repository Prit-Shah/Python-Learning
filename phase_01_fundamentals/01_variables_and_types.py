"""
01_variables_and_types.py

============================================================
1. CONCEPT
============================================================

Python is a dynamically-typed, strongly-typed programming language.

    - Dynamically Typed: Variables do not have fixed types;
      they are labels (references) pointing to objects in memory.
      You can rebind a variable to any type at any time.

    - Strongly Typed: Python strictly forbids implicit type coercion
      across incompatible types. For instance, `1 + "2"` raises a
      TypeError instead of coercing `"2"` to a number or `1` to a string.

Core Built-in Primitive Types:
    - int       : Arbitrary-precision integers (no 32-bit/64-bit overflow)
    - float     : IEEE 754 double-precision floating-point numbers
    - bool      : Boolean values (True and False, sub-type of int)
    - NoneType  : Singleton object `None` representing absence of value
    - str       : Immutable sequences of Unicode characters

============================================================
2. JS / TS ANALOGY
============================================================

1. Variable Declaration:
   JavaScript:
       let x = 10;
       const y = 20;

   Python:
       x = 10   # No let/const keywords. Rebinding is always allowed.
       # Constants are indicated by convention only (UPPER_CASE).

2. Strong Typing vs Coercion:
   JavaScript (Weak typing):
       1 + "2"   // -> "12" (implicit coercion)
       "5" - 2   // -> 3

   Python (Strong typing):
       1 + "2"   # -> TypeError: unsupported operand type(s)
       int("5") - 2  # -> 3 (explicit conversion required)

3. None vs null / undefined:
   JavaScript has both `null` and `undefined`.
   Python has a single sentinel object: `None` (type `NoneType`).

4. Truthiness of Collections:
   JavaScript:
       Boolean([])   // -> true
       Boolean({})   // -> true

   Python:
       bool([])      # -> False (ALL empty collections are falsy!)
       bool({})      # -> False

5. Equality vs Identity:
   JavaScript:
       x === y       // Strict equality (checks value and type)

   Python:
       x == y        // Checks VALUE equality (calls __eq__)
       x is y        // Checks MEMORY IDENTITY (pointer address equality)

============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyObject Header:
   Every object in CPython has an internal structure `PyObject` containing:
       - `ob_refcnt`: Reference counter for garbage collection.
       - `ob_type`: Pointer to the object's type descriptor.
   Variable assignment (`b = a`) does NOT copy memory. It simply creates
   another pointer to the same PyObject and increments `ob_refcnt`.

2. Small Integer Cache (Interning):
   CPython pre-allocates an array of small integer objects for values
   between -5 and 256 at interpreter startup.
   Any integer in that range reuses the exact same PyObject pointer.
   Integers outside that range allocate fresh heap memory.

3. Arbitrary-Precision Integers:
   Unlike JS numbers (which are double-precision floats up to 2^53 - 1)
   or C (int32/int64), Python 3 integers have unbounded size,
   limited only by available system RAM.

============================================================
4. COMMON GOTCHAS
============================================================

1. Using `is` for value comparison:
   Bad:   `if x is 1000:`  # Can fail randomly for numbers outside -5..256
   Good:  `if x == 1000:`
   Rule:  Use `is` ONLY for singletons like `None`, `True`, `False`.

2. Modifying immutable types:
   Numbers, floats, bools, and strings are immutable. Any operation
   like `x += 1` creates a brand new integer object and rebinds `x`.

3. Float representation inaccuracies:
   `0.1 + 0.2` in binary floating point is `0.30000000000000004`.
   Use `math.isclose()` for float comparisons in production.

============================================================
5. INTERVIEW RESPONSE
============================================================

Q: "Explain how Python handles variable assignment and memory compared to JavaScript,
    and why '==' and 'is' are fundamentally different."

Answer:
"In Python, variables are names or pointers bound to heap-allocated PyObjects,
not fixed memory boxes. When you write b = a, both variables point to the identical
object in memory, incrementing its reference count.

Because of this, Python provides two distinct operators:
- '==' tests value equality by invoking the object's __eq__() method.
- 'is' tests object identity, checking if id(a) == id(b) (same memory address).

A classic senior interview gotcha is integer caching: CPython interns integers
from -5 to 256 globally. So 256 is 256 evaluates to True, but 1000 is 1000 can
evaluate to False because they are separate heap allocations. Therefore, the production
rule is: never use 'is' for values; use 'is' only for singletons like None."

============================================================
"""

import sys
import math

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_tests():

    # ============================================================
    # 1. INTEGERS (int)
    # ============================================================
    # - Arbitrary precision (no overflow)
    # - Supports binary, octal, hex representations
    # - Built-in methods like bit_length()
    # ============================================================

    a = 42

    assert type(a) is int
    assert isinstance(a, int)

    # Basic Arithmetic
    assert a + 8 == 50
    assert a - 2 == 40
    assert a * 2 == 84

    # True Division (/) always returns a float
    assert 10 / 2 == 5.0
    assert type(10 / 2) is float

    # Floor Division (//) truncates to integer
    assert 10 // 3 == 3
    assert -10 // 3 == -4  # Rounds towards negative infinity!

    # Modulo (%)
    assert 10 % 3 == 1

    # Exponentiation (**)
    assert 2 ** 8 == 256

    # ------------------------------------------------------------
    # Arbitrary Precision (No Overflow!)
    # In JS, Number.MAX_SAFE_INTEGER is 9007199254740991 (2^53 - 1).
    # Python ints grow automatically as large as memory permits.
    # ------------------------------------------------------------

    huge_number = 2 ** 100
    assert huge_number == 1267650600228229401496703205376
    assert (huge_number + 1) - huge_number == 1

    # ------------------------------------------------------------
    # Number Base Literals & Underscores
    # ------------------------------------------------------------

    # Underscores for visual readability
    one_million = 1_000_000
    assert one_million == 1000000

    # Binary (0b), Octal (0o), Hexadecimal (0x)
    binary_val = 0b1010       # 10 in binary
    octal_val = 0o12          # 10 in octal
    hex_val = 0x0A            # 10 in hex

    assert binary_val == 10
    assert octal_val == 10
    assert hex_val == 10

    # Bit length
    assert (16).bit_length() == 5   # 16 is 10000 in binary (5 bits)
    assert (255).bit_length() == 8  # 255 is 11111111 in binary (8 bits)


    # ============================================================
    # 2. FLOATING-POINT NUMBERS (float)
    # ============================================================
    # - Implemented as C double (IEEE 754 64-bit)
    # - Subject to standard binary floating-point representation limits
    # ============================================================

    f = 3.14159

    assert type(f) is float
    assert isinstance(f, float)

    # Scientific notation
    sci = 1.5e-3
    assert sci == 0.0015

    # ------------------------------------------------------------
    # Float Precision Gotcha & math.isclose()
    # ------------------------------------------------------------

    # 0.1 + 0.2 cannot be represented exactly in binary float
    result = 0.1 + 0.2
    assert result != 0.3
    assert abs(result - 0.3) < 1e-9

    # Production way to compare floats: math.isclose
    assert math.isclose(0.1 + 0.2, 0.3)

    # ------------------------------------------------------------
    # Infinity and NaN
    # ------------------------------------------------------------

    pos_inf = float("inf")
    neg_inf = float("-inf")
    not_a_num = float("nan")

    assert pos_inf > 10**12
    assert neg_inf < -10**12
    assert math.isinf(pos_inf)
    assert math.isnan(not_a_num)

    # NaN is NEVER equal to anything, including itself (same as JS!)
    assert not_a_num != not_a_num
    assert not (not_a_num == not_a_num)

    # ------------------------------------------------------------
    # Float Inspection Methods
    # ------------------------------------------------------------

    assert (4.0).is_integer() is True
    assert (4.5).is_integer() is False

    # Ratio representation
    numerator, denominator = (0.75).as_integer_ratio()
    assert numerator == 3 and denominator == 4


    # ============================================================
    # 3. BOOLEANS (bool)
    # ============================================================
    # - True and False
    # - In Python, bool is an explicit subclass of int!
    # - True == 1 and False == 0
    # ============================================================

    t = True
    f = False

    assert type(t) is bool
    assert isinstance(t, int)   # bool inherits from int!
    assert issubclass(bool, int)

    # Arithmetic with booleans (because True == 1, False == 0)
    assert True + True == 2
    assert False * 10 == 0
    assert True == 1
    assert False == 0

    # But identity is preserved for True and False singletons
    assert (True is 1) is False
    assert (False is 0) is False

    # ------------------------------------------------------------
    # Truthiness Rules (Falsy values in Python)
    # The following are ALL Falsy:
    #   - None
    #   - False
    #   - Zero of any numeric type: 0, 0.0, 0j
    #   - Empty sequences: "", (), []
    #   - Empty mappings / sets: {}, set()
    # ------------------------------------------------------------

    assert bool(None) is False
    assert bool(0) is False
    assert bool(0.0) is False
    assert bool("") is False
    assert bool([]) is False     # Major JS contrast! In JS: Boolean([]) is true
    assert bool(()) is False
    assert bool({}) is False     # Major JS contrast! In JS: Boolean({}) is true
    assert bool(set()) is False

    # Truthy values:
    assert bool(1) is True
    assert bool(-1) is True      # Any non-zero number is truthy
    assert bool("hello") is True
    assert bool([0]) is True     # Non-empty list containing 0 is TRUTHY!
    assert bool({"a": 1}) is True


    # ============================================================
    # 4. NoneType (None)
    # ============================================================
    # - The single null object in Python
    # - Represents absence of value or default argument placeholder
    # - Always check using `is None` or `is not None`
    # ============================================================

    empty_val = None

    assert type(empty_val) is type(None)
    assert empty_val is None
    assert (empty_val is not None) is False

    # Why use 'is' for None?
    # 'is' checks pointer identity; it cannot be overridden by user classes.
    # '==' invokes __eq__ which could theoretically be subverted.
    class CustomObj:
        def __eq__(self, other):
            return True  # Maliciously says it equals everything

    malicious = CustomObj()
    assert (malicious == None) is True   # Caught by bad ==
    assert (malicious is None) is False  # Safe check with 'is'!


    # ============================================================
    # 5. TYPE CASTING & CONVERSION
    # ============================================================

    # String to int
    assert int("123") == 123
    assert int("1010", base=2) == 10
    assert int("ff", base=16) == 255

    # String to float
    assert float("3.14") == 3.14

    # Float to int (truncates towards zero, does not round)
    assert int(3.99) == 3
    assert int(-3.99) == -3

    # Number to string
    assert str(42) == "42"
    assert str(3.14) == "3.14"
    assert str(True) == "True"
    assert str(None) == "None"

    # Conversion failures raise ValueError
    try:
        int("not_a_number")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


    # ============================================================
    # 6. CPYTHON MEMORY MODEL: 'is' vs '==' & POINTERS
    # ============================================================

    # Two variables pointing to the same object
    x = [1, 2, 3]
    y = x

    assert x == y    # Value equality
    assert x is y    # Memory identity (id(x) == id(y))
    assert id(x) == id(y)

    # Creating a clone: same value, DIFFERENT memory address
    z = [1, 2, 3]
    assert x == z    # Values are identical
    assert x is not z  # Different heap objects!
    assert id(x) != id(z)

    # ------------------------------------------------------------
    # Small Integer Interning Cache (-5 to 256)
    # ------------------------------------------------------------

    small_1 = 200
    small_2 = 200
    assert small_1 is small_2  # Cached by CPython interpreter

    # Values constructed at runtime above 256 may not share identity
    large_1 = int("1000")
    large_2 = int("1000")
    assert large_1 == large_2      # Values are equal
    assert large_1 is not large_2  # Distinct heap allocations!


    # ============================================================
    # 7. STRONG TYPING IN ACTION (NO IMPLICIT COERCION)
    # ============================================================

    # TypeError when mixing incompatible types
    try:
        result = "Count: " + 5
        assert False, "Should raise TypeError"
    except TypeError:
        pass

    try:
        result = 10 + "20"
        assert False, "Should raise TypeError"
    except TypeError:
        pass

    # Explicit conversion succeeds
    assert "Count: " + str(5) == "Count: 5"
    assert 10 + int("20") == 30


# ================================================================
# MAIN
# ================================================================

if __name__ == '__main__':
    run_tests()
    print("01_variables_and_types.py tests passed!")
