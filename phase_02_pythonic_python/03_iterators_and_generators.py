"""
1. CONCEPT & JS/TS ANALOGY
Iteration protocol: `__iter__` returns iterator, `__next__` returns next item or raises StopIteration
Generators with yield: lazy evaluation, memory efficiency
Generator expressions: `(x*2 for x in range(10))`

JS Analogy:
JS has the `Symbol.iterator` protocol and `.next()` returning `{value, done}`. Python has `__iter__` and `__next__` raising `StopIteration`.
JS generators use `function*` and `yield`. Python uses standard `def` with `yield` inside.
JS array mapping `[1,2].map(x => x*2)` creates a new array. Python generator expressions `(x*2 for x in ...)` are lazy and evaluated on-demand.

2. UNDER THE HOOD (CPython & Memory)
When a function contains `yield`, CPython flags it as a generator function. Calling it returns a generator object, which wraps the frame object.
The execution state (local variables, instruction pointer) is saved on `yield` and resumed on `__next__`. This is highly memory efficient.

3. COMMON GOTCHA
Generators are exhausted after one pass. Calling `list(gen)` twice will yield an empty list the second time.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "What is the difference between a generator and a list comprehension? When would you use each?"
A: "A list comprehension evaluates entirely in memory, creating a complete list upfront. A generator expression looks similar but uses parentheses, and evaluates lazily, yielding one item at a time.
You should use list comprehensions when you need a smaller, finite list to iterate over multiple times or to access elements by index. You should use a generator when dealing with large or infinite datasets where loading everything into memory is impractical, as generators have a tiny memory footprint and process data in a single pass."

5. Self-tests
See run_tests()
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def demonstrate_iteration_protocol():
    print("--- Iteration Protocol ---")
    nums = [1, 2]
    iterator = iter(nums) # calls __iter__
    print(next(iterator)) # calls __next__
    print(next(iterator))
    try:
        next(iterator)
    except StopIteration:
        print("StopIteration raised!")

def demonstrate_generators():
    print("\n--- Generators ---")
    def fibonacci(n):
        a, b = 0, 1
        for _ in range(n):
            yield a
            a, b = b, a + b
            
    fib_gen = fibonacci(5)
    print(f"Fib generator object: {fib_gen}")
    print(f"Values: {list(fib_gen)}")

def demonstrate_generator_expressions():
    print("\n--- Generator Expressions ---")
    # List comprehension (memory heavy)
    list_comp = [x*2 for x in range(5)]
    print(f"List comp: {list_comp}")
    
    # Generator expression (memory light)
    gen_expr = (x*2 for x in range(5))
    print(f"Gen expr: {gen_expr}")
    print(f"Gen expr materialized: {list(gen_expr)}")
    print(f"Gen expr materialized twice: {list(gen_expr)} (Exhausted!)")

def demonstrate_builtin_helpers():
    print("\n--- Built-in Helpers ---")
    names = ["Alice", "Bob"]
    scores = [85, 92]
    
    for i, name in enumerate(names):
        print(f"Index {i}: {name}")
        
    for name, score in zip(names, scores):
        print(f"{name} scored {score}")
        
    print(f"Any score > 90? {any(s > 90 for s in scores)}")
    print(f"All scores > 90? {all(s > 90 for s in scores)}")

def run_tests():
    # Generator exhaustion
    gen = (x for x in range(3))
    assert list(gen) == [0, 1, 2]
    assert list(gen) == [] # Exhausted
    
    # Iter protocol
    it = iter([1])
    assert next(it) == 1
    try:
        next(it)
        assert False, "Should have raised StopIteration"
    except StopIteration:
        pass
        
    # Built-ins
    assert any([False, True, False])
    assert not all([False, True, False])
    
    print("\nAll iterator tests passed!")

if __name__ == '__main__':
    demonstrate_iteration_protocol()
    demonstrate_generators()
    demonstrate_generator_expressions()
    demonstrate_builtin_helpers()
    run_tests()
