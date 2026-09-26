"""
03_iterators_and_generators.py

============================================================
1. CONCEPT
============================================================

Python's iteration architecture enables lazy data evaluation, constant memory
processing, and expressive streaming pipelines:

1. The Iteration Protocol:
   - Iterable: An object that implements `__iter__()` returning an iterator,
     or `__getitem__()` supporting sequence indexing from 0.
   - Iterator: A stateful stream object that implements `__next__()` to return
     the next item, or raises `StopIteration` when exhausted. It must also
     implement `__iter__()` returning `self`.

2. Generator Functions and `yield`:
   - A function containing the `yield` statement is a generator factory.
     Calling it does NOT execute the body immediately; it returns a `generator`
     object.
   - When `next()` is called on the generator, execution advances until the
     next `yield`. Execution pauses, saving local variables and the instruction
     pointer on the heap frame.
   - Infinite series (e.g. streaming sensor data) can be represented naturally
     with zero risk of out-of-memory errors.

3. Generator Expressions:
   - Concise syntax using parentheses: `(expr for item in iterable if cond)`.
   - Evaluates lazily on demand. Unlike list comprehensions `[...]` which
     allocate the entire collection in RAM upfront, generator expressions
     maintain strictly $O(1)$ auxiliary space.

4. Bidirectional Generators (Coroutines):
   - Generators can receive values via `.send(val)`, raise exceptions via
     `.throw(ExcType)`, and be terminated early via `.close()`.

5. Delegation with `yield from` (PEP 380):
   - Transparently delegates iteration to a subgenerator.
   - Establishes a bidirectional pipeline passing `next()`, `send()`, and `throw()`
     directly between the caller and the active subgenerator, while capturing
     the subgenerator's `return` value.

6. The `itertools` Library:
   - High-performance C-implemented iterator building blocks:
     `count`, `cycle`, `chain`, `islice`, `takewhile`, `product`, `combinations`.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript            |
+------------------------------+------------------------------------+------------------------------------+
| Iterable Protocol            | `__iter__() -> Iterator`           | `[Symbol.iterator](): Iterator`    |
| Iterator Step Method         | `__next__() -> item`               | `.next() -> { value, done }`       |
| Termination Signal           | Raises `StopIteration` exception   | Returns `{ value: undefined, done: true }`|
| Generator Declaration        | Standard `def` containing `yield`  | `function* myGen()`                |
| Generator Yield              | `yield item`                       | `yield item`                       |
| Generator Expression         | `(x * 2 for x in items)`           | No syntax (use generator function) |
| Delegation                   | `yield from sub_gen`               | `yield* subGen`                    |
| Bidirectional Input          | `val = yield output` / `gen.send()`| `val = yield output` / `gen.next(val)`|
| Generator Cleanup            | `gen.close()`                      | `gen.return()`                     |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Iteration Differences:
1. Termination mechanics:
   JavaScript iterator steps return plain objects `{ value: 1, done: false }`.
   Python raises an actual exception: `StopIteration`. CPython optimizes this
   heavily in bytecode to avoid high exception-handling overhead.

2. Lazy vs Eager Transformations:
   In JS, chaining `.map().filter()` eagerly creates intermediate arrays at
   every step. In Python, chaining generator expressions or `itertools` processes
   one item through the entire pipeline before consuming the next.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. PyGenObject & Heap Stack Frames:
   - Normal function calls allocate a stack frame (`PyFrameObject`) on the C call
     stack, which is discarded upon return.
   - When a generator function is invoked, CPython flags it via code object flags
     (`CO_GENERATOR`).
   - Instead of a transient call frame, CPython allocates a `PyGenObject` on the
     heap. The `PyFrameObject` is anchored inside the generator object.
   - On `yield`, the instruction pointer (`f_lasti`) and local variables (`f_localsplus`)
     are frozen on the heap. When resumed, CPython re-enters the evaluation loop
     without re-allocating a new stack frame.

2. Memory Footprint:
   - `sys.getsizeof([x for x in range(1_000_000)])` ~ 8.4 MB of RAM.
   - `sys.getsizeof((x for x in range(1_000_000)))` ~ 200 bytes of RAM!
   - Memory consumption for a generator is $O(1)$ regardless of stream length.

3. Bytecode Implementation of Loops:
   - `for x in iterable:` compiles to:
     - `GET_ITER`: pushes `iter(iterable)` to stack.
     - `FOR_ITER`: invokes `__next__()`. If exhausted (`StopIteration`), jumps
       to loop exit. Otherwise pushes value and executes loop body.
     - `JUMP_BACKWARD`: jumps back to `FOR_ITER`.


============================================================
4. COMMON GOTCHAS
============================================================

1. Generator Exhaustion:
   - Generators are single-pass streams. Once exhausted, subsequent calls
     to `next()` raise `StopIteration`, and `list(gen)` yields `[]`.
   - Never attempt to iterate over the same generator instance twice.
   - If multiple passes are needed, recreate the generator or use `itertools.tee()`.

2. Generator Expressions with Immediate Functions:
   - `sum(x for x in items)` vs `sum([x for x in items])`
   - Writing parentheses twice `sum((x for x in items))` is redundant; Python
     allows omitting the outer parentheses when a generator expression is the
     sole argument to a function.

3. Modifying Iterables During Iteration:
   - Calling `lst.append()` or `lst.pop()` while iterating with `for item in lst:`
     desynchronizes the internal index pointer, causing skipped elements.

4. Unhandled `GeneratorExit` on Cleanup:
   - Inside a generator, catching all exceptions with `except Exception:` does NOT
     catch `GeneratorExit` (which inherits directly from `BaseException`).
   - If you catch `BaseException` and fail to re-raise `GeneratorExit`, Python raises
     `RuntimeError: generator ignored GeneratorExit`.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Explain the Python iteration protocol and how a custom iterator is created."
Script:
"The Python iteration protocol consists of two methods: `__iter__()` and `__next__()`.
An iterable implements `__iter__()` to return an iterator instance. An iterator
implements `__next__()`, which returns the next item on each invocation and raises
`StopIteration` when no items remain, as well as `__iter__()` returning `self` so that
iterators can themselves be used in loops. To build a custom iterator, we define a class
implementing both methods, tracking iteration state internally in instance attributes."

Q2: "How do generators work internally in CPython, and what advantages do they provide?"
Script:
"When a function containing `yield` is called, CPython recognizes the `CO_GENERATOR`
code flag and returns a `PyGenObject` wrapping a heap-allocated execution frame rather
than running the code immediately. When `next()` is called, CPython resumes execution
at the saved bytecode offset (`f_lasti`). When `yield` is reached, local variables are
preserved in `f_localsplus`, and the value is yielded. This provides lazy evaluation
and strict $O(1)$ auxiliary memory usage, making generators ideal for processing
massive files, database cursors, and streaming pipelines without memory exhaustion."

Q3: "What does 'yield from' do, and why is it superior to manual loop yielding?"
Script:
"`yield from` (introduced in PEP 380) delegates iteration to a subgenerator or iterable.
Beyond replacing a manual `for item in subgen: yield item` loop, `yield from` sets up a
full bidirectional communication channel. It transparently forwards `.send(val)` inputs,
propagates `.throw()` exceptions, coordinates `.close()` lifecycle events, and directly
returns the value returned by the subgenerator via `return val` upon its completion."
"""

