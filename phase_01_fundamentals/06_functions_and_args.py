"""
06_functions_and_args.py

============================================================
1. CONCEPT
============================================================

Functions in Python are first-class objects defined using the `def` keyword
(or `lambda` for single-expression anonymous functions). Python features a
rich parameter passing system:

1. Parameter Types & Order:
   Python parameters must be defined in this exact order:
   `def func(pos_only, /, standard, *args, kw_only, **kwargs):`
   - Positional-only: Before `/` (cannot be passed as keyword).
   - Standard: Positional or keyword.
   - Var-positional: `*args` (captures excess positional arguments as a tuple).
   - Keyword-only: After `*` or `*args` (must be passed by name).
   - Var-keyword: `**kwargs` (captures excess keyword arguments as a dict).

2. Return Values:
   - Python functions always return a value. If no `return` statement is
     reached, `None` is returned implicitly.
   - Returning multiple values (`return a, b`) returns a single `tuple`
     that can be unpacked at the call site.

3. First-Class Citizens:
   - Functions can be assigned to variables, passed into other functions
     (higher-order functions), returned from functions, and stored in
     collections (e.g., dispatch tables).

4. Closures & Scoping (`nonlocal` and `global`):
   - Inner functions capture variables from enclosing scopes (closures).
   - Re-binding an outer local variable requires the `nonlocal` keyword.
   - Re-binding a module-level variable requires the `global` keyword.

5. Type Hints and Introspection:
   - Function parameters and return values can be annotated with type hints.
   - Type hints are metadata stored in `__annotations__`; CPython does NOT
     enforce them at runtime without external libraries (e.g. Pydantic).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+-----------------------------------+------------------------------------+
| Feature                      | Python                            | JavaScript / TypeScript            |
+------------------------------+-----------------------------------+------------------------------------+
| Named Function               | `def my_fn(a, b):`                | `function myFn(a, b) { ... }`      |
| Anonymous Function           | `lambda x: x * 2`                 | `(x) => x * 2`                     |
| Var-positional (Rest)        | `*args` (tuple)                   | `...args` (array)                  |
| Var-keyword                  | `**kwargs` (dict)                 | `{ ...kwargs }` (object param)     |
| Default Argument Evaluation  | AT DEFINITION TIME (once!)        | AT CALL TIME (fresh evaluation)    |
| Native Keyword Args          | YES: `my_fn(port=8080)`           | NO: Simulated with object destr.   |
| Positional-only marker       | `/` (PEP 570)                     | No equivalent                      |
| Keyword-only marker          | `*` (PEP 3102)                    | No equivalent                      |
| Outer Scope Mutation         | Requires `nonlocal`               | Works natively in outer scope      |
| Return multiple values       | `return a, b` (returns tuple)     | `return [a, b]` or `return {a, b}` |
+------------------------------+-----------------------------------+------------------------------------+

Crucial JavaScript vs Python Difference: Default Parameter Timing!
- In JavaScript:
  `function add(item, list = []) { list.push(item); return list; }`
  In JS, `[]` is evaluated EVERY TIME the function is called without that arg.
  Calling `add(1)` twice gives `[1]` both times.
- In Python:
  `def add(item, list=[]): list.append(item); return list`
  In Python, `[]` is evaluated ONCE when the module loads!
  Calling `add(1)` twice gives `[1, 1]`.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyFunctionObject:
   - A `def` statement executes at runtime, creating a `PyFunctionObject` on
     the heap and binding it to the function name in the local namespace.
   - The compiled bytecode is stored in `func.__code__` (`PyCodeObject`).

2. Where Defaults Live (`__defaults__` and `__kwdefaults__`):
   - When CPython encounters `def foo(a, b=42, lst=[]):`, it evaluates the
     default expressions immediately.
   - It stores positional defaults in `foo.__defaults__` as a tuple.
   - It stores keyword-only defaults in `foo.__kwdefaults__` as a dict.
   - When `foo()` is invoked without arguments, CPython looks directly inside
     this `__defaults__` tuple. If a default object is mutable (like a list),
     in-place mutations modify the object sitting inside `foo.__defaults__`.

3. Local Variable Array (`co_fastlocal`):
   - CPython optimizes local variable access using `LOAD_FAST` and `STORE_FAST`
     opcodes, indexing directly into a fixed-size C array on the call stack frame
     rather than querying a dictionary.

4. Closures & Cell Objects (`PyCellObject`):
   - When an inner function references a variable from an enclosing scope,
     CPython wraps the variable inside a `cell` object.
   - Both the outer scope and inner scope hold pointers to the same `PyCellObject`.
   - Access is achieved via `LOAD_DEREF` and `STORE_DEREF` opcodes.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Mutable Default Argument Trap:
   - Anti-pattern: `def append_to(element, target_list=[]):`
   - Problem: `target_list` is shared across ALL invocations.
   - Idiomatic fix: Default to `None` and instantiate inside:
     ```python
     def append_to(element, target_list=None):
         if target_list is None:
             target_list = []
         target_list.append(element)
         return target_list
     ```

2. Lambda Expressions are Single Expressions Only:
   - Python lambdas CANNOT contain statements: no `return`, no assignments
     (prior to Python 3.8 walrus), no `for` loops, no `try/except`.
   - Only a single expression whose evaluated value is implicitly returned.
   - Do NOT name a lambda (`func = lambda x: x * 2`). PEP 8 mandates `def func(x):`.

3. UnboundLocalError When Re-binding Outer Variables:
   - If you assign to a variable inside an inner function without `nonlocal`,
     CPython marks it as a LOCAL variable for the ENTIRE inner function at compile time.
   - Reading it before assignment raises `UnboundLocalError`.

4. Positional vs Keyword Argument Ordering:
   - Positional arguments CANNOT follow keyword arguments at the call site.
   - `func(a=1, 2)` -> SyntaxError: positional argument follows keyword argument.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Why are mutable default arguments dangerous in Python, and how do you resolve them?"
Script:
"In Python, default parameter expressions are evaluated once when the function
definition is executed at module load time, not on each call. The evaluated
default objects are stored in the function object's `__defaults__` tuple. If a
mutable object like a list or dictionary is used as a default, every call that
omits that argument shares the exact same reference. Mutations to that parameter
persist across subsequent calls. The standard remedy is the sentinel pattern:
set the default to `None`, and inside the function body, initialize a new mutable
container if the argument is `None`."

Q2: "What is the difference between *args and **kwargs, and how are parameter markers / and * used?"
Script:
"`*args` collects arbitrary positional arguments into an immutable `tuple`, while
`**kwargs` collects arbitrary keyword arguments into a mutable `dict`.
Python also supports parameter markers: a forward slash `/` indicates that all
preceding parameters are positional-only and cannot be passed by keyword, which
allows renaming internal parameters without breaking caller contracts.
An asterisk `*` indicates that all subsequent parameters are keyword-only, forcing
callers to explicitly name arguments, which greatly improves readability for
boolean flags or optional configurations."

Q3: "How does Python handle closures and the nonlocal keyword?"
Script:
"When an inner function references an identifier from an enclosing scope, CPython
creates a closure by wrapping the variable in a `PyCellObject` shared across both
stack frames. If the inner function only reads the variable, no declaration is needed.
However, because Python uses assignment to infer scope, assigning to that variable
inside the inner function would implicitly treat it as local, causing an
`UnboundLocalError` if referenced before assignment. Declaring the variable
`nonlocal` tells CPython to re-bind the variable in the nearest enclosing non-global
scope rather than creating a local binding."
"""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Module-level variable for testing 'global' keyword
MODULE_GLOBAL_TRACKER = 0


