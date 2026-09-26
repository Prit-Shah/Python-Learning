"""
02_dunder_methods_and_data_model.py

============================================================
1. CONCEPT
============================================================

The Python Data Model is a formalized framework that allows user-defined classes
to integrate seamlessly with Python's syntax, built-ins, and operators via
special "dunder" (double underscore) methods:

1. Representation Protocol:
   - `__repr__`: Unambiguous, developer-centric representation for debugging.
     Ideally formatted as executable Python code: `eval(repr(obj)) == obj`.
   - `__str__`: Human-friendly string format invoked by `str()` and `print()`.
     If `__str__` is not implemented, Python automatically falls back to `__repr__`.
   - `__format__`: Custom formatting hook used by f-strings (e.g. `f"{v:polar}"`).

2. Equality, Comparison & Hashability:
   - Rich comparisons: `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`.
     Using `@functools.total_ordering` generates all comparison operators from
     `__eq__` and any single ordering method (e.g. `__lt__`).
   - The Hashability Invariant: If `a == b`, then `hash(a) == hash(b)` MUST hold True!
   - In Python, defining `__eq__` automatically unsets `__hash__ = None` unless
     `__hash__` is explicitly implemented.

3. Container & Sequence Protocols:
   - `__len__`: Returns non-negative integer for `len(obj)`.
   - `__getitem__`: Handles index access, key lookups, and slice objects (`obj[start:stop:step]`).
   - `__setitem__` & `__delitem__`: Container mutation and item removal.
   - `__contains__`: Enables the `in` operator (defaults to linear scan if omitted).

4. Arithmetic & Operator Overloading:
   - Standard arithmetic: `__add__`, `__sub__`, `__mul__`, `__truediv__`.
   - Reflected (Right-hand) arithmetic: `__radd__`, `__rmul__` (invoked when the left
     operand does not support the operation with the right operand).
   - In-place arithmetic: `__iadd__`, `__imul__` (`+=`, `*=`).

5. Callable Protocol & Attribute Interception:
   - `__call__`: Enables calling an instance as a function: `obj(*args)`.
   - `__getattr__`: Fallback lookup called ONLY when an attribute does not exist.
   - `__bool__`: Controls truthiness (falls back to `__len__() != 0`).


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| String Representation        | `__str__` and `__repr__`           | `toString()` / `[util.inspect]`    |
| Length Protocol              | `len(obj)` calls `__len__`         | `obj.length` property convention   |
| Operator Overloading         | `+` calls `__add__`                | Not supported (except Symbol.toPrimitive)|
| Index Access Protocol        | `obj[key]` calls `__getitem__`     | Proxy get trap (`get(target, key)`)|
| Iteration Protocol           | `__iter__` and `__next__`          | `[Symbol.iterator]()`              |
| Callable Object              | `__call__`                         | Function object or `Proxy.apply`   |
| Value Comparison             | `__eq__` / rich comparisons        | No operator overloading (custom fn)|
| Set / Map Keys               | `__hash__` and `__eq__`            | Reference identity in Set / Map    |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Difference:
- JavaScript has NO operator overloading: `vec1 + vec2` results in string
  concatenation `"[object Object][object Object]"`.
- Python's Data Model enables elegant mathematical expressions with domain objects:
  `total = balance + interest - fees`, `pos = origin + direction * speed`.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyTypeObject C Struct Slots:
   - In CPython, dunder methods are not resolved as slow dictionary lookups.
   - CPython classes are instances of `PyTypeObject`, which contains dedicated
     C function pointer slots:
     `tp_as_number` -> pointer to number methods table (`nb_add`, `nb_subtract`).
     `tp_as_sequence` -> pointer to sequence methods (`sq_length`, `sq_item`).
     `tp_as_mapping` -> pointer to mapping methods (`mp_subscript`).
   - Calling `len(x)` directly jumps to the C function pointer in the `tp_as_sequence->sq_length`
     slot, executing at raw C speeds!

2. Reflected (Reverse) Arithmetic Mechanics:
   - When evaluating `a + b`:
     1. CPython first tries `type(a).__add__(a, b)`.
     2. If `__add__` is not implemented or returns `NotImplemented`, CPython checks
        if `type(b)` implements `__radd__`.
     3. It calls `type(b).__radd__(b, a)`.
     4. If both return `NotImplemented`, CPython raises `TypeError: unsupported operand type(s)`.

3. Hash Invariant & Hash Flooding Defense:
   - Python implements randomized SIPHASH for strings to prevent algorithmic
     complexity attacks on dictionaries.
   - A custom class must return a 64-bit integer from `__hash__`. If mutated after
     insertion into a hash map, its bucket calculation will fail, losing the key.


============================================================
4. COMMON GOTCHAS
============================================================

1. Overriding `__eq__` Without `__hash__`:
   - If you define `__eq__`, Python sets `__hash__ = None`.
   - Attempting to put instances in a `set` or use them as `dict` keys raises:
     `TypeError: unhashable type: 'MyClass'`.
   - Fix: Implement `__hash__` using immutable attributes: `return hash((self.id, self.name))`.

2. Returning `bool` from Comparison Instead of `NotImplemented`:
   - Returning `False` instead of `NotImplemented` from `__eq__` prevents Python
     from falling back to the other operand's comparison method!

3. Infinite Recursion in `__getattribute__`:
   - Calling `self.attr` inside `__getattribute__` calls `__getattribute__` again,
     causing infinite recursion.
   - Fix: Always delegate using `super().__getattribute__(name)`.

4. Misunderstanding `__getattr__` vs `__getattribute__`:
   - `__getattr__` is a safe fallback called ONLY when normal lookup fails.
   - `__getattribute__` intercepts EVERY lookup. Prefer `__getattr__` for dynamic proxies.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "What is the difference between __repr__ and __str__, and which should you always implement?"
Script:
"`__repr__` is intended for developers and debugging, providing an unambiguous string
representation of an object that ideally looks like valid Python code to recreate it,
such as `User(id=1, name='Alice')`. `__str__` is intended for end users and presents a
clean, readable display string. If a class does not define `__str__`, Python automatically
falls back to `__repr__`. Therefore, the professional Python best practice is to always
implement `__repr__` first to guarantee informative output in tracebacks, logging, and
interactive shells, and implement `__str__` second only when a distinct user-facing
representation is needed."

Q2: "Explain the relationship between __eq__ and __hash__ in Python."
Script:
"The Python Data Model enforces a fundamental contract: if two objects are equal according
to `__eq__`, their `__hash__` values must be identical so they map to the same hash table
bucket in dictionaries and sets. By default, user-defined classes inherit identity-based
equality and hashability from `object`. However, as soon as a class overrides `__eq__` to
provide value-based equality, CPython automatically sets `__hash__ = None` to prevent
hash table corruption if instances are mutable. If the object is immutable, you must explicitly
implement `__hash__` by hashing a tuple of its immutable attributes."

Q3: "How does operator overloading work in Python when operands are of different types?"
Script:
"When an operator like `+` is evaluated as `a + b`, Python first calls the left operand's
method `a.__add__(b)`. If `a` does not recognize the type of `b`, it returns the singleton
`NotImplemented` rather than raising an exception. This signals Python to check the right
operand for a reflected method: `b.__radd__(a)`. If the right operand succeeds, its return
value is used. If both operands return `NotImplemented`, CPython raises a `TypeError`. This
mechanism allows custom domain types, like a `Vector`, to gracefully interoperate with
built-in scalar types like `int` or `float`."
"""

