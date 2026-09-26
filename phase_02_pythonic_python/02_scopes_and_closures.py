"""
02_scopes_and_closures.py

============================================================
1. CONCEPT
============================================================

Variable scoping and closures in Python are governed by the LEGB rule,
compile-time scope determination, and explicit scope declarations:

1. The LEGB Resolution Hierarchy:
   When resolving an identifier, Python searches namespaces in this order:
   - L (Local): Defined inside the current function or lambda.
   - E (Enclosing): Defined in enclosing function scopes (from inner to outer).
   - G (Global): Defined at the module level or declared via `global`.
   - B (Built-in): Predefined names in the `builtins` module (e.g., `len`, `int`).

2. Compile-Time Scope Determination:
   - Python determines variable scope statically at compile time (AST phase),
     NOT dynamically at runtime.
   - If an identifier is assigned to ANYWHERE within a function, Python marks
     it as a LOCAL variable for the ENTIRE function.
   - Referencing that variable before the assignment statement raises
     `UnboundLocalError`.

3. Lack of Block Scope:
   - Python does NOT have block scope. Control constructs (`if`, `for`, `while`,
     `with`) do not create new scopes; variables assigned inside them belong
     to the enclosing function or module.
   - (Exception: The exception target in `except Exception as err:` is deleted
     at the end of the `except` block to prevent circular reference cycles).

4. Closures & Cell Objects:
   - An inner function that references variables from enclosing functions forms
     a closure.
   - CPython stores captured variables inside `cell` objects accessed via
     the function's `__closure__` attribute.

5. Scope Re-binding: `global` and `nonlocal`:
   - Reading an outer variable works automatically.
   - Re-binding an outer variable requires an explicit keyword:
     - `nonlocal`: Re-binds in the nearest enclosing non-global scope (PEP 3104).
     - `global`: Re-binds at module level.

6. The Late Binding Trap:
   - Python closures bind variables by reference to the cell, NOT by value.
   - Creating closures inside loops causes all closures to observe the
     terminal value of the loop variable unless defensively bound.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Block Scoping                | NO: `if`/`for` leak into function  | YES: `let` and `const`             |
| Function Scoping             | Standard (`def`)                   | `var` and `function`               |
| Scope Lookup Order           | LEGB                               | Lexical scope chain + Global       |
| Enclosing Mutation           | Requires `nonlocal` keyword        | Direct reassignment supported      |
| Global Mutation              | Requires `global` keyword          | Direct assignment to `window`/`global`|
| Compile-Time Scope Binding   | Any assignment marks var as local  | Hoisting (with Temporal Dead Zone) |
| Inspecting Scope             | `locals()`, `globals()`, `vars()`  | No direct programmatic dictionary  |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Scope Differences:
1. Block Scoping:
   JS:     `if (true) { let x = 10; } console.log(x);` -> ReferenceError
   Python: `if True: x = 10; print(x)` -> Prints 10!

2. Re-assigning Outer Closure Variables:
   In JS, an inner arrow function or nested function can reassign an outer `let`
   variable directly without any keyword.
   In Python, assigning to an outer variable without `nonlocal` silently creates
   a new local variable that shadows the outer one!


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. Fast Locals (`LOAD_FAST` and `STORE_FAST`):
   - In functions, local variables are not stored in a dictionary.
   - CPython allocates a fixed C array (`co_fastlocal`) on the stack frame.
   - Local access is indexed by integer offset, achieving pure $O(1)$ C pointer
     lookups.

2. Enclosing Variables & Cell Objects (`PyCellObject`):
   - When a variable is shared between an enclosing function and an inner closure,
     CPython allocates a `PyCellObject` struct on the heap:
     ```c
     typedef struct {
         PyObject_HEAD
         PyObject *ob_ref; // Pointer to the contained object
     } PyCellObject;
     ```
   - Both the outer and inner stack frames access this shared cell using
     `LOAD_DEREF` and `STORE_DEREF` bytecode opcodes.
   - The cell persists on the heap even after the outer function stack frame returns!

3. `locals()` vs `globals()`:
   - `globals()` returns the actual live dictionary of the module (`__dict__`).
     Mutations to `globals()["x"] = 5` directly alter the module's global state.
   - `locals()` inside a function dynamically constructs a snapshot dictionary
     from the `co_fastlocal` array. Mutating `locals()["x"] = 5` inside a function
     DOES NOT alter the local variable!


============================================================
4. COMMON GOTCHAS
============================================================

1. The Classic `UnboundLocalError`:
   - Occurs when reading a global or enclosing variable before assigning to it
     in the same function.
   - Since the presence of an assignment marks the variable as local for the
     entire function scope, the read fails.

2. The Late Binding Loop Trap:
   - `funcs = [lambda: i for i in range(3)]`
   - Invoking `funcs[0]()` returns `2`, NOT `0`!
   - Because all three lambdas reference the exact same `i` variable cell.
   - Fix: Use default parameter evaluation: `[lambda i=i: i for i in range(3)]`.

3. Modifying `locals()` in Functions Does Nothing:
   - Attempting to dynamically inject local variables using `locals()[var] = val`
     fails silently because CPython reads from `co_fastlocal`, not the dictionary.

4. Shadowing Built-in Identifiers:
   - Assigning `list = [1, 2, 3]` or `dict = {}` shadows the built-in constructors.
   - Subsequent calls like `list("abc")` raise `TypeError: 'list' object is not callable`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the LEGB rule and what causes an UnboundLocalError in Python."
Script:
"Python resolves variable names following the LEGB hierarchy: Local, Enclosing,
Global, and Built-in. Crucially, CPython determines the scope of every variable
statically at compile time rather than dynamically at runtime. If a variable is
assigned anywhere within a function body, CPython marks that symbol as local to the
entire function. If the function attempts to read that variable before the line of
assignment, Python does not fall back to the global or enclosing scope; instead, it
raises an `UnboundLocalError` because the local variable exists in the frame but has
not yet been bound to a value."

Q2: "How does CPython implement closures under the hood, and what is the function of PyCellObject?"
Script:
"When an inner function references a variable from an enclosing scope, CPython
identifies it as a free variable (`co_freevars`) in the inner function and a cell
variable (`co_cellvars`) in the outer function. Instead of storing the variable in the
standard fast local array, CPython allocates a `PyCellObject` on the heap. Both the
outer function and inner closure share a reference to this cell, accessing it via
`LOAD_DEREF` and `STORE_DEREF` opcodes. Because the cell resides on the heap, the inner
function retains access to the variable even after the outer function has returned and
its stack frame has been destroyed."

Q3: "What is the late-binding closure trap in Python, and what are two idiomatic ways to fix it?"
Script:
"The late-binding trap occurs when closures created inside a loop reference the loop
variable. Because Python closures bind by reference to the variable cell rather than
capturing its value at definition time, all created closures look up the variable when
they are called, observing its final terminal value. The two standard remedies are:
first, binding the current value at definition time using a default argument in the
parameter list (e.g., `lambda i=i: i`), which evaluates eagerly at creation time; and
second, using a helper factory function or `functools.partial` to create a dedicated
enclosing scope for each iteration."
"""

