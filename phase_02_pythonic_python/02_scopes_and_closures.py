"""
1. CONCEPT & JS/TS ANALOGY
LEGB rule: Local, Enclosing, Global, Built-in scope resolution order.
No block scope (variables from if/for leak into function scope).
Closures: inner functions capturing outer variables.
nonlocal and global keywords for rebinding outer variables.

JS Analogy:
In JS, `var` is function-scoped (like Python variables), but `let`/`const` are block-scoped. Python has no block scope.
In JS, inner functions capture outer variables and can mutate them directly. In Python, an inner function can *read* outer variables or mutate mutable objects they point to, but to *rebind* an outer primitive, you must use `nonlocal` (or `global`).

2. UNDER THE HOOD (CPython & Memory)
Scopes are implemented as dictionaries mapping names to objects.
`locals()` and `globals()` return these dictionaries.
A closure is a function object with a `__closure__` attribute: a tuple of cell objects. These cells reference the captured variables.

3. COMMON GOTCHA
Late binding in closures with loops. E.g., `[lambda: i for i in range(3)]`. Since `i` is not block-scoped, all lambdas reference the same `i`, which is `2` after the loop.
Also, variables defined inside an `if` or `for` statement are perfectly accessible outside the block in the same function.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "Explain Python scoping rules and how closures work differently from JavaScript."
A: "Python uses the LEGB rule for scoping: Local, Enclosing, Global, and Built-in. Unlike JS which has block scope with let/const, Python variables defined in control blocks like if or for statements leak into the surrounding function scope.
For closures, both languages allow inner functions to capture outer variables. However, if you want to reassign a captured immutable variable in Python, you must explicitly declare it with the 'nonlocal' keyword, whereas JavaScript allows direct reassignment. Without 'nonlocal', Python will simply create a new local variable shadowing the outer one."

5. Self-tests
See run_tests()
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_legb_scope():
    print("--- LEGB Scope ---")
    x = "Global"
    def outer():
        x = "Enclosing"
        def inner():
            x = "Local"
            print(f"Inner sees: {x}")
        inner()
        print(f"Outer sees: {x}")
    outer()
    print(f"Global sees: {x}")

def demonstrate_no_block_scope():
    print("\n--- No Block Scope ---")
    if True:
        no_block = "I exist outside the if block!"
    print(no_block)
    
    for i in range(3):
        pass
    print(f"Loop counter i is accessible after loop: {i}")

def demonstrate_closures_and_nonlocal():
    print("\n--- Closures and nonlocal ---")
    def counter():
        count = 0
        def increment():
            nonlocal count
            count += 1
            return count
        return increment
        
    c = counter()
    print(f"Count 1: {c()}")
    print(f"Count 2: {c()}")

def demonstrate_late_binding_trap():
    print("\n--- Late Binding Trap ---")
    # Trap: All lambdas capture the SAME 'i', which is 2 at the end of the loop
    trapped_funcs = [lambda: i for i in range(3)]
    print(f"Trapped results: {[f() for f in trapped_funcs]}")
    
    # Fix: Bind 'i' at creation time using a default argument
    fixed_funcs = [lambda i=i: i for i in range(3)]
    print(f"Fixed results: {[f() for f in fixed_funcs]}")

def run_tests():
    # Test nonlocal
    def outer():
        x = 1
        def inner():
            nonlocal x
            x = 2
        inner()
        return x
    assert outer() == 2
    
    # Test late binding fix
    funcs = [lambda x=x: x for x in range(3)]
    assert [f() for f in funcs] == [0, 1, 2]
    
    print("\nAll scope tests passed!")

if __name__ == '__main__':
    demonstrate_legb_scope()
    demonstrate_no_block_scope()
    demonstrate_closures_and_nonlocal()
    demonstrate_late_binding_trap()
    run_tests()