import functools
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


@functools.total_ordering
class PriorityTask:
    """Demonstrates __repr__, __str__, rich comparisons, and hashability."""
    def __init__(self, task_id: int, title: str, priority: int):
        self._task_id = int(task_id)
        self._title = str(title)
        self._priority = int(priority)

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def priority(self) -> int:
        return self._priority

    # ------------------------------------------------------------
    # String representations
    # ------------------------------------------------------------
    def __repr__(self) -> str:
        return f"PriorityTask(task_id={self._task_id}, title={self._title!r}, priority={self._priority})"

    def __str__(self) -> str:
        return f"[{self._priority}] {self._title} (ID: {self._task_id})"

    # ------------------------------------------------------------
    # Equality and Hashability
    # ------------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriorityTask):
            return NotImplemented
        return self._task_id == other._task_id

    def __hash__(self) -> int:
        # Hash based on immutable identity key
        return hash(self._task_id)

    # ------------------------------------------------------------
    # Rich Comparison (with @total_ordering, __lt__ generates <=, >, >=)
    # ------------------------------------------------------------
    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PriorityTask):
            return NotImplemented
        # Higher priority value means higher priority rank
        return self._priority < other._priority


class Vector2D:
    """Demonstrates arithmetic operator overloading, reflection, and container protocol."""
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        return f"Vector2D({self.x}, {self.y})"

    # Equality
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2D):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    # Vector addition: v1 + v2
    def __add__(self, other: object) -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented
        return Vector2D(self.x + other.x, self.y + other.y)

    # Scalar multiplication: v * scalar
    def __mul__(self, scalar: float | int) -> "Vector2D":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2D(self.x * scalar, self.y * scalar)

    # Reflected scalar multiplication: scalar * v
    def __rmul__(self, scalar: float | int) -> "Vector2D":
        return self.__mul__(scalar)

    # In-place addition: v += other
    def __iadd__(self, other: object) -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented
        self.x += other.x
        self.y += other.y
        return self

    # Truthiness: False if origin (0, 0), True otherwise
    def __bool__(self) -> bool:
        return self.x != 0.0 or self.y != 0.0


