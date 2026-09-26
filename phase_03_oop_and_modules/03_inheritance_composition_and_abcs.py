"""
03_inheritance_composition_and_abcs.py

============================================================
1. CONCEPT
============================================================

Python provides rich object-oriented modeling capabilities featuring multiple
inheritance, the C3 Linearization algorithm for method resolution, runtime-enforced
Abstract Base Classes (ABCs), and composition architectures:

1. Inheritance and Cooperative `super()`:
   - Single and multiple inheritance: `class Child(ParentA, ParentB):`.
   - Python 3's zero-argument `super()` automatically resolves the current class
     and instance via compiler cell variables (`__class__` and `self`).
   - `super()` does NOT merely call the immediate parent class; it invokes the
     *next class* in the Method Resolution Order (MRO).

2. Multiple Inheritance & The Diamond Problem:
   - When a derived class inherits from two classes that share a common base
     (`A -> B, C -> D`), naive inheritance executes the base constructor twice.
   - In Python, cooperative `super().__init__()` calls traverse the linearized
     MRO chain such that every class in the diamond graph is visited exactly once.

3. Method Resolution Order (MRO) & C3 Linearization:
   - Python computes the method lookup path at class definition time using the
     C3 Linearization algorithm.
   - Enforces two guarantees:
     1. Local Precedence Order: Subclasses appear before parent classes, and
        parents appear in the order specified in the class definition tuple.
     2. Monotonicity: If class `A` precedes `B` in one MRO, `A` must precede `B`
        in all subclass MROs.
   - If an inheritance hierarchy violates monotonicity, Python raises `TypeError`
     at import time.

4. Abstract Base Classes (ABCs):
   - Created via `from abc import ABC, abstractmethod`.
   - Enforces interface contracts at runtime: any class containing unimplemented
     `@abstractmethod` hooks CANNOT be instantiated, raising `TypeError`.
   - Can provide default implementations (Template Method design pattern).

5. Composition Over Inheritance:
   - "Favor object composition over class inheritance" (GoF).
   - "Is-a" relationships (Inheritance) create tight coupling.
   - "Has-a" relationships (Composition) inject modular dependencies, simplifying
     unit testing, mocking, and refactoring.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Multiple Implementation Inh. | YES: `class D(B, C):`              | NO: Classes can only `extend` one  |
| Method Resolution Order      | C3 Linearization (`Class.mro()`)   | Single prototype chain (`__proto__`)|
| Cooperative Super            | `super().method()` walks MRO chain | `super.method()` calls parent only |
| Abstract Classes             | `class MyABC(ABC):`                | `abstract class MyClass { ... }`   |
| Interface Enforcement        | Runtime check on `__init__`        | Compile-time static check only     |
| Mixins                       | Native via multiple inheritance    | Mixin pattern via factory functions|
| Composition                  | Injected component attributes      | Injected component attributes      |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Difference:
- JavaScript / TypeScript strictly disallows inheriting from multiple classes:
  `class D extends B, C` is a syntax error. TS uses `implements InterfaceA, InterfaceB`
  for interfaces, but only one class for code reuse.
- Python natively supports multiple implementation inheritance and uses C3 MRO
  to resolve method and attribute conflicts deterministically.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. C3 Linearization Algorithm:
   - For a class `C` inheriting from `B1, B2, ..., BN`:
     `L[C] = [C] + merge(L[B1], L[B2], ..., L[BN], [B1, B2, ..., BN])`
   - Merge algorithm: Take the head of the first list; if it is not in the tail
     of any other list, add it to the MRO and remove it from all lists.
     Repeat until all lists are empty or raise `TypeError` if a cycle is detected.

2. Zero-Argument `super()` Mechanics:
   - In Python 3, writing `super()` inside a method causes the compiler to
     silently create a closure cell named `__class__`.
   - At runtime, `super()` retrieves `__class__` and `self` from the current
     execution frame, locating the next class in `type(self).__mro__`.

3. ABC Instantiation Check (`type.__call__`):
   - `ABC` uses the metaclass `abc.ABCMeta`.
   - When `SubClass()` is instantiated, `ABCMeta.__call__` inspects the set of
     abstract methods stored in `cls.__abstractmethods__`.
   - If `cls.__abstractmethods__` is non-empty, CPython halts instantiation
     immediately, raising `TypeError`.


============================================================
4. COMMON GOTCHAS
============================================================

1. Forgetting `super().__init__()`:
   - Unlike Java or C#, Python does NOT automatically call base class constructors.
   - If a subclass defines `__init__` without calling `super().__init__()`, the
     parent's instance variables will never be initialized, causing `AttributeError`.

2. Inconsistent MRO Definition Order:
   - `class A: pass`, `class B(A): pass`, `class C(A, B): pass`
   - Defining `class C(A, B)` raises:
     `TypeError: Cannot create a consistent method resolution order (MRO) for bases A, B`.
     Because `B` inherits from `A`, `B` must precede `A` in the base class list: `class C(B, A):`.

3. Modifying Subclass Attributes Missing from Abstract Properties:
   - If an ABC defines an `@abstractmethod` property without a setter, implementing
     it with a setter in the subclass must explicitly re-decorate or define the setter.

4. Deep Inheritance Trees vs Composition:
   - Subclassing 4 or 5 levels deep creates fragile base class problems.
   - Prefer injecting helper classes into `__init__`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does Python resolve multiple inheritance, and what is the C3 Linearization algorithm?"
Script:
"Python supports multiple inheritance and resolves method lookup collisions using the
Method Resolution Order (MRO), computed via the C3 Linearization algorithm. C3 enforces
two strict rules: local precedence order, meaning subclasses precede parents and base
classes are evaluated in left-to-right order as declared; and monotonicity, meaning that
if class A precedes class B in any parent's MRO, A must precede B across all descendant
MROs. If an inheritance hierarchy violates monotonicity or creates circular dependencies,
Python rejects the class definition at import time with a `TypeError`."

Q2: "Why is cooperative multiple inheritance with super() necessary in Python?"
Script:
"In multiple inheritance hierarchies, particularly the classic diamond pattern where
classes B and C inherit from A, and D inherits from both B and C, calling parent
constructors by name like `A.__init__(self)` leads to duplicate executions of A's
constructor and brittle hard-coded coupling. By using `super().__init__(*args, **kwargs)`
consistently across all classes, Python delegates each initialization step to the next
class in D's linearized MRO. This ensures that every class in the diamond graph executes
its setup logic exactly once, maintaining a fully cooperative lifecycle."

Q3: "When would you choose an Abstract Base Class (ABC) over typing.Protocol in Python?"
Script:
"Use an Abstract Base Class (`abc.ABC`) when you need nominal subtyping with guaranteed
runtime enforcement. If a subclass fails to implement an `@abstractmethod`, Python prevents
instantiation by raising a `TypeError` at runtime. ABCs are also ideal for the Template Method
pattern, where the base class provides concrete, reusable workflow logic that relies on
abstract hook methods. Conversely, choose `typing.Protocol` (PEP 544) when you want structural
subtyping—or static duck typing. Protocols decouple consumers from producers because classes
do not need to inherit from the Protocol explicitly; static type checkers like Mypy verify
compatibility purely based on method signatures."
"""

