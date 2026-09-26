"""
05_modern_typing.py

============================================================
1. CONCEPT
============================================================

Python possesses a gradual, expressive type hint system (PEP 484 and subsequent
enhancements) designed to bring static verification, rich IDE tooling, and
architectural clarity to dynamic code:

1. Modern Type Annotations (Python 3.9+ & 3.10+):
   - Built-in Generic Types (PEP 585): Direct use of standard collection types
     in annotations: `list[str]`, `dict[str, int]`, `set[float]`, `tuple[int, ...]`,
     deprecating legacy `typing.List`, `typing.Dict`, etc.
   - Union Type Operator (PEP 604): Using the pipe operator `|` for unions:
     `int | str | None`, replacing `Union[int, str]` and `Optional[X]`.
   - Literal Types: Restricting values to specific strings/numbers: `Literal["read", "write"]`.
   - Immutability Flags: `Final` to declare constants and prevent variable rebinding.

2. Declarative Data Containers: Dataclasses (PEP 557):
   - `@dataclass` automatically generates `__init__`, `__repr__`, `__eq__`,
     and comparison dunders based on type annotations.
   - `frozen=True`: Creates immutable value objects.
   - `default_factory`: Safely supplies mutable defaults (e.g. `field(default_factory=list)`).
   - `__post_init__`: Executes post-construction validation or computes derived fields.

3. Static Typing for Dictionaries: TypedDict (PEP 589):
   - Enforces key names and expected value types for dictionary payloads.
   - Supports partial schemas with `total=False` or `Required` / `NotRequired` (PEP 655).

4. Structural Subtyping: Protocols (PEP 544):
   - Static duck typing: An object satisfies a `Protocol` if it implements the
     required attributes and methods, without explicit inheritance!
   - `@runtime_checkable`: Enables runtime `isinstance()` checks against protocols.

5. Runtime Reality:
   - Type hints in pure Python are METADATA stored in `__annotations__`.
   - The CPython runtime does NOT enforce type hints or perform type coercion.
   - Static type checkers (`mypy`, `pyright`) analyze types ahead-of-time; runtime
     enforcement requires libraries like `pydantic`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Type System Nature           | Gradual, Optional, Stored Metadata | Gradual, Statically Erased         |
| Union Types                  | `int | str | None`                 | `number | string | null`           |
| Interface / Duck Typing      | `typing.Protocol`                  | `interface`                        |
| Typed Key-Value Maps         | `typing.TypedDict`                 | `interface User { id: number; }`   |
| Immutable Objects            | `@dataclass(frozen=True)`          | `readonly` properties / `as const` |
| Literal Value Sets           | `Literal["GET", "POST"]`           | `'GET' | 'POST'`                   |
| Callable Signatures          | `Callable[[int, int], str]`        | `(a: number, b: number) => string` |
| Runtime Type Erasure         | Hints stored in `__annotations__`  | Erased entirely at compile-time    |
| Runtime Validation           | Requires Pydantic / dataclasses    | Requires Zod / Yup / io-ts         |
+------------------------------+------------------------------------+------------------------------------+

Key JS/TS vs Python Typing Insights:
1. TypeScript interfaces use structural subtyping by default (`duck typing`).
   Standard Python classes use nominal subtyping (inheritance). To achieve
   structural typing in Python, you must explicitly inherit from `typing.Protocol`.
2. Both Python and TypeScript do NOT enforce types at runtime natively.
   In TS, `const x: number = "hello" as any` runs without errors in node.
   In Python, `def f(x: int): pass; f("hello")` runs without runtime errors.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The `__annotations__` Dictionary:
   - When CPython compiles a module, class, or function, type expressions are
     evaluated and stored as an ordinary Python dictionary in `__annotations__`.
   - From Python 3.7+ (`from __future__ import annotations`) and future PEPs,
     annotations can be stored as lazy string literals rather than evaluated
     eagerly, completely eliminating import-time overhead and circular references.

2. Dataclass Code Generation:
   - `@dataclass` is a class decorator that inspects `cls.__annotations__`.
   - It dynamically constructs string templates for `__init__`, `__repr__`,
     and `__eq__`, compiles them using Python's `compile()` built-in, and
     attaches the resulting functions to the class dictionary.
   - Because it generates native Python bytecode, instantiation speed is identical
     to a hand-written `__init__` method.

3. Protocols and `_ProtocolMeta`:
   - `Protocol` classes inherit from a specialized metaclass `_ProtocolMeta`.
   - When decorated with `@runtime_checkable`, `isinstance(obj, MyProtocol)`
     intercepts the check using `__subclasshook__`, verifying that every callable
     and attribute declared on the protocol exists on `type(obj)`.


============================================================
4. COMMON GOTCHAS
============================================================

1. Expecting Runtime Enforcement:
   - `def double(x: int) -> int: return x * 2`
   - Calling `double("hello")` returns `"hellohello"`. Python never raises a
     `TypeError` simply because a type hint was violated.

2. Mutable Defaults in Dataclasses:
   - Writing `items: list[str] = []` inside a `@dataclass` raises a `ValueError`
     at definition time: `mutable default <class 'list'> for field items is not allowed`.
   - Fix: Always use `field(default_factory=list)`.

3. TypedDict is a Plain Dict at Runtime:
   - A `TypedDict` does NOT perform type casting or validation at runtime.
     Passing invalid types or unexpected keys succeeds without error unless
     analyzed by Mypy or validated via Pydantic.

4. Differentiating isinstance() with Generics:
   - `isinstance(data, list[int])` raises `TypeError: Subscripted generics cannot
     be used with class and instance checks`.
   - At runtime, you must test against the origin type: `isinstance(data, list)`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How do Python type hints compare to TypeScript, and are they enforced at runtime?"
Script:
"Python type hints and TypeScript share the philosophy of gradual typing, allowing
developers to add static type safety to dynamic codebases. However, while TypeScript
erases types during compilation to JavaScript, Python stores type hints at runtime
in the `__annotations__` attribute of functions, classes, and modules. Despite being
accessible at runtime, Python's interpreter ignores them entirely during execution—meaning
type violations do not raise exceptions. Static type checkers like Mypy or Pyright must
be integrated into the development workflow or CI pipeline to enforce them, while libraries
like Pydantic are used when runtime validation and coercion are required."

Q2: "What is the difference between nominal and structural subtyping in Python, and how does Protocol implement the latter?"
Script:
"Nominal subtyping requires explicit inheritance declarations: a class `Dog` is only
considered an `Animal` if it inherits from `Animal`. Structural subtyping—often called
static duck typing—treats types as compatible based purely on their shape and methods,
regardless of inheritance hierarchy. Python implements structural subtyping through
`typing.Protocol` (PEP 544). If a class implements all the methods and attributes
defined in a `Protocol`, static type checkers accept it as a valid subtype without
requiring it to inherit from that protocol. When decorated with `@runtime_checkable`,
`isinstance()` can also verify the interface at runtime."

Q3: "Explain how @dataclass optimizes class authoring and why default_factory is necessary."
Script:
"`@dataclass` eliminates boilerplate by introspecting class type annotations to
dynamically generate standard dunder methods including `__init__`, `__repr__`, and `__eq__`.
When defining mutable collection attributes like lists or dicts, assigning a default directly
like `tags: list[str] = []` is disallowed because that object would be shared across all
instances as a class attribute. To guarantee that every instance receives a fresh, isolated
container, `@dataclass` requires `field(default_factory=list)`, which invokes the factory
callable upon each instantiation."
"""