import builtins
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Module-level global variables for scope testing
MODULE_GLOBAL_X = "GLOBAL_X"
MODULE_COUNTER = 100


def run_tests():
    # ============================================================
    # 1. THE LEGB RESOLUTION HIERARCHY
    # ============================================================
    # Local -> Enclosing -> Global -> Built-in

    # ------------------------------------------------------------
    # Complete LEGB layered resolution
    # ------------------------------------------------------------
    global_var = "Global Layer"

    def enclosing_function():
        enclosing_var = "Enclosing Layer"

        def inner_function():
            local_var = "Local Layer"
            # Accessing Local, Enclosing, Global, and Built-in (len)
            return local_var, enclosing_var, global_var, len([1, 2])

        return inner_function()

    loc, enc, glo, b_len = enclosing_function()
    assert loc == "Local Layer"
    assert enc == "Enclosing Layer"
    assert glo == "Global Layer"
    assert b_len == 2

    # ------------------------------------------------------------
    # Built-in scope access
    # ------------------------------------------------------------
    assert abs(-42) == 42
    assert builtins.abs(-42) == 42


    # ============================================================
    # 2. COMPILE-TIME SCOPE DETERMINATION & UNBOUNDLOCALERROR
    # ============================================================
    # Python statically inspects assignments at compile time.

    # ------------------------------------------------------------
    # UnboundLocalError demonstration
    # ------------------------------------------------------------
    shadowed_val = 50

    def cause_unbound_error():
        # Even though shadowed_val exists in outer scope,
        # the assignment `shadowed_val = 20` below makes it local!
        read_val = shadowed_val  # Raises UnboundLocalError
        shadowed_val = 20
        return read_val

    error_caught = False
    try:
        cause_unbound_error()
    except UnboundLocalError:
        error_caught = True
    assert error_caught is True


    # ============================================================
    # 3. LACK OF BLOCK SCOPE & THE EXCEPTION TARGET EXCEPTION
    # ============================================================

    # ------------------------------------------------------------
    # 'if' blocks do not create scope
    # ------------------------------------------------------------
    if True:
        created_in_if = "I survived the block!"
    assert created_in_if == "I survived the block!"

    # ------------------------------------------------------------
    # 'for' loop variable leakage
    # ------------------------------------------------------------
    for loop_index in range(5):
        pass
    assert loop_index == 4  # Holds final value

    # ------------------------------------------------------------
    # PEP 3110 Exception: 'except as err' target is cleaned up!
    # Python explicitly deletes the bound exception name at the end
    # of the except block to break circular reference tracebacks.
    # ------------------------------------------------------------
    try:
        raise ValueError("Intentional error for test")
    except ValueError as caught_err:
        assert str(caught_err) == "Intentional error for test"

    # caught_err is deleted from local scope after except block!
    err_deleted = False
    try:
        _ = caught_err
    except UnboundLocalError:
        err_deleted = True
    assert err_deleted is True


    # ============================================================
    # 4. CLOSURES AND THE CELL OBJECT MODEL
    # ============================================================
    # Free variables are stored in `__closure__` as PyCellObject.

    # ------------------------------------------------------------
    # Creating a closure
    # ------------------------------------------------------------
    def make_multiplier(factor):
        def multiply(x):
            return x * factor  # 'factor' is captured
        return multiply

    times_three = make_multiplier(3)
    assert times_three(10) == 30

    # ------------------------------------------------------------
    # Inspecting closure cells
    # ------------------------------------------------------------
    assert times_three.__closure__ is not None
    assert len(times_three.__closure__) == 1
    cell = times_three.__closure__[0]
    assert cell.cell_contents == 3
    assert times_three.__code__.co_freevars == ("factor",)


    # ============================================================
    # 5. RE-BINDING ENCLOSING VARIABLES: 'nonlocal'
    # ============================================================
    # Re-binds identifiers in nearest enclosing function scope.

    # ------------------------------------------------------------
    # Stateful accumulator using nonlocal
    # ------------------------------------------------------------
    def make_bank_account(initial_balance):
        balance = initial_balance

        def deposit(amount):
            nonlocal balance
            balance += amount
            return balance

        def withdraw(amount):
            nonlocal balance
            if amount > balance:
                raise ValueError("Insufficient funds")
            balance -= amount
            return balance

        def get_balance():
            return balance

        return deposit, withdraw, get_balance

    deposit_fn, withdraw_fn, balance_fn = make_bank_account(100)
    assert balance_fn() == 100
    assert deposit_fn(50) == 150
    assert withdraw_fn(30) == 120
    assert balance_fn() == 120

    # ------------------------------------------------------------
    # Running average accumulator
    # ------------------------------------------------------------
    def make_averager():
        total = 0.0
        count = 0
        def averager(new_value):
            nonlocal total, count
            total += new_value
            count += 1
            return total / count
        return averager

    avg = make_averager()
    assert avg(10) == 10.0
    assert avg(20) == 15.0
    assert avg(30) == 20.0


    # ============================================================
    # 6. RE-BINDING MODULE VARIABLES: 'global'
    # ============================================================

    def update_module_counter(delta):
        global MODULE_COUNTER
        MODULE_COUNTER += delta

    assert MODULE_COUNTER == 100
    update_module_counter(25)
    assert MODULE_COUNTER == 125


    # ============================================================
    # 7. THE LATE BINDING CLOSURE TRAP IN LOOPS
    # ============================================================

    # ------------------------------------------------------------
    # The Trap: All lambdas capture the SAME variable cell
    # ------------------------------------------------------------
    trapped_callables = [lambda: i for i in range(4)]
    # At loop termination, i == 3. Every callable returns 3!
    assert [f() for f in trapped_callables] == [3, 3, 3, 3]

    # ------------------------------------------------------------
    # Fix 1: Default argument binding (evaluated eagerly at def time)
    # ------------------------------------------------------------
    fixed_with_defaults = [lambda i=i: i for i in range(4)]
    assert [f() for f in fixed_with_defaults] == [0, 1, 2, 3]

    # ------------------------------------------------------------
    # Fix 2: Helper factory function creating separate stack frames
    # ------------------------------------------------------------
    def make_evaluator(val):
        return lambda: val

    fixed_with_factory = [make_evaluator(i) for i in range(4)]
    assert [f() for f in fixed_with_factory] == [0, 1, 2, 3]


    # ============================================================
    # 8. SCOPE INTROSPECTION: locals(), globals(), vars()
    # ============================================================

    # ------------------------------------------------------------
    # globals() returns live dictionary
    # ------------------------------------------------------------
    glob_dict = globals()
    assert "MODULE_GLOBAL_X" in glob_dict
    assert glob_dict["MODULE_GLOBAL_X"] == "GLOBAL_X"

    # ------------------------------------------------------------
    # locals() in a function is a snapshot: mutations do NOT affect locals
    # ------------------------------------------------------------
    def test_locals_mutation():
        test_var = "original"
        locs = locals()
        assert locs["test_var"] == "original"
        locs["test_var"] = "mutated"  # Attempt to mutate local via dictionary
        return test_var  # Still returns 'original' because CPython uses co_fastlocal!

    assert test_locals_mutation() == "original"


if __name__ == "__main__":
    run_tests()
    print("02_scopes_and_closures.py tests passed!")