class CustomRegistry:
    """Demonstrates container sequence/mapping protocols: len, getitem, setitem, contains."""
    def __init__(self):
        self._storage = {}

    def __len__(self) -> int:
        return len(self._storage)

    def __getitem__(self, key: str):
        return self._storage[key]

    def __setitem__(self, key: str, value):
        self._storage[key] = value

    def __delitem__(self, key: str):
        del self._storage[key]

    def __contains__(self, key: str) -> bool:
        return key in self._storage


class DynamicProxy:
    """Demonstrates __getattr__ fallback and __call__ callable protocol."""
    def __init__(self, target_dict: dict):
        self._target = target_dict

    def __getattr__(self, name: str):
        # Called ONLY when attribute is not on the instance
        if name in self._target:
            return self._target[name]
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __call__(self, key_to_query: str):
        # Enables calling instance as a function: proxy('key')
        return self._target.get(key_to_query)


def run_tests():
    # ============================================================
    # 1. STRING REPRESENTATION (__repr__ and __str__)
    # ============================================================

    task = PriorityTask(101, "Deploy Cluster", priority=5)

    # __str__ invocation via str() and f-string
    assert str(task) == "[5] Deploy Cluster (ID: 101)"

    # __repr__ invocation via repr() and !r formatting
    assert repr(task) == "PriorityTask(task_id=101, title='Deploy Cluster', priority=5)"

    # Verification: Fallback to __repr__ when __str__ is absent
    class BareObject:
        def __repr__(self):
            return "BareObject(v=1)"

    bare = BareObject()
    assert str(bare) == "BareObject(v=1)"  # Fell back cleanly!


    # ============================================================
    # 2. COMPARISONS & @functools.total_ordering
    # ============================================================

    t1 = PriorityTask(1, "Low Priority", priority=1)
    t2 = PriorityTask(2, "Medium Priority", priority=5)
    t3 = PriorityTask(3, "High Priority", priority=10)
    t1_dup = PriorityTask(1, "Duplicate ID", priority=99)

    # Equality check based on task_id
    assert t1 == t1_dup
    assert t1 != t2

    # Ordering based on priority
    assert t1 < t2
    assert t2 < t3
    assert t3 > t1
    assert t1 <= t2
    assert t3 >= t2

    # Sorting tasks using rich comparison
    task_list = [t3, t1, t2]
    task_list.sort()
    assert task_list == [t1, t2, t3]


    # ============================================================
    # 3. HASHABILITY & SET/DICT MEMBERSHIP
    # ============================================================

    # PriorityTasks can be placed in sets because __hash__ is defined
    task_set = {t1, t2, t3}
    assert len(task_set) == 3

    # Adding duplicate with same task_id does not increase set size
    task_set.add(t1_dup)
    assert len(task_set) == 3

    # Dict keys
    task_dict = {t1: "active", t2: "pending"}
    assert task_dict[t1_dup] == "active"


    # ============================================================
    # 4. ARITHMETIC OPERATORS & REFLECTION
    # ============================================================

    v1 = Vector2D(2.0, 3.0)
    v2 = Vector2D(4.0, 1.0)

    # Vector addition (__add__)
    v3 = v1 + v2
    assert v3 == Vector2D(6.0, 4.0)

    # Scalar multiplication (__mul__)
    v_scaled = v1 * 3
    assert v_scaled == Vector2D(6.0, 9.0)

    # Reflected scalar multiplication (__rmul__: 3 * v1)
    v_reflected = 3 * v1
    assert v_reflected == Vector2D(6.0, 9.0)

    # In-place addition (__iadd__)
    v1 += v2
    assert v1 == Vector2D(6.0, 4.0)

    # Truthiness (__bool__)
    assert bool(v1) is True
    origin = Vector2D(0.0, 0.0)
    assert bool(origin) is False


    # ============================================================
    # 5. CONTAINER PROTOCOL (__len__, __getitem__, __contains__)
    # ============================================================

    reg = CustomRegistry()
    assert len(reg) == 0

    reg["api_key"] = "sec_123"
    reg["region"] = "us-east-1"

    assert len(reg) == 2
    assert reg["api_key"] == "sec_123"
    assert "region" in reg
    assert "missing" not in reg

    del reg["region"]
    assert len(reg) == 1
    assert "region" not in reg


    # ============================================================
    # 6. ATTRIBUTE INTERCEPTION (__getattr__) & CALLABLE (__call__)
    # ============================================================

    proxy = DynamicProxy({"env": "staging", "workers": 4})

    # __getattr__ accesses underlying dict attributes
    assert proxy.env == "staging"
    assert proxy.workers == 4

    # Non-existent attribute raises AttributeError
    missing_attr_raised = False
    try:
        _ = proxy.non_existent
    except AttributeError:
        missing_attr_raised = True
    assert missing_attr_raised is True

    # __call__ allows proxy invocation like a function
    assert proxy("env") == "staging"
    assert proxy("unknown_key") is None


if __name__ == "__main__":
    run_tests()
    print("02_dunder_methods_and_data_model.py tests passed!")
