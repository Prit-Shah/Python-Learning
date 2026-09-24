"""
Phase 1: Python Fundamentals - Variables, Dynamic/Strong Typing & CPython Object Model
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Dynamic Typing: Variables are labels bound to objects, not fixed memory slots.
   - Strong Typing: Python forbids implicit coercion across types (no 1 + '2' -> '12').
   - JS Analogy:
     * Python 'None' is a singleton object of type 'NoneType' (combines JS null & undefined).
     * Python has NO 'const' or 'let'. Rebinding is always allowed.
     * In JS: Boolean([]) === true. In Python: bool([]) is FALSE (empty collections are falsy!).

2. UNDER THE HOOD (CPython & Memory):
   - Every object in CPython is a 'PyObject' with:
     1) ob_refcnt (reference count for automatic memory reclamation)
     2) ob_type (pointer to the type descriptor)
   - 'id(x)' returns the virtual memory address of the PyObject.
   - Small Integer Cache: CPython pre-allocates integers from -5 to 256.

3. COMMON GOTCHA:
   - Using 'is' instead of '==' for value comparisons!
   - 'is' checks pointer identity (id(a) == id(b)).
   - '==' checks value equality (a.__eq__(b)).

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Python handle memory and variable assignment compared to JavaScript,
       and what is the fundamental difference between '==' and 'is'?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Core Model:
      "In Python, variables are not memory containers holding values; they are names
       (pointers) bound to PyObjects on the heap. When you write 'b = a', both names
       point to the exact same object in memory, incrementing its reference count."
   2. The '==' vs 'is' Distinction:
      "Because of this pointer model, Python provides two distinct comparison operators:
       - '==' checks VALUE equality by delegating to the object's __eq__() method.
       - 'is' checks IDENTITY equality, testing if both variables share the identical
         memory address (id(a) == id(b))."
   3. The Senior Gotcha (Small Int Interning):
      "A classic screening trap is checking numbers with 'is'. CPython pre-allocates
       small integers between -5 and 256. So '256 is 256' evaluates to True, but
       '1000 is 1000' can evaluate to False because they are distinct heap objects.
       Therefore, the production rule is: NEVER use 'is' for values. Use 'is' ONLY
       for singletons like 'None', 'True', and 'False'."
================================================================================
"""

import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_cpython_memory_model():
    print("\n--- 1. CPython Object Model & Pointer Rebinding ---")
    
    # In CPython, variable assignment binds a name to an object on the heap
    a = 1000
    b = a
    print(f"  a = {a}, id(a) = {hex(id(a))}")
    print(f"  b = {b}, id(b) = {hex(id(b))}")
    print(f"  Do 'a' and 'b' share identical memory address? {a is b}")
    
    # Rebinding 'a' allocates a new object; 'b' stays pointing to the original
    a = a + 1
    print(f"  After 'a = a + 1':")
    print(f"  a = {a}, id(a) = {hex(id(a))}")
    print(f"  b = {b}, id(b) = {hex(id(b))}")
    print(f"  Are 'a' and 'b' still identical? {a is b}")


def demonstrate_small_integer_cache():
    print("\n--- 2. CPython Small Integer Interning Trap (Interview Focus) ---")
    # CPython pre-allocates small ints [-5, 256] globally
    x = 250 + 6
    y = 256
    print(f"  256 is 256? {x is y} (Cached by CPython runtime)")
    
    # Above 256, separate objects are allocated when evaluated in different scopes
    p = int("1000")
    q = int("1000")
    print(f"  1000 == 1000 (Value equality)?   {p == q}")
    print(f"  1000 is 1000 (Identity equality)? {p is q} (Distinct heap objects!)")


def demonstrate_truthiness_contrast_with_js():
    print("\n--- 3. Truthiness: Python vs JavaScript Trap ---")
    # MAJOR JS GOTCHA: In JavaScript, Boolean([]) and Boolean({}) are TRUE.
    # In Python, ALL empty collections are explicitly FALSY!
    empty_list = []
    empty_dict = {}
    empty_str = ""
    
    print(f"  bool([]) -> {bool(empty_list)} (In JS: Boolean([]) is true!)")
    print(f"  bool({{}}) -> {bool(empty_dict)} (In JS: Boolean({{}}) is true!)")
    print(f"  bool('') -> {bool(empty_str)}")
    
    # Idiomatic Python style:
    items = []
    if not items:
        print("  Idiomatic Python: 'if not items:' correctly detects empty list!")


def demonstrate_strong_typing():
    print("\n--- 4. Strong Typing Enforcement ---")
    try:
        _ = 10 + "20"
    except TypeError as e:
        print(f"  TypeError raised as expected: {e}")
        print("  Explicit cast required: 10 + int('20') ->", 10 + int("20"))


# ==============================================================================
# SELF-TEST CHALLENGES (Run this script to verify your solutions!)
# ==============================================================================

def normalize_input(val):
    """
    Challenge 1:
    - If val is None or an empty collection/string (falsy), return 'EMPTY'.
    - If val is a number (int or float), return its square.
    - If val is a string, return it stripped of whitespace in uppercase.
    - Otherwise, return str(val).
    """
    if val is None or (hasattr(val, '__len__') and len(val) == 0):
        return 'EMPTY'
    if isinstance(val, bool):  # Note: bool is a subclass of int in Python!
        return 'EMPTY' if not val else 1
    if isinstance(val, (int, float)):
        return val ** 2
    if isinstance(val, str):
        stripped = val.strip().upper()
        return stripped if stripped else 'EMPTY'
    return str(val)


def run_tests():
    print("\n[*] Running automated self-tests...")
    assert normalize_input(None) == 'EMPTY', "None must evaluate to EMPTY"
    assert normalize_input([]) == 'EMPTY', "Empty list must evaluate to EMPTY"
    assert normalize_input('') == 'EMPTY', "Empty string must evaluate to EMPTY"
    assert normalize_input(4) == 16, "4 squared must be 16"
    assert normalize_input(2.5) == 6.25, "2.5 squared must be 6.25"
    assert normalize_input('  hello  ') == 'HELLO', "String must be stripped & uppercase"
    print("[SUCCESS] All automated self-tests passed cleanly!")


if __name__ == '__main__':
    print('=' * 65)
    print('Execution: Phase 1 - CPython Object Model & Fundamentals')
    print('=' * 65)
    demonstrate_cpython_memory_model()
    demonstrate_small_integer_cache()
    demonstrate_truthiness_contrast_with_js()
    demonstrate_strong_typing()
    print('-' * 65)
    run_tests()
    print('=' * 65)