import itertools
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Custom Iterator Class implementing the Iteration Protocol
class CountdownIterator:
    """Demonstrates manual implementation of the Python iteration protocol."""
    def __init__(self, start):
        self.current = start

    def __iter__(self):
        # An iterator must return itself from __iter__
        return self

    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        val = self.current
        self.current -= 1
        return val


# Custom Iterable (returns a fresh Iterator on each __iter__ call)
class CountdownCollection:
    def __init__(self, start):
        self.start = start

    def __iter__(self):
        return CountdownIterator(self.start)


def run_tests():
    # ============================================================
    # 1. THE ITERATION PROTOCOL (__iter__ and __next__)
    # ============================================================

    # ------------------------------------------------------------
    # Using iter() and next() directly on built-in types
    # ------------------------------------------------------------
    fruits = ["apple", "banana"]
    iterator = iter(fruits)

    assert next(iterator) == "apple"
    assert next(iterator) == "banana"

    # Next call raises StopIteration
    stop_iteration_raised = False
    try:
        next(iterator)
    except StopIteration:
        stop_iteration_raised = True
    assert stop_iteration_raised is True

    # ------------------------------------------------------------
    # Testing Custom Iterator class
    # ------------------------------------------------------------
    cd_iter = CountdownIterator(3)
    assert next(cd_iter) == 3
    assert next(cd_iter) == 2
    assert next(cd_iter) == 1

    try:
        next(cd_iter)
        assert False, "Should have raised StopIteration"
    except StopIteration:
        pass

    # ------------------------------------------------------------
    # Iterable vs Iterator reusability:
    # A collection returning fresh iterators can be looped multiple times
    # ------------------------------------------------------------
    countdown_collection = CountdownCollection(3)
    assert list(countdown_collection) == [3, 2, 1]
    # Second iteration succeeds because __iter__ instantiates a fresh iterator!
    assert list(countdown_collection) == [3, 2, 1]


    # ============================================================
    # 2. GENERATOR FUNCTIONS AND YIELD
    # ============================================================
    # Functions with yield return generator objects.

    # ------------------------------------------------------------
    # Fibonacci generator (Lazy stream)
    # ------------------------------------------------------------
    def fibonacci_sequence(limit):
        a, b = 0, 1
        count = 0
        while count < limit:
            yield a
            a, b = b, a + b
            count += 1

    fib_gen = fibonacci_sequence(6)
    assert list(fib_gen) == [0, 1, 1, 2, 3, 5]

    # Generator is now exhausted
    assert list(fib_gen) == []

    # ------------------------------------------------------------
    # Infinite generator with break
    # ------------------------------------------------------------
    def infinite_counter(start=0):
        val = start
        while True:
            yield val
            val += 1

    collected = []
    for item in infinite_counter(10):
        if item > 14:
            break
        collected.append(item)

    assert collected == [10, 11, 12, 13, 14]


    # ============================================================
    # 3. GENERATOR EXPRESSIONS & MEMORY PROFILES
    # ============================================================
    # (expr for item in iterable) vs [expr for item in iterable]

    # ------------------------------------------------------------
    # Memory footprint comparison
    # ------------------------------------------------------------
    gen_exp = (x * 2 for x in range(1_000_000))
    # Generator object size is constant and tiny
    assert sys.getsizeof(gen_exp) < 300

    # Consuming only what is needed lazily
    first_three = [next(gen_exp), next(gen_exp), next(gen_exp)]
    assert first_three == [0, 2, 4]

    # ------------------------------------------------------------
    # Reductions with generator expressions (O(1) memory)
    # ------------------------------------------------------------
    # Note: Outer parentheses omitted when sole argument to sum
    total_sum = sum(x for x in range(10))
    assert total_sum == 45


    # ============================================================
    # 4. ADVANCED GENERATOR CONTROL: send(), throw(), close()
    # ============================================================

    # ------------------------------------------------------------
    # send(): Bidirectional data transmission
    # ------------------------------------------------------------
    def accumulator():
        total = 0
        while True:
            # Yield current total, receive new value to add
            val = yield total
            if val is None:
                break
            total += val

    acc = accumulator()
    # Priming the generator to advance to first yield
    assert next(acc) == 0

    assert acc.send(10) == 10
    assert acc.send(25) == 35
    assert acc.send(5) == 40

    # ------------------------------------------------------------
    # close(): Terminate generator
    # ------------------------------------------------------------
    acc.close()
    closed_raised = False
    try:
        acc.send(10)
    except StopIteration:
        closed_raised = True
    assert closed_raised is True


    # ============================================================
    # 5. SUBGENERATOR DELEGATION: yield from (PEP 380)
    # ============================================================

    # ------------------------------------------------------------
    # Flattening nested sequences
    # ------------------------------------------------------------
    def flatten(nested_iterable):
        for element in nested_iterable:
            if isinstance(element, (list, tuple)):
                yield from flatten(element)
            else:
                yield element

    nested_data = [1, [2, [3, 4], 5], [6, 7]]
    assert list(flatten(nested_data)) == [1, 2, 3, 4, 5, 6, 7]

    # ------------------------------------------------------------
    # Capturing subgenerator return values with yield from
    # ------------------------------------------------------------
    def sub_task():
        yield "sub_step_1"
        yield "sub_step_2"
        return "sub_task_completed"

    def coordinator():
        yield "start"
        result = yield from sub_task()
        yield f"result: {result}"

    coord_output = list(coordinator())
    assert coord_output == ["start", "sub_step_1", "sub_step_2", "result: sub_task_completed"]


    # ============================================================
    # 6. STREAMING DATA PIPELINES (Producer -> Transform -> Consumer)
    # ============================================================
    # Chaining generators allows high-throughput, low-memory ETL.

    raw_log_lines = [
        "2026-09-26 INFO User login: alice",
        "2026-09-26 ERROR DB connection timeout",
        "2026-09-26 INFO Page view: /dashboard",
        "2026-09-26 ERROR Payment gateway unreachable",
    ]

    # Stage 1: Line producer
    def read_lines(lines):
        for line in lines:
            yield line

    # Stage 2: Filter errors
    def filter_errors(lines_gen):
        for line in lines_gen:
            if "ERROR" in line:
                yield line

    # Stage 3: Extract message
    def extract_messages(error_gen):
        for err in error_gen:
            yield err.split("ERROR ")[1]

    pipeline = extract_messages(filter_errors(read_lines(raw_log_lines)))
    error_messages = list(pipeline)

    assert error_messages == [
        "DB connection timeout",
        "Payment gateway unreachable",
    ]


    # ============================================================
    # 7. THE itertools STANDARD LIBRARY MODULE
    # ============================================================

    # ------------------------------------------------------------
    # islice(): Slicing any iterator lazily without materialization
    # ------------------------------------------------------------
    count_from_10 = itertools.count(10, step=2)  # 10, 12, 14, 16, 18, ...
    sliced_items = list(itertools.islice(count_from_10, 5))
    assert sliced_items == [10, 12, 14, 16, 18]

    # ------------------------------------------------------------
    # chain(): Concatenating iterables seamlessly
    # ------------------------------------------------------------
    ch1 = [1, 2]
    ch2 = [3, 4]
    chained = list(itertools.chain(ch1, ch2, [5, 6]))
    assert chained == [1, 2, 3, 4, 5, 6]

    # ------------------------------------------------------------
    # takewhile() and dropwhile()
    # ------------------------------------------------------------
    nums = [1, 3, 5, 8, 9, 10, 11]
    taken = list(itertools.takewhile(lambda x: x < 7, nums))
    assert taken == [1, 3, 5]

    dropped = list(itertools.dropwhile(lambda x: x < 7, nums))
    assert dropped == [8, 9, 10, 11]

    # ------------------------------------------------------------
    # product() and combinations()
    # ------------------------------------------------------------
    cartesian = list(itertools.product(["A", "B"], [1, 2]))
    assert cartesian == [("A", 1), ("A", 2), ("B", 1), ("B", 2)]

    combs = list(itertools.combinations([1, 2, 3], 2))
    assert combs == [(1, 2), (1, 3), (2, 3)]


    # ============================================================
    # 8. SHORT-CIRCUITING BOOLEAN EVALUATION: any() AND all()
    # ============================================================
    # Evaluates generator lazily, stopping immediately upon definitive result.

    probes = []

    def probe_num(n):
        probes.append(n)
        return n % 2 == 0

    # any stops on first True
    has_even = any(probe_num(x) for x in [1, 3, 4, 5, 6])
    assert has_even is True
    assert probes == [1, 3, 4]  # 5 and 6 never evaluated!

    probes.clear()

    # all stops on first False
    all_even = all(probe_num(x) for x in [2, 4, 5, 8])
    assert all_even is False
    assert probes == [2, 4, 5]  # 8 never evaluated!


if __name__ == "__main__":
    run_tests()
    print("03_iterators_and_generators.py tests passed!")
