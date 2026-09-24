"""
1. CONCEPT & JS/TS ANALOGY
Built-in data structures: lists (dynamic arrays), tuples (immutable sequences), sets (hash sets), dicts (hash maps).
JS/TS Analogy: Python List -> JS Array. Python Dict -> JS Object/Map. Python Set -> JS Set. Python Tuple -> no exact JS equivalent (Object.freeze arrays).

2. UNDER THE HOOD (CPython & Memory)
Lists are dynamic arrays of pointers. Dicts and Sets are implemented as hash tables. Dicts maintain insertion order (since 3.7) using a dense array of indices pointing to a sparse array of hashes. Lookups in dicts/sets are amortized O(1).

3. COMMON GOTCHA
Dict keys and Set elements must be hashable. You cannot use a list or a dict as a dictionary key, but you can use a tuple.

4. INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
Q: "When would you use a tuple vs a list vs a set?"
Script: "Use a list when you have a sequence of homogenous items that might change in size or value. Use a tuple for heterogenous data or when the sequence must remain immutable, which also allows it to be used as a dictionary key. Use a set when you need to store unique items and want O(1) membership testing, or need mathematical set operations like intersection or union."

5. Self-tests with assert statements
"""
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def run_tests():
    # List
    lst = [1, 2, 3]
    lst.append(4)
    assert lst == [1, 2, 3, 4]

    # Tuple
    tup = (1, 2)
    try:
        tup[0] = 3
        assert False, "Should raise TypeError"
    except TypeError:
        pass

    # Set
    s = {1, 2, 2, 3}
    assert len(s) == 3
    assert 2 in s

    # Dict
    d = {'a': 1}
    d['b'] = 2
    assert d.get('a') == 1
    assert 'b' in d

if __name__ == '__main__':
    run_tests()
    print("04_data_structures.py tests passed!")
