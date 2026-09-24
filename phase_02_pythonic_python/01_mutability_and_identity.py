"""
1. CONCEPT & JS/TS ANALOGY
Mutable (list, dict, set) vs immutable (int, str, tuple, frozenset)
== (value equality) vs is (identity)
References: multiple names pointing to same object
Shallow vs Deep copy

JS Analogy:
In JS, primitives (number, string, boolean) are immutable. Objects/Arrays are mutable.
`===` in JS compares identity for objects, value for primitives. In Python, `is` checks memory address (identity), `==` checks value equality (via `__eq__`).
JS `const` prevents reassignment but allows mutation. Python has no `const`.
JS object spread `{...obj}` is a shallow copy. `structuredClone(obj)` is a deep copy. In Python, `list.copy()` or `copy.copy()` is shallow, `copy.deepcopy()` is deep.

2. UNDER THE HOOD (CPython & Memory)
In CPython, everything is an object (PyObject struct).
Variables are just names (pointers) bound to objects.
Small integers (-5 to 256) and short strings are cached (interned). `a = 5`, `b = 5` means `a is b` will be True.
When you mutate a list, the PyObject itself changes in place.
When you "modify" an immutable string, a completely new PyObject is created and the name is rebound to it.

3. COMMON GOTCHA
Aliasing trap: `a = [1, 2, 3]`; `b = a`; `b.append(4)`. Both `a` and `b` show `[1, 2, 3, 4]`.
Also, default mutable arguments: `def foo(lst=[]): lst.append(1)`. The default list is created ONCE at function definition time, leading to state bleeding across calls.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "Explain mutable vs immutable types in Python. What happens when you pass a list to a function?"
A: "In Python, types like int, str, and tuple are immutable, meaning their state cannot be changed after creation. Reassigning them creates a new object. Types like list, dict, and set are mutable, meaning they can be changed in-place.
When you pass a list to a function, Python uses 'pass-by-object-reference'. This means a reference to the same list object is passed, not a copy of the list, nor a reference to the variable itself. If you mutate the list inside the function (like appending an item), the caller sees the change because both caller and function reference the exact same object. However, if you reassign the list variable inside the function to a completely new list, the caller's variable remains unchanged."

5. Self-tests
See run_tests()
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import copy

def demonstrate_mutability():
    print("--- Mutability ---")
    s = "hello"
    s_id_before = id(s)
    s += " world"
    s_id_after = id(s)
    print(f"String changed? IDs match: {s_id_before == s_id_after} (Immutable creates new object)")

    lst = [1, 2, 3]
    lst_id_before = id(lst)
    lst.append(4)
    lst_id_after = id(lst)
    print(f"List changed? IDs match: {lst_id_before == lst_id_after} (Mutable changes in-place)")

def demonstrate_identity():
    print("\n--- Identity vs Equality ---")
    a = [1, 2, 3]
    b = [1, 2, 3]
    print(f"a == b? {a == b} (Value equality)")
    print(f"a is b? {a is b} (Identity)")
    
    # Integer interning
    x = 100
    y = 100
    print(f"100 is 100? {x is y} (Due to interning)")

def demonstrate_shallow_vs_deep_copy():
    print("\n--- Shallow vs Deep Copy ---")
    original = [[1, 2], [3, 4]]
    shallow = original.copy()
    deep = copy.deepcopy(original)
    
    original[0].append(99)
    print(f"Original: {original}")
    print(f"Shallow copy reflects inner list mutation: {shallow}")
    print(f"Deep copy untouched: {deep}")

def demonstrate_function_argument_passing():
    print("\n--- Pass by Object Reference ---")
    def modify(lst):
        lst.append("MUTATED")
        lst = [1, 2, 3] # Rebinding local name
        
    my_list = ["original"]
    modify(my_list)
    print(f"After function call: {my_list}")

def run_tests():
    a = [1]
    b = [1]
    assert a == b
    assert a is not b
    
    def bad_default(item, items=[]):
        items.append(item)
        return items
    assert bad_default(1) == [1]
    assert bad_default(2) == [1, 2]
    
    def good_default(item, items=None):
        items = [] if items is None else items
        items.append(item)
        return items
    assert good_default(1) == [1]
    assert good_default(2) == [2]
    
    orig = [[1]]
    shallow = copy.copy(orig)
    deep = copy.deepcopy(orig)
    orig[0].append(2)
    assert shallow == [[1, 2]]
    assert deep == [[1]]
    print("\nAll mutability tests passed!")

if __name__ == '__main__':
    demonstrate_mutability()
    demonstrate_identity()
    demonstrate_shallow_vs_deep_copy()
    demonstrate_function_argument_passing()
    run_tests()
