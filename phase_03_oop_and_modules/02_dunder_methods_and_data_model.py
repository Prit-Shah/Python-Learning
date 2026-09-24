"""
Phase 3: OOP & Real Application Code - Dunder Methods & The Python Data Model
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Dunder methods ('__<name>__') hook your custom classes directly into Python operators.
   - Core Protocols:
     * String representation:
       - '__repr__': Unambiguous developer string (e.g. "User(id=1, name='Alice')").
       - '__str__': User-friendly display string (e.g. "Alice (#1)").
     * Equality & Hashing:
       - '__eq__': Implements 'obj1 == obj2'.
       - '__hash__': Allows instances to be stored in sets or as dictionary keys.
     * Container / Sequence protocol:
       - '__len__': Implements 'len(obj)'.
       - '__getitem__': Implements index / key access 'obj[key]'.
     * Callable protocol:
       - '__call__': Allows an instance to be called like a function: 'obj(arg)'.
   - JS/TS Analogy:
     * In JS, you write 'user.toString()' or Symbol.iterator. In Python, you implement '__str__' and '__iter__'.
     * Python's Data Model provides standard, universal protocols rather than arbitrary method names.

2. UNDER THE HOOD (CPython & Memory):
   - Operators do not invoke magic; they map to C-level slot pointers in 'PyTypeObject'.
   - When CPython encounters 'a == b', it calls 'a.__class__.__eq__(a, b)'.
   - If '__eq__' is defined but '__hash__' is not, CPython sets '__hash__ = None', making the object unhashable!

3. COMMON GOTCHA:
   - Implementing '__eq__' without implementing '__hash__':
     class Tag:
         def __init__(self, name): self.name = name
         def __eq__(self, o): return self.name == o.name
     # BUG: set([Tag('ai')]) raises TypeError: unhashable type: 'Tag'!
     # FIX: Must also implement '__hash__' or use @dataclass(frozen=True).

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "What is the Python Data Model, what are dunder methods, and why are
       __repr__ and __str__ both needed?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Data Model Protocol:
      "The Python Data Model is a framework that allows user-defined classes to seamlessly
       integrate with Python language features—like slicing, iterations, arithmetic, and context managers.
       Instead of memorizing custom APIs like obj.size() or obj.equals(), Python uses standard
       dunder methods like __len__ and __eq__."
   2. __str__ vs __repr__:
      "__str__ is intended for end users; it should be readable and clean, called by str() and print().
       __repr__ is intended for developers and debugging; it should be unambiguous and, if possible,
       look like valid Python code that could recreate the object: eval(repr(obj)) == obj.
       If __str__ is missing, Python falls back to __repr__, so a senior rule is to always implement
       __repr__ first."
   3. The Hashability Rule:
      "If you override __eq__, Python automatically unsets __hash__ to protect set/dict consistency.
       If you want value-comparable objects to be set keys, you must implement __hash__ returning a
       stable integer based on immutable attributes."
================================================================================
"""

import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class Vector2D:
    """Demonstrates arithmetic, string, equality, and hashing dunders."""

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    # 1. Developer representation
    def __repr__(self) -> str:
        return f"Vector2D(x={self.x}, y={self.y})"

    # 2. User display representation
    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    # 3. Arithmetic: Addition (+)
    def __add__(self, other: "Vector2D") -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented
        return Vector2D(self.x + other.x, self.y + other.y)

    # 4. Arithmetic: Scalar Multiplication (*)
    def __mul__(self, scalar: float) -> "Vector2D":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2D(self.x * scalar, self.y * scalar)

    # 5. Value Equality (==)
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2D):
            return False
        return self.x == other.x and self.y == other.y

    # 6. Hashing (enables inclusion in sets and dict keys)
    def __hash__(self) -> int:
        return hash((self.x, self.y))


class SmartBatch:
    """Demonstrates __len__, __getitem__, and __call__ dunders."""

    def __init__(self, items: list):
        self._items = list(items)

    # Container length: len(batch)
    def __len__(self) -> int:
        return len(self._items)

    # Sequence indexing / slicing: batch[0], batch[1:3]
    def __getitem__(self, index):
        return self._items[index]

    # Callable protocol: batch("transform_fn")
    def __call__(self, transform_fn) -> list:
        """Calling the instance runs the transformation over items."""
        return [transform_fn(x) for x in self._items]


def demonstrate_dunder_methods():
    print("\n--- 1. Vector Dunder Protocols (__repr__, __str__, __add__, __mul__) ---")
    v1 = Vector2D(3, 4)
    v2 = Vector2D(1, 2)
    
    print(f"  v1 repr: {repr(v1)}")
    print(f"  v1 str:  {v1}")
    print(f"  v1 + v2 = {v1 + v2}")
    print(f"  v1 * 3  = {v1 * 3}")
    
    # Hashability test: can be added to set
    vector_set = {v1, v2, Vector2D(3, 4)}
    print(f"  Total unique vectors in set: {len(vector_set)} (Duplicates correctly deduplicated via __hash__ & __eq__)")


def demonstrate_container_and_callable():
    print("\n--- 2. Container & Callable Protocols (__len__, __getitem__, __call__) ---")
    batch = SmartBatch(["apple", "banana", "cherry", "date"])
    print(f"  len(batch): {len(batch)}")
    print(f"  batch[1]:   {batch[1]}")
    print(f"  batch[1:3]: {batch[1:3]}")
    
    # Using __call__ to execute instance like a function:
    uppercased = batch(lambda s: s.upper())
    print(f"  batch(lambda s: s.upper()): {uppercased}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

class ShoppingCart:
    """
    Challenge:
    Implement a ShoppingCart that:
    1. Holds items as a list of dicts: [{'name': 'item', 'price': 10.0}, ...]
    2. Implements __len__ to return total number of items.
    3. Implements __getitem__ so cart[0] returns the first item.
    4. Implements __add__ so cart1 + cart2 returns a new ShoppingCart with items merged.
    5. Implements __repr__ displaying total count and total cost.
    """
    def __init__(self, items=None):
        self.items = list(items) if items else []

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __add__(self, other: "ShoppingCart") -> "ShoppingCart":
        if not isinstance(other, ShoppingCart):
            return NotImplemented
        return ShoppingCart(self.items + other.items)

    def total_cost(self) -> float:
        return sum(item["price"] for item in self.items)

    def __repr__(self) -> str:
        return f"ShoppingCart(items={len(self.items)}, total=${self.total_cost():.2f})"


def run_tests():
    print("\n[*] Running automated self-tests for 02_dunder_methods_and_data_model.py...")
    c1 = ShoppingCart([{"name": "Book", "price": 15.0}])
    c2 = ShoppingCart([{"name": "Pen", "price": 2.5}, {"name": "Notebook", "price": 5.0}])
    
    assert len(c1) == 1
    assert len(c2) == 2
    assert c2[0]["name"] == "Pen"
    
    merged = c1 + c2
    assert len(merged) == 3
    assert merged.total_cost() == 22.5
    assert "total=$22.50" in repr(merged)
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 3 - Dunder Methods & Python Data Model")
    print("=" * 65)
    demonstrate_dunder_methods()
    demonstrate_container_and_callable()
    print("-" * 65)
    run_tests()
    print("=" * 65)
