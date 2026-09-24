"""
1. CONCEPT & JS/TS ANALOGY
Functions in Python can have positional, keyword, default, *args (variable positional), and **kwargs (variable keyword) arguments.
JS/TS Analogy: `*args` and `**kwargs` are similar to JS's rest operator `...args`. Python `lambda` is like JS arrow functions `() => {}`, but strictly limited to a single expression.

2. UNDER THE HOOD (CPython & Memory)
Functions are first-class objects. Default arguments are evaluated ONLY ONCE when the function is defined, and stored in the function object's `__defaults__` or `__kwdefaults__` attributes.

3. COMMON GOTCHA
Mutable default arguments (like `def func(lst=[])`). Since the default is evaluated once, modifications to `lst` persist across function calls. Always use `None` and initialize inside.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "Explain *args and **kwargs and when you use them"
Script: "*args allows a function to accept any number of positional arguments, packing them into a tuple. **kwargs allows accepting any number of keyword arguments, packing them into a dictionary. They are highly useful for writing flexible APIs, wrapping other functions, decorators, or class inheritance via `super()` where you want to pass arguments forward without explicitly defining them all."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def sum_all(*args):
    return sum(args)

def config(**kwargs):
    return kwargs

def run_tests():
    assert sum_all(1, 2, 3) == 6
    assert sum_all() == 0
    
    cfg = config(host="localhost", port=8080)
    assert cfg["host"] == "localhost"
    assert cfg["port"] == 8080

    # Lambda test
    add = lambda x, y: x + y
    assert add(2, 3) == 5

if __name__ == '__main__':
    run_tests()
    print("06_functions_and_args.py tests passed!")
