"""
1. CONCEPT & JS/TS ANALOGY
Decorators: functions that wrap other functions, `@decorator` syntax
`functools.wraps` to preserve metadata
Context managers: `with` statement, `__enter__`/`__exit__` protocol
`contextlib.contextmanager` for generator-based context managers

JS Analogy:
Decorators are like Higher-Order Functions (HOFs) or Express middleware in JS. JS has proposed decorators for classes.
Context managers map to the `try/finally` pattern for cleanup (like closing a file or DB connection), or the new JS `using` keyword (explicit resource management).

2. UNDER THE HOOD (CPython & Memory)
A decorator `@foo` above `def bar():` is simply syntactic sugar for `bar = foo(bar)`.
A context manager `with foo() as x:` evaluates `foo()`, calls its `__enter__` method and assigns the result to `x`. On block exit (normal or exception), `__exit__` is called.

3. COMMON GOTCHA
Forgetting `@functools.wraps(func)` inside your decorator. Without it, the wrapped function loses its original `__name__` and `__doc__` and becomes the wrapper function's name. This breaks debugging and introspection.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "How do decorators work in Python? Write a decorator that logs function calls with timing."
A: "A decorator is a higher-order function that takes a function as input, extends or modifies its behavior, and returns a new wrapper function. We use the @ syntax to apply them. 
Under the hood, @decorator is just syntactic sugar for func = decorator(func). When writing one, it's critical to use @functools.wraps on the inner wrapper function to preserve the original function's name and docstring.
(See code for timing decorator)."

5. Self-tests
See run_tests()
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import time
import functools
from contextlib import contextmanager

def demonstrate_basic_decorator():
    print("--- Basic Decorator ---")
    def my_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print("Before call")
            result = func(*args, **kwargs)
            print("After call")
            return result
        return wrapper

    @my_decorator
    def say_hello(name):
        print(f"Hello, {name}")
        return "done"
        
    say_hello("World")
    print(f"Function name preserved: {say_hello.__name__}")

def demonstrate_timing_decorator():
    print("\n--- Timing Decorator ---")
    def timer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"{func.__name__} took {end - start:.6f}s")
            return result
        return wrapper
        
    @timer
    def slow_function():
        time.sleep(0.1)
        
    slow_function()

def demonstrate_parameterized_decorator():
    print("\n--- Parameterized Decorator ---")
    def repeat(times):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for _ in range(times):
                    result = func(*args, **kwargs)
                return result
            return wrapper
        return decorator
        
    @repeat(times=3)
    def say_hi():
        print("Hi!")
        
    say_hi()

def demonstrate_context_manager():
    print("\n--- Context Manager (Class) ---")
    class FileManager:
        def __init__(self, name):
            self.name = name
            
        def __enter__(self):
            print(f"Opening {self.name}")
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            print(f"Closing {self.name}")
            if exc_type:
                print(f"Exception caught: {exc_val}")
            return True # Suppresses exception
            
    with FileManager("test.txt") as f:
        print("Inside with block")
        raise ValueError("Boom!")

def demonstrate_contextlib():
    print("\n--- contextlib.contextmanager ---")
    @contextmanager
    def file_manager_gen(name):
        print(f"Opening {name}")
        try:
            yield {"name": name}
        finally:
            print(f"Closing {name}")
            
    with file_manager_gen("test2.txt") as f:
        print(f"Working with {f['name']}")

def run_tests():
    # Test decorator metadata
    def dummy_dec(f):
        @functools.wraps(f)
        def wrapper(*args): return f(*args)
        return wrapper
        
    @dummy_dec
    def doc_func():
        """I have a doc"""
        pass
        
    assert doc_func.__name__ == "doc_func"
    assert doc_func.__doc__ == "I have a doc"
    
    # Test Context manager exception suppression
    class Suppressor:
        def __enter__(self): return self
        def __exit__(self, *args): return True
        
    with Suppressor():
        raise Exception("Should be suppressed")
        
    print("\nAll decorator tests passed!")

if __name__ == '__main__':
    demonstrate_basic_decorator()
    demonstrate_timing_decorator()
    demonstrate_parameterized_decorator()
    demonstrate_context_manager()
    demonstrate_contextlib()
    run_tests()
