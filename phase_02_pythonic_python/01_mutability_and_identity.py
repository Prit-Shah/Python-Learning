"""
01_mutability_and_identity.py

============================================================
1. CONCEPT
============================================================

Python utilizes an object-centric memory model governed by references,
identity, and mutability:

1. Everything is a PyObject:
   - In Python, variables do NOT hold values directly; they hold pointers
     (references) to objects allocated on the heap.
   - Assignment (`x = 42`) binds the name `x` in the current namespace
     to the memory address of the object `42`.

2. Mutability Classification:
   - Immutable types: Cannot be changed after creation.
     `int`, `float`, `bool`, `str`, `tuple`, `frozenset`, `bytes`.
     Modifying an immutable object always produces a brand-new object.
   - Mutable types: Can be modified in-place without altering identity (`id`).
     `list`, `dict`, `set`, `bytearray`, user-defined classes (unless frozen).

3. Identity (`is`) vs Equality (`==`):
   - `a is b`: Identity test. Evaluates whether `id(a) == id(b)` (whether
     both names point to the exact same physical memory address).
   - `a == b`: Equality test. Invokes `a.__eq__(b)` to evaluate whether
     both objects have equivalent values/contents.

4. CPython Interning & Caching:
   - CPython pre-allocates and caches integers in the range [-5, 256].
   - CPython interns string literals that resemble valid Python identifiers.
   - Singletons like `None`, `True`, and `False` exist only once per interpreter.

5. Shallow vs Deep Copy:
   - Reference assignment (`b = a`): No copy is made; creates a new alias.
   - Shallow copy (`copy.copy(a)`, `a[:]`, `a.copy()`): Creates a new outer
     container, but populates it with references to the original inner objects.
   - Deep copy (`copy.deepcopy(a)`): Recursively traverses and constructs new
     copies of all child objects, using a memoization dictionary to handle cycles.

6. Evaluation Strategy: "Pass-by-Object-Reference" (Call by Sharing):
   - Arguments are passed by pointer reference.
   - In-place mutations on mutable arguments affect the caller's object.
   - Re-binding an argument identifier inside a function has zero effect on the caller.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Value Equality               | `a == b` (calls `__eq__`)          | `JSON.stringify(a) === ...` (obj)  |
| Identity (Same Address)      | `a is b` (checks memory address)   | `a === b` (for objects / symbols)  |
| Immutable Sequences          | `tuple`, `str`, `bytes`            | `Object.freeze([1, 2])`            |
| Shallow Copy                 | `a.copy()`, `copy.copy(a)`, `a[:]` | `[...arr]`, `{...obj}`             |
| Deep Copy                    | `copy.deepcopy(a)`                 | `structuredClone(obj)`             |
| Immutability modifier        | No `const` keyword                 | `const` (prevents reassignment)    |
| Reassignment vs Mutation     | Rebinding pointer vs in-place edit | Same conceptual distinction        |
| Function Argument Passing    | Call by Sharing (object reference) | Call by Sharing (object reference) |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Gotcha:
- In JavaScript, `===` checks value for primitives (string, number, boolean)
  and reference identity for objects.
- In Python, `is` ALWAYS checks memory identity, while `==` ALWAYS checks value
  equality across all types!
- Python has no `const` keyword. Variables can always be rebound unless
  protected by a custom descriptor or property.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyObject Structure:
   - Every CPython object on the heap begins with `PyObject_HEAD`:
     ```c
     typedef struct _object {
         _PyObject_HEAD_EXTRA // doubly-linked list for GC tracking
         Py_ssize_t ob_refcnt; // Reference counter for memory reclamation
         struct _typeobject *ob_type; // Pointer to object's type struct
     } PyObject;
     ```
   - For variable-sized objects (e.g., `list`, `str`, `int`), `PyVarObject`
     adds `ob_size`.

2. The Memory Identity Function `id()`:
   - In CPython, `id(obj)` returns the exact virtual memory address:
     `reinterpret_cast<uintptr_t>(obj)`.
   - `a is b` is directly implemented as the C comparison: `obj_a == obj_b`.

3. Small Integer Cache & String Interning:
   - During startup, CPython initializes an array of 312 `PyLongObject` structs
     representing integers from `-5` to `256`. Any integer computation producing
     a number in this range returns a pointer to this pre-allocated array.
   - String interning maintains an internal `dict` of strings to eliminate
     duplicate allocations and speed up dict lookups from string comparison
     down to a single pointer equality check.

4. Garbage Collection (Reference Counting + Cyclic GC):
   - CPython frees an object immediately when its `ob_refcnt` drops to zero.
   - For circular references (e.g., `a.child = b; b.parent = a`), a generational
     cyclic garbage collector (`gc` module) periodically detects and breaks cycles.


============================================================
4. COMMON GOTCHAS
============================================================

1. The Variable Aliasing Trap:
   - `a = [1, 2, 3]`; `b = a`; `b.append(4)`
   - Both `a` and `b` now evaluate to `[1, 2, 3, 4]` because both names point
     to the identical underlying `PyObject`.

2. The Mutable Default Argument Bug:
   - Default arguments are stored in the function's `__defaults__` tuple, which
     is created once at definition time.
   - Mutating a default argument permanently changes the function's internal state.

3. In-Place Operators on Lists Inside Tuples (The Python Puzzle):
   - `t = ([1, 2], 3)`
   - `t[0] += [4]`
   - This statement raises `TypeError: 'tuple' object does not support item assignment`,
     YET the list IS successfully mutated to `[1, 2, 4]`!
   - Why? `+=` executes `list.__iadd__` (which succeeds in-place), and THEN
     attempts to store the result back into `t[0]` (which fails because tuple is immutable).

4. Shallow Copying Nested Containers:
   - `original = [[1, 2], [3, 4]]`
   - `shallow = original.copy()`
   - `shallow[0].append(99)`
   - Both `original[0]` and `shallow[0]` are modified because only the outer list
     was copied; the inner lists are shared references.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain how Python passes arguments to functions: pass-by-value or pass-by-reference?"
Script:
"Python uses 'pass-by-object-reference', often referred to as 'call by sharing'.
When an argument is passed into a function, a reference (pointer) to the actual
object is copied into the function's local namespace. If the object is mutable—such
as a list or dictionary—and you mutate it in-place using methods like `.append()` or
key assignments, the caller will observe those mutations because both names point
to the same underlying memory address. However, if you reassign the local parameter
variable, you simply re-bind the local name to a new object, leaving the caller's
original reference untouched."

Q2: "What is the difference between 'is' and '==' in Python, and when should you use each?"
Script:
"`==` checks for value equality by invoking the object's `__eq__` method, meaning
two distinct objects residing at different memory locations can evaluate as equal if
their contents match. In contrast, `is` checks reference identity by comparing memory
addresses directly (`id(a) == id(b)`). In production Python, `is` should be reserved
exclusively for identity checks against singleton objects like `None`, `True`, `False`,
or custom sentinel objects. For all numerical and structural comparisons, `==` should
always be used."

Q3: "How does copy.copy() differ from copy.deepcopy(), and how does deepcopy handle cyclic references?"
Script:
"`copy.copy()` performs a shallow copy: it constructs a new container object, but
populates it with references to the child objects found in the original.
`copy.deepcopy()` recursively traverses the entire object graph, constructing new
instances of every encountered object. To avoid infinite recursion caused by cyclic
references (where an object directly or indirectly references itself), `deepcopy`
maintains an internal memoization dictionary mapping the `id` of each source object
to its newly created duplicate."
"""