import sys
from abc import ABC, abstractmethod

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 1. ABSTRACT BASE CLASS (INTERFACE & TEMPLATE METHOD)
# ============================================================

class DataProcessor(ABC):
    """Abstract Base Class enforcing the data processing pipeline."""

    @abstractmethod
    def read_data(self) -> list[dict]:
        """Abstract hook: ingest data from source."""
        pass

    @abstractmethod
    def transform_record(self, record: dict) -> dict:
        """Abstract hook: transform single record."""
        pass

    # Template Method: Concrete pipeline orchestrating abstract steps
    def process_pipeline(self) -> list[dict]:
        raw_records = self.read_data()
        processed = [self.transform_record(r) for r in raw_records]
        return processed


class UserDataProcessor(DataProcessor):
    """Concrete implementation of DataProcessor."""
    def __init__(self, raw_input: list[dict]):
        self.raw_input = raw_input

    def read_data(self) -> list[dict]:
        return self.raw_input

    def transform_record(self, record: dict) -> dict:
        # Standardize email to lowercase
        transformed = record.copy()
        transformed["email"] = transformed["email"].strip().lower()
        transformed["active"] = True
        return transformed


class IncompleteProcessor(DataProcessor):
    """Intentionally uncompleted class for testing runtime ABC validation."""
    pass


# ============================================================
# 2. DIAMOND INHERITANCE & COOPERATIVE SUPER
# ============================================================

class RootBase:
    """Base class at the top of the diamond."""
    def __init__(self, **kwargs):
        self.trace = ["RootBase"]
        super().__init__(**kwargs)


class LeftBranch(RootBase):
    """Left branch of diamond."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trace.append("LeftBranch")


class RightBranch(RootBase):
    """Right branch of diamond."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trace.append("RightBranch")


