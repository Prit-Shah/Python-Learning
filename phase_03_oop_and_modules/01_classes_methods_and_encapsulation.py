"""
01_classes_methods_and_encapsulation.py

============================================================
1. CONCEPT
============================================================

Object-Oriented Programming (OOP) in Python is centered on classes as callable
factories that instantiate objects with encapsulated state and behavior:

1. Explicit Instance Binding (`self`):
   - Unlike languages with an implicit `this`, Python requires the instance
     to be explicitly passed as the first parameter to instance methods.
   - When calling `obj.method(arg)`, Python translates this under the hood to
     `Class.method(obj, arg)`.

2. The Three Method Types:
   - Instance Methods: Accept `self` as the first argument; operate directly
     on instance state and have access to the class via `type(self)`.
   - Class Methods (`@classmethod`): Accept `cls` as the first argument; operate
     on class state and serve as idiomatic alternative constructors / factories.
   - Static Methods (`@staticmethod`): Accept neither `self` nor `cls`; plain
     functions logically grouped inside the class namespace.

3. Encapsulation & Access Conventions:
   - Python adheres to the philosophy: "We are all consenting adults here."
     There are no compiler-enforced access modifiers (`public`, `private`, `protected`).
   - Public: `name` (accessible everywhere).
   - Protected convention: `_name` (signals internal / implementation detail).
   - Private Name Mangling: `__name` (automatically rewritten at compile time to
     `_ClassName__name` to prevent accidental namespace collisions in subclasses).

4. Properties (`@property`):
   - Provides getter, setter, and deleter encapsulation using the descriptor protocol.
   - Allows attribute access syntax (`obj.balance`) while executing validation
     methods behind the scenes.

5. Memory Optimization via `__slots__`:
   - By default, every instance stores its attributes in an internal dictionary (`__dict__`).
   - Declaring `__slots__ = ("x", "y")` replaces `__dict__` with a fixed-size
     C array of pointers, drastically reducing memory overhead and preventing
     accidental addition of arbitrary attributes.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Instance Pointer             | Explicit `self` parameter          | Implicit `this` keyword            |
| Class Constructor            | `def __init__(self, ...):`         | `constructor(...)`                 |
| Class Factory Method         | `@classmethod def from_dict(cls):` | `static fromDict(...)`             |
| Static Utility Method        | `@staticmethod def is_valid():`    | `static isValid(...)`              |
| Property Getter / Setter     | `@property` / `@prop.setter`       | `get prop()` / `set prop(val)`     |
| Protected Convention         | `_protected_var`                   | `protected protectedVar` (TS)      |
| Private Name Mangling        | `__private_var`                    | `#privateVar` (JS private fields)  |
| Memory Optimization          | `__slots__`                        | V8 Hidden Classes / Shapes         |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python OOP Nuance:
1. `this` vs `self`:
   In JavaScript, `this` is dynamically bound based on call-site context (unless
   bound or using arrow functions). In Python, `self` is explicitly declared in
   the parameter signature and bound deterministically.
2. Static vs Class Methods:
   TypeScript `static` methods do not receive a dynamic reference to derived
   subclasses when called via inheritance unless manually checked.
   Python `@classmethod` receives the exact subclass `cls` polymorphically!


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The `__dict__` Attribute & Namespaces:
   - Classes and instances each maintain their own `__dict__` attribute.
   - When resolving `obj.attr`, CPython executes a lookup order:
     1. Data descriptors defined on the class (e.g. `@property`).
     2. The instance dictionary: `obj.__dict__["attr"]`.
     3. Non-data descriptors on the class (e.g. standard methods).
     4. Class dictionary: `type(obj).__dict__["attr"]`.
     5. Base classes in the Method Resolution Order (MRO).

2. Method Binding (`PyMethodObject`):
   - A function defined in a class is an ordinary function (`function` type).
   - When accessed via an instance (`obj.method`), the function's descriptor
     `__get__` method is triggered, returning a bound method object (`PyMethodObject`).
   - The bound method stores two pointers: `im_func` (the function bytecode)
     and `im_self` (the instance). When called, it prepends `im_self` to the arguments.

3. How `__slots__` Saves Memory:
   - Standard instance: `PyObject_HEAD` + pointer to `__dict__` (which starts at
     ~100+ bytes and grows) + pointer to `__weakref__`.
   - With `__slots__`: CPython reserves space directly in the C struct for each
     slot variable offset, completely omitting the `__dict__`.
   - For millions of instances (e.g. coordinates or telemetry points), memory
     usage drops by up to 60-70%.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Mutable Class Attribute Trap:
   - Defining a mutable container at class level:
     ```python
     class Team:
         members = []  # BUG: Shared across ALL instances!
     ```
   - All `Team` instances share and mutate the exact same list!
   - Fix: Initialize mutable attributes inside `__init__` on `self.members`.

2. Shadowing Class Attributes via Instance Assignment:
   - `class Config: timeout = 30`
   - `c = Config(); c.timeout = 60`
   - This does NOT change `Config.timeout`! It creates an instance attribute
     `timeout` on `c.__dict__`, shadowing the class attribute.

3. Missing `self` in Method Definitions:
   - Defining `def compute():` inside a class.
   - Calling `obj.compute()` passes `obj` as first argument, raising:
     `TypeError: compute() takes 0 positional arguments but 1 was given`.

4. Misunderstanding Name Mangling:
   - Double underscore `__var` is not cryptographically secure.
   - Python simply renames it to `_ClassName__var`. It can still be accessed
     and mutated from outside if someone writes `obj._ClassName__var`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the difference between instance methods, class methods, and static methods in Python."
Script:
"Instance methods are the default in Python; they take `self` as their first parameter,
giving them direct read and write access to instance attributes as well as class state via
`type(self)`. Class methods are decorated with `@classmethod` and receive `cls`, which is
the class object itself rather than an instance. They are the idiomatic Python pattern for
alternative factory constructors (like `from_dict` or `from_json`) because they support
clean polymorphic instantiation in subclasses. Static methods are decorated with `@staticmethod`
and receive neither `self` nor `cls`; they are essentially pure utility functions that live
within the class's namespace for organizational coherence."

Q2: "How does Python handle encapsulation and name mangling?"
Script:
"Python does not enforce private variables at the language runtime level. Instead, it relies
on established conventions. A single leading underscore, like `_internal_state`, is a PEP 8
convention indicating an internal API that callers should not rely on. A double leading
underscore, like `__private_state`, invokes compile-time name mangling: CPython prepends
an underscore and the enclosing class name, rewriting it to `_ClassName__private_state`.
This mechanism exists specifically to prevent accidental variable name collisions in
inheritance hierarchies, not for data security."

Q3: "What is __slots__ in Python, and when would you use it?"
Script:
"By default, Python instances store their dynamic attributes in a heap-allocated dictionary
named `__dict__`. While this offers immense flexibility, dictionaries carry substantial memory
overhead. By defining `__slots__ = ('x', 'y')`, we instruct CPython to eliminate `__dict__`
and instead allocate a fixed-size C array of attribute pointers directly inside the object's
memory layout. This reduces memory consumption by 50 to 70 percent and speeds up attribute
access. It is best used for high-frequency data classes where millions of lightweight objects
are instantiated, such as in game loops, data processing engines, or graph nodes."
"""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class BankAccount:
    """Demonstrates instance, class, and static methods, properties, and name mangling."""

    # Class variables: shared across all instances
    BANK_NAME = "Apex International"
    _interest_rate: float = 0.04
    _total_accounts_created: int = 0

    def __init__(self, owner: str, initial_deposit: float = 0.0):
        # Instance variables: private to each instance
        self.owner = owner
        self._balance = max(0.0, float(initial_deposit))
        BankAccount._total_accounts_created += 1
        # Double underscore triggers name mangling: _BankAccount__account_id
        self.__account_id = f"ACC-{BankAccount._total_accounts_created:04d}"

    # ------------------------------------------------------------
    # Properties: Encapsulation with Getters, Setters, Deleters
    # ------------------------------------------------------------
    @property
    def balance(self) -> float:
        """Getter for account balance."""
        return self._balance

    @balance.setter
    def balance(self, new_balance: float) -> None:
        """Setter with validation."""
        if new_balance < 0:
            raise ValueError("Balance cannot be negative.")
        self._balance = float(new_balance)

    @property
    def account_id(self) -> str:
        """Read-only property exposing mangled private account ID."""
        return self.__account_id

    # ------------------------------------------------------------
    # 1. Instance Method
    # ------------------------------------------------------------
    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Deposit must be positive.")
        self._balance += amount
        return self._balance

    def withdraw(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Withdrawal must be positive.")
        if amount > self._balance:
            raise ValueError("Insufficient funds.")
        self._balance -= amount
        return self._balance

    # ------------------------------------------------------------
    # 2. Class Method: Alternative Factory Constructor
    # ------------------------------------------------------------
    @classmethod
    def from_dict(cls, payload: dict) -> "BankAccount":
        """Factory constructor instantiating BankAccount from dictionary."""
        owner = payload.get("owner", "Anonymous")
        deposit = payload.get("deposit", 0.0)
        # Polymorphic: uses cls so subclasses instantiate their own type!
        return cls(owner=owner, initial_deposit=deposit)

    @classmethod
    def get_total_accounts(cls) -> int:
        return cls._total_accounts_created

    # ------------------------------------------------------------
    # 3. Static Method: Namespace Utility
    # ------------------------------------------------------------
    @staticmethod
    def is_valid_currency(currency_code: str) -> bool:
        """Utility function validating currency code without instance or class state."""
        return currency_code.upper() in {"USD", "EUR", "GBP", "JPY", "CAD"}


class SlottedPoint:
    """High-performance 2D coordinate class utilizing __slots__."""
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


class StandardPoint:
    """Standard 2D coordinate class using __dict__."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y


def run_tests():
    # ============================================================
    # 1. INSTANCE METHODS & EXPLICIT SELF
    # ============================================================

    acc1 = BankAccount("Alice", 100.0)
    assert acc1.owner == "Alice"
    assert acc1.balance == 100.0

    # Instance method call
    new_bal = acc1.deposit(50.0)
    assert new_bal == 150.0
    assert acc1.balance == 150.0

    # Explicit class invocation equivalent
    BankAccount.deposit(acc1, 50.0)
    assert acc1.balance == 200.0


    # ============================================================
    # 2. CLASS METHODS & ALTERNATIVE CONSTRUCTORS
    # ============================================================

    data_payload = {"owner": "Bob", "deposit": 250.0}
    acc2 = BankAccount.from_dict(data_payload)

    assert isinstance(acc2, BankAccount)
    assert acc2.owner == "Bob"
    assert acc2.balance == 250.0
    assert BankAccount.get_total_accounts() >= 2


    # ============================================================
    # 3. STATIC METHODS FOR UTILITIES
    # ============================================================

    assert BankAccount.is_valid_currency("USD") is True
    assert BankAccount.is_valid_currency("EUR") is True
    assert BankAccount.is_valid_currency("INVALID") is False

    # Static method can also be called from an instance
    assert acc1.is_valid_currency("GBP") is True


    # ============================================================
    # 4. ENCAPSULATION, NAME MANGLING, AND PROPERTIES
    # ============================================================

    # ------------------------------------------------------------
    # @property getter and setter validation
    # ------------------------------------------------------------
    acc1.balance = 500.0
    assert acc1.balance == 500.0

    # Negative balance validation
    validation_error = False
    try:
        acc1.balance = -10.0
    except ValueError:
        validation_error = True
    assert validation_error is True

    # ------------------------------------------------------------
    # Read-only property
    # ------------------------------------------------------------
    assert acc1.account_id.startswith("ACC-")
    cant_overwrite_id = False
    try:
        acc1.account_id = "HACKED"
    except AttributeError:
        cant_overwrite_id = True
    assert cant_overwrite_id is True

    # ------------------------------------------------------------
    # Name Mangling verification: __account_id -> _BankAccount__account_id
    # ------------------------------------------------------------
    # Direct access fails with AttributeError
    mangled_failed = False
    try:
        _ = acc1.__account_id
    except AttributeError:
        mangled_failed = True
    assert mangled_failed is True

    # Accessing via mangled name succeeds (proves Python does not truly make it private)
    assert hasattr(acc1, "_BankAccount__account_id") is True
    assert getattr(acc1, "_BankAccount__account_id") == acc1.account_id


    # ============================================================
    # 5. CLASS ATTRIBUTES VS INSTANCE ATTRIBUTES
    # ============================================================

    class Config:
        timeout = 30
        tags = []  # Shared mutable class attribute warning!

    cfg_a = Config()
    cfg_b = Config()

    # Reading class attribute from instances
    assert cfg_a.timeout == 30
    assert cfg_b.timeout == 30

    # Shadowing: assigning to instance creates an instance attribute!
    cfg_a.timeout = 60
    assert cfg_a.timeout == 60
    assert cfg_b.timeout == 30  # cfg_b still points to class attribute
    assert Config.timeout == 30  # Class attribute unchanged

    # The Mutable Class Attribute Trap:
    cfg_a.tags.append("production")
    # Both observe the change because tags is shared on the class object!
    assert cfg_b.tags == ["production"]


    # ============================================================
    # 6. MEMORY OPTIMIZATION WITH __slots__
    # ============================================================

    slotted = SlottedPoint(10.0, 20.0)
    standard = StandardPoint(10.0, 20.0)

    # Standard instance has a dynamic __dict__
    assert hasattr(standard, "__dict__") is True
    assert standard.__dict__ == {"x": 10.0, "y": 20.0}

    # Slotted instance DOES NOT have a __dict__
    assert hasattr(slotted, "__dict__") is False

    # Dynamic attribute injection on standard instance succeeds
    standard.z = 30.0
    assert standard.z == 30.0

    # Dynamic attribute injection on slotted instance raises AttributeError
    slotted_blocked = False
    try:
        slotted.z = 30.0
    except AttributeError:
        slotted_blocked = True
    assert slotted_blocked is True


if __name__ == "__main__":
    run_tests()
    print("01_classes_methods_and_encapsulation.py tests passed!")