import copy
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tests():
    # ============================================================
    # 1. OBJECT IDENTITY AND MEMORY ADDRESSES (id and is)
    # ============================================================
    # Every object in Python has an identity: an integer representing
    # its memory address in CPython.

    # ------------------------------------------------------------
    # id() returns memory address
    # ------------------------------------------------------------
    sample_obj = [10, 20, 30]
    obj_address = id(sample_obj)
    assert isinstance(obj_address, int)

    # Aliasing shares identical memory address
    alias_obj = sample_obj
    assert id(alias_obj) == id(sample_obj)
    assert alias_obj is sample_obj

    # ------------------------------------------------------------
    # Identity (is) vs Equality (==)
    # Distinct objects can have equal values
    # ------------------------------------------------------------
    list_one = [1, 2, 3]
    list_two = [1, 2, 3]

    # Contents are identical -> equality is True
    assert list_one == list_two

    # Memory addresses are distinct -> identity is False
    assert list_one is not list_two
    assert id(list_one) != id(list_two)

    # ------------------------------------------------------------
    # Singleton comparison: Always use 'is' for None, True, False
    # ------------------------------------------------------------
    val = None
    assert val is None
    assert val is not False

    flag = True
    assert flag is True


    # ============================================================
    # 2. MUTABLE VS IMMUTABLE TYPES
    # ============================================================
    # Immutable objects cannot change state; operations return new objects.
    # Mutable objects modify state in-place at the same memory address.

    # ------------------------------------------------------------
    # Immutable: String re-binding creates a NEW object
    # ------------------------------------------------------------
    original_str = "hello"
    str_id_initial = id(original_str)

    original_str += " world"
    str_id_after = id(original_str)

    assert original_str == "hello world"
    assert str_id_initial != str_id_after  # New memory location!

    # ------------------------------------------------------------
    # Mutable: List modification preserves memory address
    # ------------------------------------------------------------
    original_list = [1, 2, 3]
    list_id_initial = id(original_list)

    original_list.append(4)
    list_id_after = id(original_list)

    assert original_list == [1, 2, 3, 4]
    assert list_id_initial == list_id_after  # In-place mutation!

    # ------------------------------------------------------------
    # Immutability of compound objects: Tuple containing a mutable list
    # The tuple reference is fixed, but the contained list can be mutated!
    # ------------------------------------------------------------
    inner_list = ["a", "b"]
    compound_tuple = (inner_list, 100)

    # Tuple memory address is fixed
    tuple_id_before = id(compound_tuple)

    # Mutate the list inside the tuple
    compound_tuple[0].append("c")

    assert compound_tuple == (["a", "b", "c"], 100)
    assert id(compound_tuple) == tuple_id_before


    # ============================================================
    # 3. CPYTHON OPTIMIZATIONS: SMALL INT CACHE & INTERNING
    # ============================================================
    # CPython optimizes memory and speed via object interning.

    # ------------------------------------------------------------
    # Small integer caching: [-5, 256]
    # Numbers in this range share singleton instances
    # ------------------------------------------------------------
    cached_a = 256
    cached_b = 256
    assert cached_a is cached_b

    cached_neg1 = -5
    cached_neg2 = -5
    assert cached_neg1 is cached_neg2

    # ------------------------------------------------------------
    # Explicit String Interning via sys.intern()
    # Forces two dynamically computed strings into the same singleton
    # ------------------------------------------------------------
    dynamic_s1 = sys.intern("long_custom_identifier_token_xyz")
    dynamic_s2 = sys.intern("long_custom_identifier_token_xyz")
    assert dynamic_s1 is dynamic_s2


    # ============================================================
    # 4. VARIABLE ALIASING AND IN-PLACE OPERATORS
    # ============================================================

    # ------------------------------------------------------------
    # Aliasing Trap: Multiple names bound to the same mutable object
    # ------------------------------------------------------------
    shared_data = {"status": "pending", "retries": 0}
    alias_data = shared_data

    alias_data["status"] = "completed"
    alias_data["retries"] += 1

    # shared_data reflects the changes made through alias_data
    assert shared_data["status"] == "completed"
    assert shared_data["retries"] == 1

    # ------------------------------------------------------------
    # In-place operators (+=) on mutables vs immutables
    # On lists, += calls __iadd__ (mutates in-place).
    # On lists, + creates a brand new list.
    # ------------------------------------------------------------
    list_a = [1, 2]
    list_b = list_a
    list_a += [3]  # In-place mutation!
    assert list_a is list_b
    assert list_b == [1, 2, 3]

    list_c = [1, 2]
    list_d = list_c
    list_c = list_c + [3]  # Creates a new list and re-binds list_c!
    assert list_c is not list_d
    assert list_c == [1, 2, 3]
    assert list_d == [1, 2]

    # ------------------------------------------------------------
    # The Tuple += Mutation Puzzle
    # Mutating a mutable child of a tuple via += raises TypeError,
    # yet still succeeds in-place!
    # ------------------------------------------------------------
    puzzle_tuple = ([10, 20],)
    puzzle_raised_type_error = False

    try:
        puzzle_tuple[0] += [30]
    except TypeError:
        puzzle_raised_type_error = True

    assert puzzle_raised_type_error is True
    # The list INSIDE the tuple was actually mutated before the assignment failed!
    assert puzzle_tuple[0] == [10, 20, 30]


    # ============================================================
    # 5. SHALLOW VS DEEP COPYING
    # ============================================================

    # ------------------------------------------------------------
    # Shallow Copy: Outer container copied, inner references shared
    # Techniques: list.copy(), dict.copy(), copy.copy(), slice [:]
    # ------------------------------------------------------------
    original_nested = [[1, 2], [3, 4]]
    shallow_copied = copy.copy(original_nested)

    assert shallow_copied == original_nested
    assert shallow_copied is not original_nested  # Outer container is distinct!

    # Mutating outer container does NOT affect original
    shallow_copied.append([5, 6])
    assert len(original_nested) == 2
    assert len(shallow_copied) == 3

    # Mutating INNER element DOES affect original (shared reference!)
    shallow_copied[0].append(99)
    assert original_nested[0] == [1, 2, 99]
    assert shallow_copied[0] is original_nested[0]

    # ------------------------------------------------------------
    # Deep Copy: Recursively copies all nested objects
    # ------------------------------------------------------------
    deep_source = [[10, 20], [30, 40]]
    deep_copied = copy.deepcopy(deep_source)

    assert deep_copied == deep_source
    assert deep_copied is not deep_source
    assert deep_copied[0] is not deep_source[0]  # Inner lists are new objects!

    # Mutating inner element of deep copy leaves original untouched
    deep_copied[0].append(999)
    assert deep_source[0] == [10, 20]
    assert deep_copied[0] == [10, 20, 999]

    # ------------------------------------------------------------
    # Deep Copy with Cyclic References
    # copy.deepcopy handles self-referential cycles using its memo dict
    # ------------------------------------------------------------
    node_a = {"name": "Node A"}
    node_b = {"name": "Node B"}
    node_a["neighbor"] = node_b
    node_b["neighbor"] = node_a  # Cycle!

    cycle_copy = copy.deepcopy(node_a)
    assert cycle_copy["name"] == "Node A"
    assert cycle_copy["neighbor"]["name"] == "Node B"
    # Verifying cycle is preserved in the new copy without infinite recursion
    assert cycle_copy["neighbor"]["neighbor"] is cycle_copy
    assert cycle_copy is not node_a


    # ============================================================
    # 6. FUNCTION ARGUMENT PASSING: CALL BY SHARING
    # ============================================================

    # ------------------------------------------------------------
    # In-place mutation inside function modifies caller's object
    # ------------------------------------------------------------
    def mutate_in_place(target_list):
        target_list.append("mutated_by_callee")

    caller_list = ["init"]
    mutate_in_place(caller_list)
    assert caller_list == ["init", "mutated_by_callee"]

    # ------------------------------------------------------------
    # Parameter re-binding inside function DOES NOT affect caller
    # ------------------------------------------------------------
    def rebind_parameter(target_list):
        target_list = ["completely", "new", "list"]
        return target_list

    stable_list = ["stay", "same"]
    returned_list = rebind_parameter(stable_list)
    assert stable_list == ["stay", "same"]  # Caller untouched!
    assert returned_list == ["completely", "new", "list"]


    # ============================================================
    # 7. MUTABLE DEFAULT ARGUMENT PATTERN
    # ============================================================

    # ------------------------------------------------------------
    # Bug demonstration: defaults stored in __defaults__
    # ------------------------------------------------------------
    def accumulator(item, storage=[]):
        storage.append(item)
        return storage

    res1 = accumulator("A")
    assert res1 == ["A"]
    res2 = accumulator("B")
    assert res2 == ["A", "B"]  # State persisted across invocations!

    # ------------------------------------------------------------
    # Idiomatic resolution: None sentinel with lazy instantiation
    # ------------------------------------------------------------
    def safe_accumulator(item, storage=None):
        if storage is None:
            storage = []
        storage.append(item)
        return storage

    safe_res1 = safe_accumulator("A")
    assert safe_res1 == ["A"]
    safe_res2 = safe_accumulator("B")
    assert safe_res2 == ["B"]  # Fresh storage allocated!


if __name__ == "__main__":
    run_tests()
    print("01_mutability_and_identity.py tests passed!")