import copy
import sys
from dataclasses import asdict, astuple, dataclass, field, replace
from typing import (
    Any,
    Callable,
    Final,
    Literal,
    Protocol,
    TypedDict,
    get_type_hints,
    runtime_checkable,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# PROTOCOLS: STRUCTURAL SUBTYPING
# ============================================================

@runtime_checkable
class Renderable(Protocol):
    """Protocol requiring render() method returning a string."""
    def render(self) -> str:
        ...


class HTMLReport:
    """Class implementing Renderable WITHOUT inheriting from it."""
    def render(self) -> str:
        return "<h1>Report</h1>"


class JSONReport:
    """Class implementing Renderable WITHOUT inheriting from it."""
    def render(self) -> str:
        return '{"report": true}'


class PlainText:
    """Class that does NOT implement Renderable."""
    def to_string(self) -> str:
        return "Text"


# ============================================================
# DATACLASS DECLARATIONS
# ============================================================

@dataclass(frozen=True)
class Coordinate:
    """Immutable 2D coordinate value object."""
    x: float
    y: float


@dataclass
class UserProfile:
    """User profile with mutable defaults and computed fields."""
    user_id: int
    username: str
    roles: list[str] = field(default_factory=list)
    email: str | None = None
    display_name: str = field(init=False)

    def __post_init__(self):
        # Post-initialization to compute derived attributes
        self.display_name = f"{self.username} (ID: {self.user_id})"


# ============================================================
# TYPEDDICT DECLARATION
# ============================================================

class DatabaseConfig(TypedDict):
    host: str
    port: int
    ssl_enabled: bool


def run_tests():
    # ============================================================
    # 1. MODERN TYPE HINTS (PEP 585 & PEP 604)
    # ============================================================

    # ------------------------------------------------------------
    # Built-in collection generics (list[T], dict[K, V], tuple[...])
    # ------------------------------------------------------------
    names: list[str] = ["Alice", "Bob"]
    port_map: dict[str, int] = {"http": 80, "https": 443}
    point_pair: tuple[int, int] = (10, 20)

    assert len(names) == 2
    assert port_map["https"] == 443
    assert point_pair[0] == 10

    # ------------------------------------------------------------
    # Union types with | (Python 3.10+)
    # ------------------------------------------------------------
    def parse_identifier(val: int | str) -> str:
        return f"ID_{val}"

    assert parse_identifier(101) == "ID_101"
    assert parse_identifier("ABC") == "ID_ABC"

    # Optional represented as T | None
    def lookup_user(user_id: int) -> str | None:
        return "Alice" if user_id == 1 else None

    assert lookup_user(1) == "Alice"
    assert lookup_user(999) is None

    # ------------------------------------------------------------
    # Literal types and Final variables
    # ------------------------------------------------------------
    API_VERSION: Final[str] = "v2.0"
    assert API_VERSION == "v2.0"

    def execute_command(mode: Literal["READ", "WRITE"]) -> str:
        return f"Executing {mode}"

    assert execute_command("READ") == "Executing READ"
    assert execute_command("WRITE") == "Executing WRITE"


    # ============================================================
    # 2. RUNTIME METADATA INSPECTION (__annotations__)
    # ============================================================

    def sample_api_call(endpoint: str, timeout: int = 30) -> bool:
        """Sample function for annotation inspection."""
        return True

    hints = get_type_hints(sample_api_call)
    assert hints == {"endpoint": str, "timeout": int, "return": bool}

    # Runtime behavior ignores type violations
    def strict_looking_add(a: int, b: int) -> int:
        return a + b

    # Python runtime does NOT raise TypeError on mismatched types!
    assert strict_looking_add("hello ", "world") == "hello world"


    # ============================================================
    # 3. DATACLASSES: VALUE OBJECTS & IMMUTABILITY
    # ============================================================

    # ------------------------------------------------------------
    # Immutable value object (frozen=True)
    # ------------------------------------------------------------
    c1 = Coordinate(10.5, 20.0)
    c2 = Coordinate(10.5, 20.0)
    c3 = Coordinate(0.0, 0.0)

    # Automatic __eq__ based on field values
    assert c1 == c2
    assert c1 != c3

    # Automatic __repr__
    assert repr(c1) == "Coordinate(x=10.5, y=20.0)"

    # Mutation attempt raises FrozenInstanceError
    mutation_failed = False
    try:
        c1.x = 99.0
    except Exception:
        mutation_failed = True
    assert mutation_failed is True

    # Functional update with replace()
    c4 = replace(c1, y=30.0)
    assert c4 == Coordinate(10.5, 30.0)
    assert c1 == Coordinate(10.5, 20.0)  # Original unchanged

    # ------------------------------------------------------------
    # Mutable defaults with default_factory & __post_init__
    # ------------------------------------------------------------
    u1 = UserProfile(user_id=1, username="alice", roles=["admin"])
    u2 = UserProfile(user_id=2, username="bob")

    assert u1.display_name == "alice (ID: 1)"
    assert u2.display_name == "bob (ID: 2)"
    assert u1.roles == ["admin"]
    assert u2.roles == []  # Fresh list via default_factory!

    # Verify lists are independent objects
    u2.roles.append("editor")
    assert u1.roles == ["admin"]
    assert u2.roles == ["editor"]

    # Exporting dataclasses to dict and tuple
    assert asdict(c1) == {"x": 10.5, "y": 20.0}
    assert astuple(c1) == (10.5, 20.0)


    # ============================================================
    # 4. TYPEDDICT: TYPED MAPPINGS
    # ============================================================

    # ------------------------------------------------------------
    # Creating and querying TypedDict
    # ------------------------------------------------------------
    config: DatabaseConfig = {
        "host": "db.internal.net",
        "port": 5432,
        "ssl_enabled": True,
    }

    assert config["host"] == "db.internal.net"
    assert config["port"] == 5432
    assert config["ssl_enabled"] is True

    # At runtime, TypedDict is simply an instance of built-in dict!
    assert isinstance(config, dict)


    # ============================================================
    # 5. PROTOCOLS: STRUCTURAL SUBTYPING (DUCK TYPING)
    # ============================================================

    # ------------------------------------------------------------
    # Static Duck Typing: Classes satisfy Protocol without inheritance
    # ------------------------------------------------------------
    def render_output(item: Renderable) -> str:
        return item.render()

    html = HTMLReport()
    json_rep = JSONReport()
    plain = PlainText()

    assert render_output(html) == "<h1>Report</h1>"
    assert render_output(json_rep) == '{"report": true}'

    # ------------------------------------------------------------
    # @runtime_checkable allows isinstance() validation
    # ------------------------------------------------------------
    assert isinstance(html, Renderable) is True
    assert isinstance(json_rep, Renderable) is True
    assert isinstance(plain, Renderable) is False


    # ============================================================
    # 6. CALLABLE TYPE HINTS
    # ============================================================

    # Higher-order function with Callable annotation
    def transform_and_format(val: int, formatter: Callable[[int], str]) -> str:
        return formatter(val * 2)

    int_formatter = lambda n: f"Value: {n}"
    assert transform_and_format(10, int_formatter) == "Value: 20"


if __name__ == "__main__":
    run_tests()
    print("05_modern_typing.py tests passed!")
