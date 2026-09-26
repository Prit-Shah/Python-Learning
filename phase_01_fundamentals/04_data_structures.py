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

    # ============================================================
    # 1. LIST
    # ============================================================
    # List:
    # - Ordered
    # - Mutable (can be changed)
    # - Allows duplicate values
    # - Allows different data types
    # - Uses []


    # Creating a list
    lst = [1, 2, 3]

    # Accessing elements
    assert lst[0] == 1
    assert lst[1] == 2
    assert lst[-1] == 3

    # Slicing
    assert lst[0:2] == [1, 2]
    assert lst[:2] == [1, 2]
    assert lst[1:] == [2, 3]
    assert lst[::-1] == [3, 2, 1]


    # ------------------------------------------------------------
    # append()
    # Adds ONE item at the end
    # ------------------------------------------------------------

    lst.append(4)

    assert lst == [1, 2, 3, 4]


    # ------------------------------------------------------------
    # extend()
    # Adds multiple items
    # ------------------------------------------------------------

    lst.extend([5, 6])

    assert lst == [1, 2, 3, 4, 5, 6]

    # append vs extend
    a = [1, 2]

    a.append([3, 4])
    assert a == [1, 2, [3, 4]]

    b = [1, 2]

    b.extend([3, 4])
    assert b == [1, 2, 3, 4]


    # ------------------------------------------------------------
    # insert()
    # Inserts an item at a specific index
    # ------------------------------------------------------------

    lst.insert(0, 100)

    assert lst[0] == 100
    assert lst == [100, 1, 2, 3, 4, 5, 6]


    # ------------------------------------------------------------
    # remove()
    # Removes the FIRST matching value
    # ------------------------------------------------------------

    numbers = [1, 2, 3, 2, 4]

    numbers.remove(2)

    assert numbers == [1, 3, 2, 4]


    # ------------------------------------------------------------
    # pop()
    # Removes and RETURNS an item
    # ------------------------------------------------------------

    numbers = [10, 20, 30]

    value = numbers.pop()

    assert value == 30
    assert numbers == [10, 20]

    # pop(index)
    value = numbers.pop(0)

    assert value == 10
    assert numbers == [20]


    # ------------------------------------------------------------
    # clear()
    # Removes everything
    # ------------------------------------------------------------

    numbers = [1, 2, 3]

    numbers.clear()

    assert numbers == []


    # ------------------------------------------------------------
    # index()
    # Finds the index of the first matching value
    # ------------------------------------------------------------

    numbers = [10, 20, 30, 20]

    assert numbers.index(20) == 1


    # ------------------------------------------------------------
    # count()
    # Counts how many times a value appears
    # ------------------------------------------------------------

    numbers = [1, 2, 2, 2, 3]

    assert numbers.count(2) == 3


    # ------------------------------------------------------------
    # sort()
    # Sorts the ORIGINAL list
    # ------------------------------------------------------------

    numbers = [5, 2, 8, 1, 3]

    numbers.sort()

    assert numbers == [1, 2, 3, 5, 8]

    # Reverse sorting
    numbers.sort(reverse=True)

    assert numbers == [8, 5, 3, 2, 1]


    # ------------------------------------------------------------
    # reverse()
    # Reverses the ORIGINAL list
    # ------------------------------------------------------------

    numbers = [1, 2, 3]

    numbers.reverse()

    assert numbers == [3, 2, 1]


    # ------------------------------------------------------------
    # sorted()
    # Creates a NEW sorted list
    # ------------------------------------------------------------

    numbers = [5, 1, 3, 2]

    result = sorted(numbers)

    assert result == [1, 2, 3, 5]

    # Original list is unchanged
    assert numbers == [5, 1, 3, 2]


    # ------------------------------------------------------------
    # in / not in
    # ------------------------------------------------------------

    numbers = [10, 20, 30]

    assert 20 in numbers
    assert 50 not in numbers


    # ------------------------------------------------------------
    # len()
    # ------------------------------------------------------------

    assert len(numbers) == 3


    # ------------------------------------------------------------
    # List unpacking
    # ------------------------------------------------------------

    numbers = [10, 20, 30]

    a, b, c = numbers

    assert a == 10
    assert b == 20
    assert c == 30


    # ============================================================
    # 2. TUPLE
    # ============================================================
    # Tuple:
    # - Ordered
    # - Immutable (cannot be changed)
    # - Allows duplicates
    # - Uses ()
    

    tup = (1, 2, 3)

    # Accessing elements
    assert tup[0] == 1
    assert tup[-1] == 3

    # Slicing
    assert tup[0:2] == (1, 2)


    # ------------------------------------------------------------
    # Tuple cannot be modified
    # ------------------------------------------------------------

    try:
        tup[0] = 100

        # This should never execute
        assert False, "Should raise TypeError"

    except TypeError:
        pass


    # ------------------------------------------------------------
    # count()
    # ------------------------------------------------------------

    tup = (1, 2, 2, 3, 2)

    assert tup.count(2) == 3


    # ------------------------------------------------------------
    # index()
    # ------------------------------------------------------------

    tup = (10, 20, 30, 20)

    assert tup.index(20) == 1


    # ------------------------------------------------------------
    # in / not in
    # ------------------------------------------------------------

    assert 20 in tup
    assert 50 not in tup


    # ------------------------------------------------------------
    # len()
    # ------------------------------------------------------------

    assert len(tup) == 4


    # ------------------------------------------------------------
    # Tuple unpacking
    # ------------------------------------------------------------

    person = ("Prit", 25)

    name, age = person

    assert name == "Prit"
    assert age == 25


    # ------------------------------------------------------------
    # Single-item tuple
    # IMPORTANT
    # ------------------------------------------------------------

    single = (10,)

    assert type(single) == tuple

    # Without comma, this is just an integer
    not_tuple = (10,)

    assert isinstance(not_tuple, tuple)


    # ============================================================
    # 3. SET
    # ============================================================
    # Set:
    # - Unordered
    # - Mutable
    # - Does NOT allow duplicates
    # - Uses {}
    # - Very useful for unique values and set operations


    # Duplicate values are automatically removed

    s = {1, 2, 2, 3}

    assert len(s) == 3
    assert 2 in s


    # ------------------------------------------------------------
    # add()
    # Adds ONE item
    # ------------------------------------------------------------

    s = {1, 2, 3}

    s.add(4)

    assert 4 in s


    # ------------------------------------------------------------
    # update()
    # Adds multiple items
    # ------------------------------------------------------------

    s.update([5, 6, 7])

    assert 5 in s
    assert 6 in s
    assert 7 in s


    # ------------------------------------------------------------
    # remove()
    # Removes an item
    # Raises KeyError if item doesn't exist
    # ------------------------------------------------------------

    s = {1, 2, 3}

    s.remove(2)

    assert 2 not in s


    # ------------------------------------------------------------
    # discard()
    # Removes an item
    # Does NOT raise an error if item doesn't exist
    # ------------------------------------------------------------

    s = {1, 2, 3}

    s.discard(2)
    s.discard(100)  # No error

    assert 2 not in s


    # ------------------------------------------------------------
    # pop()
    # Removes and returns an arbitrary item
    # ------------------------------------------------------------

    s = {10, 20, 30}

    value = s.pop()

    assert value in {10, 20, 30}


    # ------------------------------------------------------------
    # clear()
    # ------------------------------------------------------------

    s = {1, 2, 3}

    s.clear()

    assert len(s) == 0


    # ------------------------------------------------------------
    # UNION
    # Combines both sets
    # ------------------------------------------------------------

    a = {1, 2, 3}
    b = {3, 4, 5}

    result = a.union(b)

    assert result == {1, 2, 3, 4, 5}

    # Another syntax
    assert a | b == {1, 2, 3, 4, 5}


    # ------------------------------------------------------------
    # INTERSECTION
    # Finds common elements
    # ------------------------------------------------------------

    result = a.intersection(b)

    assert result == {3}

    # Another syntax
    assert a & b == {3}


    # ------------------------------------------------------------
    # DIFFERENCE
    # Elements in a but NOT in b
    # ------------------------------------------------------------

    result = a.difference(b)

    assert result == {1, 2}

    # Another syntax
    assert a - b == {1, 2}


    # ------------------------------------------------------------
    # SYMMETRIC DIFFERENCE
    # Elements that are NOT common
    # ------------------------------------------------------------

    result = a.symmetric_difference(b)

    assert result == {1, 2, 4, 5}

    # Another syntax
    assert a ^ b == {1, 2, 4, 5}


    # ------------------------------------------------------------
    # issubset()
    # ------------------------------------------------------------

    small = {1, 2}
    large = {1, 2, 3, 4}

    assert small.issubset(large)


    # ------------------------------------------------------------
    # issuperset()
    # ------------------------------------------------------------

    assert large.issuperset(small)


    # ------------------------------------------------------------
    # isdisjoint()
    # Checks whether two sets have NO common values
    # ------------------------------------------------------------

    a = {1, 2}
    b = {3, 4}

    assert a.isdisjoint(b)


    # ============================================================
    # 4. DICTIONARY
    # ============================================================
    # Dictionary:
    # - Stores key-value pairs
    # - Mutable
    # - Keys must be unique
    # - Uses {}
    #
    # Example:
    #
    # {
    #     "name": "Prit",
    #     "age": 25
    # }


    # Creating dictionary

    d = {
        "name": "Prit",
        "age": 25
    }


    # ------------------------------------------------------------
    # Accessing values
    # ------------------------------------------------------------

    assert d["name"] == "Prit"
    assert d["age"] == 25


    # ------------------------------------------------------------
    # Adding a new key
    # ------------------------------------------------------------

    d["city"] = "Surat"

    assert d["city"] == "Surat"


    # ------------------------------------------------------------
    # Updating an existing key
    # ------------------------------------------------------------

    d["age"] = 26

    assert d["age"] == 26


    # ------------------------------------------------------------
    # get()
    #
    # Safer way to access a key
    # ------------------------------------------------------------

    d = {"a": 1}

    assert d.get("a") == 1

    # Missing key returns None
    assert d.get("xyz") is None

    # You can provide a default value
    assert d.get("xyz", 0) == 0


    # ------------------------------------------------------------
    # keys()
    # ------------------------------------------------------------

    d = {
        "name": "Prit",
        "age": 25
    }

    assert list(d.keys()) == ["name", "age"]


    # ------------------------------------------------------------
    # values()
    # ------------------------------------------------------------

    assert list(d.values()) == ["Prit", 25]


    # ------------------------------------------------------------
    # items()
    # ------------------------------------------------------------

    assert list(d.items()) == [
        ("name", "Prit"),
        ("age", 25)
    ]


    # ------------------------------------------------------------
    # in
    # IMPORTANT:
    # "in" checks KEYS, not values
    # ------------------------------------------------------------

    assert "name" in d
    assert "Prit" not in d


    # To check values:

    assert "Prit" in d.values()


    # ------------------------------------------------------------
    # pop()
    # Removes a key and returns its value
    # ------------------------------------------------------------

    d = {
        "a": 1,
        "b": 2
    }

    value = d.pop("a")

    assert value == 1
    assert "a" not in d


    # ------------------------------------------------------------
    # popitem()
    # Removes and returns the last key-value pair
    # ------------------------------------------------------------

    d = {
        "a": 1,
        "b": 2
    }

    key, value = d.popitem()

    assert key == "b"
    assert value == 2


    # ------------------------------------------------------------
    # update()
    # Adds/updates multiple key-value pairs
    # ------------------------------------------------------------

    d = {
        "name": "Prit"
    }

    d.update({
        "age": 25,
        "city": "Surat"
    })

    assert d["age"] == 25
    assert d["city"] == "Surat"


    # ------------------------------------------------------------
    # setdefault()
    #
    # If key exists -> returns existing value
    # If key doesn't exist -> creates it
    # ------------------------------------------------------------

    d = {
        "name": "Prit"
    }

    value = d.setdefault("name", "John")

    assert value == "Prit"

    # "name" remains Prit
    assert d["name"] == "Prit"


    value = d.setdefault("city", "Surat")

    assert value == "Surat"
    assert d["city"] == "Surat"


    # ------------------------------------------------------------
    # copy()
    # Creates a shallow copy
    # ------------------------------------------------------------

    original = {
        "a": 1,
        "b": 2
    }

    copied = original.copy()

    copied["a"] = 100

    assert original["a"] == 1
    assert copied["a"] == 100


    # ------------------------------------------------------------
    # clear()
    # ------------------------------------------------------------

    d = {
        "a": 1,
        "b": 2
    }

    d.clear()

    assert d == {}


    # ------------------------------------------------------------
    # len()
    # ------------------------------------------------------------

    d = {
        "a": 1,
        "b": 2
    }

    assert len(d) == 2


    # ============================================================
    # 5. QUICK COMPARISON
    # ============================================================

    # LIST
    # Ordered
    # Mutable
    # Duplicates allowed
    # [1, 2, 2, 3]

    # TUPLE
    # Ordered
    # Immutable
    # Duplicates allowed
    # (1, 2, 2, 3)

    # SET
    # Unordered
    # Mutable
    # Duplicates NOT allowed
    # {1, 2, 3}

    # DICT
    # Key-value pairs
    # Mutable
    # Keys must be unique
    # {"name": "Prit", "age": 25}


# ================================================================
# MAIN
# ================================================================

if __name__ == '__main__':
    run_tests()
    print("04_data_structures.py tests passed!")
