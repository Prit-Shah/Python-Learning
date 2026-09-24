"""
1. CONCEPT & JS/TS ANALOGY
Type hints basics: `int`, `str`, `list[str]`, `dict[str, int]`
`Optional` vs `X | None` (Python 3.10+)
`dataclasses` for declarative object shapes
`TypedDict` and `Protocol`

JS Analogy:
Python type hints are like TypeScript types/interfaces.
TypeScript erases types at compile time and runs pure JS. Python also essentially ignores type hints at runtime (they are just annotations in `__annotations__`), meaning NO runtime enforcement occurs natively.
`Protocol` in Python is structural subtyping (static duck typing), exactly like TS interfaces.
`dataclass` is similar to TS classes with auto-generated constructors.

2. UNDER THE HOOD (CPython & Memory)
Type annotations are stored in the `__annotations__` dictionary of the module, class, or function.
They incur minimal runtime cost (evaluating the annotation expressions) but do not affect logic.
External tools like `mypy` or `pyright` read the AST and perform static analysis.

3. COMMON GOTCHA
Thinking type hints prevent runtime errors. `def add(a: int, b: int): return a + b` will happily accept `add("a", "b")` at runtime and return `"ab"`. You need tools like Pydantic for runtime validation.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "How does Python typing compare to TypeScript? Are type hints enforced at runtime?"
A: "Both Python type hints and TypeScript provide static type checking to catch errors before code runs. However, while TypeScript has strict compiler checks, Python's type hints are purely metadata stored in the __annotations__ attribute and are completely ignored by the Python runtime.
This means type hints do not prevent runtime type errors or perform any coercion. To enforce them statically, you must run an external tool like Mypy or Pyright in your CI pipeline. If you need runtime validation, you would use a library like Pydantic, which validates data at runtime."

5. Self-tests
See run_tests()
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dataclasses import dataclass, field
from typing import TypedDict, Protocol

def demonstrate_basic_type_hints():
    print("--- Basic Type Hints ---")
    def greet(name: str) -> str:
        return f"Hello {name}"
        
    # Union types (3.10+)
    def process(data: int | str | None = None) -> None:
        print(f"Processing: {data}")
        
    print(greet("Alice"))
    process(10)
    process("Ten")
    process()
    
    print(f"greet annotations: {greet.__annotations__}")

def demonstrate_dataclasses():
    print("\n--- Dataclasses ---")
    @dataclass(frozen=True)
    class User:
        id: int
        name: str
        tags: list[str] = field(default_factory=list)
        
    u1 = User(1, "Alice", ["admin"])
    print(f"User: {u1}")
    try:
        # Frozen means immutable
        u1.name = "Bob"  # type: ignore
    except Exception as e: # FrozenInstanceError inherits from Exception
        print(f"Caught error on mutation: {type(e).__name__}")

def demonstrate_protocol():
    print("\n--- Protocols (Structural Subtyping) ---")
    class Quacker(Protocol):
        def quack(self) -> str: ...
        
    class Duck:
        def quack(self) -> str:
            return "Quack!"
            
    class Person:
        def quack(self) -> str:
            return "I'm pretending to be a duck"
            
    def make_sound(q: Quacker):
        print(q.quack())
        
    make_sound(Duck())
    make_sound(Person()) # Works! Static duck typing.

def demonstrate_typeddict():
    print("\n--- TypedDict ---")
    class Config(TypedDict):
        host: str
        port: int
        
    valid_config: Config = {"host": "localhost", "port": 8080}
    print(f"Valid config: {valid_config}")
    # At runtime, invalid_config works perfectly fine despite TypedDict!
    invalid_config: Config = {"host": 123, "port": "not_an_int"} # type: ignore
    print(f"Invalid config (runtime ignores hints): {invalid_config}")

def run_tests():
    # Dataclass tests
    @dataclass
    class Point:
        x: int
        y: int
        
    p1 = Point(1, 2)
    p2 = Point(1, 2)
    assert p1 == p2 # Auto eq
    
    # Runtime ignores hints
    def add(a: int, b: int) -> int:
        return a + b
    assert add("a", "b") == "ab" # Python doesn't care at runtime!
    
    print("\nAll typing tests passed!")

if __name__ == '__main__':
    demonstrate_basic_type_hints()
    demonstrate_dataclasses()
    demonstrate_protocol()
    demonstrate_typeddict()
    run_tests()