class DiamondChild(LeftBranch, RightBranch):
    """Bottom of diamond inheriting from both Left and Right."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trace.append("DiamondChild")


# ============================================================
# 3. MIXIN PATTERN (MODULAR CROSS-CUTTING CONCERNS)
# ============================================================

class JsonSerializableMixin:
    """Mixin adding to_json serialization without storing state."""
    def to_dict(self) -> dict:
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith("_")
        }


class TimestampMixin:
    """Mixin adding timestamp tracking."""
    def __init__(self, **kwargs):
        self.created_at = "2026-09-26T12:00:00Z"
        super().__init__(**kwargs)


class Article(JsonSerializableMixin, TimestampMixin):
    """Domain model composed with mixins."""
    def __init__(self, title: str, author: str):
        self.title = title
        self.author = author
        super().__init__()


# ============================================================
# 4. COMPOSITION OVER INHERITANCE
# ============================================================

class MemoryCache:
    """Pluggable caching component."""
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, val):
        self._store[key] = val


class AuditLogger:
    """Pluggable telemetry component."""
    def __init__(self):
        self.logs = []

    def log(self, event: str):
        self.logs.append(event)


class OrderService:
    """High-level service composed of cache and logger components."""
    def __init__(self, cache: MemoryCache, logger: AuditLogger):
        # Injected dependencies (Composition / 'Has-A')
        self._cache = cache
        self._logger = logger

    def get_order(self, order_id: str) -> dict:
        cached = self._cache.get(order_id)
        if cached:
            self._logger.log(f"Cache hit for {order_id}")
            return cached

        # Simulated database fetch
        order_data = {"order_id": order_id, "status": "shipped"}
        self._cache.set(order_id, order_data)
        self._logger.log(f"Cache miss and stored {order_id}")
        return order_data


def run_tests():
    # ============================================================
    # 1. ABSTRACT BASE CLASS ENFORCEMENT & TEMPLATE METHOD
    # ============================================================

    # Attempting to instantiate an uncompleted ABC raises TypeError
    abc_blocked = False
    try:
        IncompleteProcessor()
    except TypeError:
        abc_blocked = True
    assert abc_blocked is True

    # Complete subclass instantiates and executes template method
    raw_users = [
        {"username": "Alice", "email": "ALICE@EXAMPLE.COM"},
        {"username": "Bob", "email": "  Bob@Example.Com  "},
    ]
    processor = UserDataProcessor(raw_users)
    processed = processor.process_pipeline()

    assert processed == [
        {"username": "Alice", "email": "alice@example.com", "active": True},
        {"username": "Bob", "email": "bob@example.com", "active": True},
    ]


    # ============================================================
    # 2. DIAMOND INHERITANCE & MRO VERIFICATION
    # ============================================================

    diamond = DiamondChild()

    # MRO order: DiamondChild -> LeftBranch -> RightBranch -> RootBase -> object
    expected_mro_names = [
        "DiamondChild",
        "LeftBranch",
        "RightBranch",
        "RootBase",
        "object",
    ]
    actual_mro_names = [cls.__name__ for cls in DiamondChild.mro()]
    assert actual_mro_names == expected_mro_names

    # Verification: RootBase constructor was executed EXACTLY ONCE!
    # Execution trace reflects reverse cooperative stack unwind:
    # RootBase runs, then RightBranch finishes, then LeftBranch finishes, then DiamondChild finishes
    assert diamond.trace == ["RootBase", "RightBranch", "LeftBranch", "DiamondChild"]


    # ============================================================
    # 3. MRO INCONSISTENCY DETECTION AT DEFINITION TIME
    # ============================================================

    # Creating a class hierarchy that violates C3 monotonicity raises TypeError
    class BaseX:
        pass

    class SubY(BaseX):
        pass

    inconsistent_mro_caught = False
    try:
        # Invalid: SubY must come before BaseX in class definition!
        type("InvalidHierarchy", (BaseX, SubY), {})
    except TypeError:
        inconsistent_mro_caught = True
    assert inconsistent_mro_caught is True


    # ============================================================
    # 4. MIXIN ARCHITECTURE
    # ============================================================

    article = Article("Modern Python Architecture", "Senior Engineer")
    assert article.title == "Modern Python Architecture"
    assert article.created_at == "2026-09-26T12:00:00Z"

    # JsonSerializableMixin export
    data_dict = article.to_dict()
    assert data_dict == {
        "title": "Modern Python Architecture",
        "author": "Senior Engineer",
        "created_at": "2026-09-26T12:00:00Z",
    }


    # ============================================================
    # 5. COMPOSITION OVER INHERITANCE
    # ============================================================

    cache_instance = MemoryCache()
    logger_instance = AuditLogger()
    service = OrderService(cache=cache_instance, logger=logger_instance)

    # First call: cache miss
    order1 = service.get_order("ORD-101")
    assert order1 == {"order_id": "ORD-101", "status": "shipped"}
    assert logger_instance.logs == ["Cache miss and stored ORD-101"]

    # Second call: cache hit
    order2 = service.get_order("ORD-101")
    assert order2 == {"order_id": "ORD-101", "status": "shipped"}
    assert logger_instance.logs == [
        "Cache miss and stored ORD-101",
        "Cache hit for ORD-101",
    ]


if __name__ == "__main__":
    run_tests()
    print("03_inheritance_composition_and_abcs.py tests passed!")