def run_tests():
    # ============================================================
    # 1. BASIC FUNCTION DEFINITION & RETURN MECHANICS
    # ============================================================
    # Functions use `def`, optional docstring, and return values.

    # ------------------------------------------------------------
    # Implicit vs explicit return
    # If no `return` is reached, None is returned automatically
    # ------------------------------------------------------------
    def no_return_func():
        x = 10 + 20

    assert no_return_func() is None

    def explicit_return_func(a, b):
        return a + b

    assert explicit_return_func(10, 20) == 30

    # ------------------------------------------------------------
    # Multiple return values (Tuples under the hood)
    # Python packs comma-separated returns into a single tuple
    # ------------------------------------------------------------
    def min_max(numbers):
        return min(numbers), max(numbers)  # returns tuple (min, max)

    result = min_max([4, 1, 9, 2])
    assert isinstance(result, tuple)
    assert result == (1, 9)

    # Unpacking at the call site
    lowest, highest = min_max([10, 50, 30])
    assert lowest == 10
    assert highest == 50


    # ============================================================
    # 2. POSITIONAL VS KEYWORD ARGUMENTS
    # ============================================================
    # Callers can pass arguments by position or by name.

    def create_user(username, email, role="viewer"):
        return {"username": username, "email": email, "role": role}

    # Positional invocation
    u1 = create_user("alice", "alice@example.com")
    assert u1 == {"username": "alice", "email": "alice@example.com", "role": "viewer"}

    # Keyword invocation (order does not matter when named)
    u2 = create_user(email="bob@example.com", username="bob", role="admin")
    assert u2 == {"username": "bob", "email": "bob@example.com", "role": "admin"}

    # Mixed invocation: positional MUST precede keyword
    u3 = create_user("charlie", role="editor", email="charlie@example.com")
    assert u3 == {"username": "charlie", "email": "charlie@example.com", "role": "editor"}


    # ============================================================
    # 3. MUTABLE DEFAULT ARGUMENT TRAP & SENTINEL PATTERN
    # ============================================================
    # Defaults are evaluated ONCE at function definition time.

    # ------------------------------------------------------------
    # The Bug: Shared mutable default across calls
    # ------------------------------------------------------------
    def buggy_append(item, container=[]):
        container.append(item)
        return container

    call1 = buggy_append("first")
    assert call1 == ["first"]

    call2 = buggy_append("second")
    # call2 did not get a fresh list! It modified the same container:
    assert call2 == ["first", "second"]
    assert buggy_append.__defaults__[0] == ["first", "second"]

    # ------------------------------------------------------------
    # The Fix: None sentinel with lazy instantiation
    # ------------------------------------------------------------
    def safe_append(item, container=None):
        if container is None:
            container = []
        container.append(item)
        return container

    safe1 = safe_append("first")
    assert safe1 == ["first"]

    safe2 = safe_append("second")
    assert safe2 == ["second"]  # Fresh list created!
    assert safe_append.__defaults__ == (None,)


    # ============================================================
    # 4. VARIADIC ARGUMENTS (*args and **kwargs)
    # ============================================================
    # *args collects excess positional arguments into a tuple.
    # **kwargs collects excess keyword arguments into a dictionary.

    # ------------------------------------------------------------
    # *args (variable positional)
    # ------------------------------------------------------------
    def multiply_all(multiplier, *args):
        assert isinstance(args, tuple)
        return [multiplier * x for x in args]

    assert multiply_all(2, 1, 2, 3) == [2, 4, 6]
    assert multiply_all(10) == []  # args is an empty tuple ()

    # ------------------------------------------------------------
    # **kwargs (variable keyword)
    # ------------------------------------------------------------
    def build_query(endpoint, **kwargs):
        assert isinstance(kwargs, dict)
        params = [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return f"{endpoint}?{'&'.join(params)}" if params else endpoint

    assert build_query("/api/users", page=1, limit=20) == "/api/users?limit=20&page=1"
    assert build_query("/api/health") == "/api/health"

    # ------------------------------------------------------------
    # Argument forwarding / Proxying
    # Forwarding *args and **kwargs to an underlying function
    # ------------------------------------------------------------
    def raw_calculator(a, b, operation="add"):
        return a + b if operation == "add" else a - b

    def logged_calculator(*args, **kwargs):
        # Intercept / log then forward
        return raw_calculator(*args, **kwargs)

    assert logged_calculator(10, 5) == 15
    assert logged_calculator(10, 5, operation="sub") == 5

    # ------------------------------------------------------------
    # Call-site unpacking with * and **
    # ------------------------------------------------------------
    nums = [10, 20]
    assert raw_calculator(*nums) == 30

    options = {"b": 7, "operation": "sub"}
    assert raw_calculator(15, **options) == 8


    # ============================================================
    # 5. PARAMETER DELIMITERS: POSITIONAL-ONLY (/) AND KEYWORD-ONLY (*)
    # ============================================================
    # Introduced in PEP 570 (/) and PEP 3102 (*).

    # ------------------------------------------------------------
    # Positional-Only parameters: Before '/'
    # Must be supplied positionally, cannot be supplied by name
    # ------------------------------------------------------------
    def pos_only_demo(x, y, /, standard_param):
        return x + y + standard_param

    # Valid: x and y positional, standard_param positional or keyword
    assert pos_only_demo(1, 2, 3) == 6
    assert pos_only_demo(1, 2, standard_param=3) == 6

    # Invalid: passing x or y by keyword raises TypeError
    pos_error_raised = False
    try:
        pos_only_demo(x=1, y=2, standard_param=3)
    except TypeError:
        pos_error_raised = True
    assert pos_error_raised is True

    # ------------------------------------------------------------
    # Keyword-Only parameters: After '*'
    # Must be supplied by keyword name, cannot be passed positionally
    # ------------------------------------------------------------
    def kw_only_demo(data, *, secure=True, timeout=30):
        return {"data": data, "secure": secure, "timeout": timeout}

    # Valid: secure and timeout passed by name
    res = kw_only_demo("payload", secure=False, timeout=10)
    assert res == {"data": "payload", "secure": False, "timeout": 10}

    # Invalid: passing keyword-only argument positionally raises TypeError
    kw_error_raised = False
    try:
        kw_only_demo("payload", False, 10)
    except TypeError:
        kw_error_raised = True
    assert kw_error_raised is True

    # ------------------------------------------------------------
    # Combined signature: pos-only, standard, and kw-only
    # `def api(endpoint, /, timeout=5, *, retry=True):`
    # ------------------------------------------------------------
    def full_spec(pos, /, std, *, kw):
        return f"{pos}-{std}-{kw}"

    assert full_spec("A", "B", kw="C") == "A-B-C"
    assert full_spec("A", std="B", kw="C") == "A-B-C"


    # ============================================================
    # 6. FIRST-CLASS & HIGHER-ORDER FUNCTIONS
    # ============================================================
    # Functions can be passed, returned, and stored in dictionaries.

    # ------------------------------------------------------------
    # Dispatch table pattern (replacing long if-elif chains)
    # ------------------------------------------------------------
    def handle_create(payload):
        return f"Created {payload}"

    def handle_update(payload):
        return f"Updated {payload}"

    def handle_delete(payload):
        return f"Deleted {payload}"

    dispatch_table = {
        "CREATE": handle_create,
        "UPDATE": handle_update,
        "DELETE": handle_delete,
    }

    action = "CREATE"
    assert dispatch_table[action]("user_1") == "Created user_1"

    # ------------------------------------------------------------
    # Function factory (Function returning a function)
    # ------------------------------------------------------------
    def make_multiplier(factor):
        def multiplier(x):
            return x * factor
        return multiplier

    double = make_multiplier(2)
    triple = make_multiplier(3)

    assert double(5) == 10
    assert triple(5) == 15


    # ============================================================
    # 7. LAMBDA FUNCTIONS (ANONYMOUS FUNCTIONS)
    # ============================================================
    # Syntax: lambda arg1, arg2: expression
    # Evaluates to a single expression; cannot contain statements.

    # ------------------------------------------------------------
    # Basic lambda usage
    # ------------------------------------------------------------
    square = lambda x: x ** 2
    assert square(6) == 36

    # With conditional expression (ternary)
    classify = lambda x: "even" if x % 2 == 0 else "odd"
    assert classify(4) == "even"
    assert classify(7) == "odd"

    # ------------------------------------------------------------
    # Idiomatic use of lambda: Sorting keys
    # ------------------------------------------------------------
    employees = [
        {"name": "Alice", "score": 92},
        {"name": "Bob", "score": 85},
        {"name": "Charlie", "score": 97},
    ]

    # Sort descending by score
    sorted_emp = sorted(employees, key=lambda e: e["score"], reverse=True)
    assert [e["name"] for e in sorted_emp] == ["Charlie", "Alice", "Bob"]


    # ============================================================
    # 8. CLOSURES & SCOPE MODIFIERS (global and nonlocal)
    # ============================================================

    # ------------------------------------------------------------
    # Reading outer variables in a closure (Automatic)
    # ------------------------------------------------------------
    def outer_reader():
        greeting = "Hello"
        def inner(name):
            return f"{greeting}, {name}!"
        return inner

    greeter = outer_reader()
    assert greeter("World") == "Hello, World!"

    # ------------------------------------------------------------
    # Mutating outer variables: 'nonlocal'
    # Modifies variable in the nearest enclosing non-global scope
    # ------------------------------------------------------------
    def make_counter(start=0):
        count = start
        def increment():
            nonlocal count
            count += 1
            return count
        return increment

    counter_a = make_counter(0)
    assert counter_a() == 1
    assert counter_a() == 2
    assert counter_a() == 3

    # Independent closure state
    counter_b = make_counter(100)
    assert counter_b() == 101
    assert counter_a() == 4  # counter_a unchanged

    # ------------------------------------------------------------
    # 'global' keyword: Re-binding module-level variables
    # ------------------------------------------------------------
    def modify_global():
        global MODULE_GLOBAL_TRACKER
        MODULE_GLOBAL_TRACKER = 42

    modify_global()
    assert MODULE_GLOBAL_TRACKER == 42


    # ============================================================
    # 9. FUNCTION INTROSPECTION & METADATA
    # ============================================================
    # Functions are rich objects with introspectable attributes.

    def documented_func(a: int, b: str = "default") -> bool:
        """Sample docstring explaining documented_func."""
        return True

    # Accessing docstring
    assert documented_func.__doc__ == "Sample docstring explaining documented_func."

    # Accessing function name
    assert documented_func.__name__ == "documented_func"

    # Accessing type hints annotations
    assert documented_func.__annotations__ == {"a": int, "b": str, "return": bool}

    # Accessing default values
    assert documented_func.__defaults__ == ("default",)

    # Inspecting bytecode parameter names
    code_obj = documented_func.__code__
    assert "a" in code_obj.co_varnames
    assert "b" in code_obj.co_varnames
    assert code_obj.co_argcount == 2


if __name__ == "__main__":
    run_tests()
    print("06_functions_and_args.py tests passed!")
