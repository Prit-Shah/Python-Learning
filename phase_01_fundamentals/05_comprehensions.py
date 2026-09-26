"""
05_comprehensions.py

============================================================
1. CONCEPT
============================================================

Comprehensions provide a concise way to create:

    - Lists
    - Sets
    - Dictionaries

from an iterable.

Basic list comprehension:

    [expression for item in iterable]

With a condition:

    [expression for item in iterable if condition]


============================================================
2. JS / TS ANALOGY
============================================================

Python:

    [x * 2 for x in numbers]

JavaScript:

    numbers.map(x => x * 2)


Python:

    [x for x in numbers if x > 10]

JavaScript:

    numbers.filter(x => x > 10)


Python can combine both:

    [x * 2 for x in numbers if x > 10]

JavaScript:

    numbers
        .filter(x => x > 10)
        .map(x => x * 2)


============================================================
3. UNDER THE HOOD
============================================================

A comprehension is still performing iteration.

For example:

    squares = [x ** 2 for x in range(5)]

is conceptually similar to:

    squares = []

    for x in range(5):
        squares.append(x ** 2)

List comprehensions are often faster than an equivalent
Python loop using append(), but readability should be the
main reason to use them.


============================================================
4. COMMON GOTCHAS
============================================================

Avoid comprehensions when:

1. The logic becomes too complicated.
2. There are too many nested conditions.
3. You are using them only for side effects.
4. A normal for-loop is much easier to understand.

Bad:

    [print(x) for x in numbers]

Better:

    for x in numbers:
        print(x)


============================================================
5. INTERVIEW RESPONSE
============================================================

Q: What are comprehensions and when should you NOT use them?

Answer:

"Comprehensions are a concise way to create lists, sets,
or dictionaries by iterating over an iterable and optionally
filtering or transforming its elements. They are useful when
the logic is simple and readable. I would avoid them when the
logic becomes complex, when there are many nested conditions,
or when the operation is being used only for side effects.
In those cases, a normal for-loop is easier to understand."


============================================================
"""

import sys


# ------------------------------------------------------------
# Make terminal output UTF-8 when possible
# ------------------------------------------------------------

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_tests():

    # ============================================================
    # 1. BASIC LIST COMPREHENSION
    # ============================================================

    # Normal for-loop:

    numbers = [1, 2, 3, 4, 5]

    result = []

    for number in numbers:
        result.append(number)

    assert result == [1, 2, 3, 4, 5]


    # Same thing using comprehension:

    result = [number for number in numbers]

    assert result == [1, 2, 3, 4, 5]


    # General syntax:
    #
    # [expression for item in iterable]
    #
    # expression -> what we want to put in the new list
    # item       -> current item
    # iterable   -> collection we are looping over


    # ============================================================
    # 2. TRANSFORMING VALUES
    # ============================================================

    numbers = [1, 2, 3, 4, 5]

    squares = [x ** 2 for x in numbers]

    assert squares == [1, 4, 9, 16, 25]


    # Double every number

    doubled = [x * 2 for x in numbers]

    assert doubled == [2, 4, 6, 8, 10]


    # Convert strings to uppercase

    names = ["prit", "rahul", "amit"]

    upper_names = [name.upper() for name in names]

    assert upper_names == ["PRIT", "RAHUL", "AMIT"]


    # ============================================================
    # 3. FILTERING WITH IF
    # ============================================================

    numbers = [1, 2, 3, 4, 5, 6]

    # Only even numbers

    evens = [x for x in numbers if x % 2 == 0]

    assert evens == [2, 4, 6]


    # Only odd numbers

    odds = [x for x in numbers if x % 2 != 0]

    assert odds == [1, 3, 5]


    # Numbers greater than 3

    greater_than_three = [x for x in numbers if x > 3]

    assert greater_than_three == [4, 5, 6]


    # ============================================================
    # 4. TRANSFORM + FILTER
    # ============================================================

    numbers = [1, 2, 3, 4, 5, 6]

    # Take even numbers and square them

    even_squares = [
        x ** 2
        for x in numbers
        if x % 2 == 0
    ]

    assert even_squares == [4, 16, 36]


    # This is conceptually similar to JavaScript:
    #
    # numbers
    #     .filter(x => x % 2 === 0)
    #     .map(x => x ** 2)


    # ============================================================
    # 5. IF / ELSE INSIDE COMPREHENSION
    # ============================================================

    numbers = [1, 2, 3, 4, 5]

    labels = [
        "even" if x % 2 == 0 else "odd"
        for x in numbers
    ]

    assert labels == [
        "odd",
        "even",
        "odd",
        "even",
        "odd"
    ]


    # Important difference:
    #
    # Filtering:
    #
    # [x for x in numbers if x > 2]
    #
    # if/else transformation:
    #
    # ["big" if x > 2 else "small" for x in numbers]


    # ============================================================
    # 6. STRING COMPREHENSION
    # ============================================================

    text = "Python"

    characters = [char for char in text]

    assert characters == [
        "P",
        "y",
        "t",
        "h",
        "o",
        "n"
    ]


    # Get only vowels

    vowels = [
        char
        for char in text.lower()
        if char in "aeiou"
    ]

    assert vowels == ["o"]


    # ============================================================
    # 7. WORKING WITH range()
    # ============================================================

    numbers = [x for x in range(5)]

    assert numbers == [0, 1, 2, 3, 4]


    squares = [x ** 2 for x in range(5)]

    assert squares == [0, 1, 4, 9, 16]


    # Even numbers from 0 to 10

    evens = [
        x
        for x in range(11)
        if x % 2 == 0
    ]

    assert evens == [0, 2, 4, 6, 8, 10]


    # ============================================================
    # 8. LIST COMPREHENSION WITH FUNCTION
    # ============================================================

    def double(value):
        return value * 2


    numbers = [1, 2, 3]

    result = [double(x) for x in numbers]

    assert result == [2, 4, 6]


    # ============================================================
    # 9. NESTED LIST COMPREHENSION
    # ============================================================

    matrix = [
        [1, 2],
        [3, 4],
        [5, 6]
    ]


    # Normal nested loops:

    result = []

    for row in matrix:
        for value in row:
            result.append(value)

    assert result == [1, 2, 3, 4, 5, 6]


    # Nested comprehension:

    result = [
        value
        for row in matrix
        for value in row
    ]

    assert result == [1, 2, 3, 4, 5, 6]


    # Read this from left to right:
    #
    # for row in matrix
    #     for value in row
    #         value


    # ============================================================
    # 10. NESTED COMPREHENSION WITH CONDITION
    # ============================================================

    matrix = [
        [1, 2, 3],
        [4, 5, 6]
    ]

    even_values = [
        value
        for row in matrix
        for value in row
        if value % 2 == 0
    ]

    assert even_values == [2, 4, 6]


    # ============================================================
    # 11. DICTIONARY COMPREHENSION
    # ============================================================

    # Basic dictionary comprehension:

    numbers = [1, 2, 3]

    squares = {
        x: x ** 2
        for x in numbers
    }

    assert squares == {
        1: 1,
        2: 4,
        3: 9
    }


    # Syntax:
    #
    # {key_expression: value_expression for item in iterable}


    # ============================================================
    # 12. DICT COMPREHENSION WITH CONDITION
    # ============================================================

    numbers = range(1, 6)

    even_squares = {
        x: x ** 2
        for x in numbers
        if x % 2 == 0
    }

    assert even_squares == {
        2: 4,
        4: 16
    }


    # ============================================================
    # 13. DICT FROM TWO LISTS
    # ============================================================

    names = ["Prit", "Rahul", "Amit"]
    ages = [25, 30, 28]


    # zip() combines corresponding values

    people = {
        name: age
        for name, age in zip(names, ages)
    }

    assert people == {
        "Prit": 25,
        "Rahul": 30,
        "Amit": 28
    }


    # ============================================================
    # 14. SET COMPREHENSION
    # ============================================================

    numbers = [1, 2, 2, 3, 3, 4]

    unique_numbers = {
        x
        for x in numbers
    }

    assert unique_numbers == {
        1, 2, 3, 4
    }


    # Notice that duplicates disappear because this is a SET.


    # ============================================================
    # 15. SET COMPREHENSION WITH CONDITION
    # ============================================================

    numbers = range(1, 11)

    even_numbers = {
        x
        for x in numbers
        if x % 2 == 0
    }

    assert even_numbers == {
        2, 4, 6, 8, 10
    }


    # ============================================================
    # 16. CONVERTING BETWEEN COLLECTIONS
    # ============================================================

    numbers = [1, 2, 2, 3, 3, 4]

    # Remove duplicates:

    unique = {x for x in numbers}

    assert unique == {1, 2, 3, 4}


    # Convert back to list:

    unique_list = [
        x
        for x in unique
    ]

    assert set(unique_list) == {
        1, 2, 3, 4
    }


    # ============================================================
    # 17. CONDITIONAL TRANSFORMATION
    # ============================================================

    numbers = [1, 2, 3, 4, 5]

    result = [
        x * 10 if x % 2 == 0 else x
        for x in numbers
    ]

    assert result == [
        1,
        20,
        3,
        40,
        5
    ]


    # ============================================================
    # 18. REAL-LIFE EXAMPLE
    # ============================================================

    users = [
        {"name": "Prit", "active": True},
        {"name": "Rahul", "active": False},
        {"name": "Amit", "active": True},
        {"name": "Neha", "active": False}
    ]


    # Get names of active users:

    active_users = [
        user["name"]
        for user in users
        if user["active"]
    ]

    assert active_users == [
        "Prit",
        "Amit"
    ]


    # This is a very common real-world use case.


    # ============================================================
    # 19. REAL-LIFE EXAMPLE: FILTER + TRANSFORM
    # ============================================================

    products = [
        {"name": "Laptop", "price": 50000},
        {"name": "Mouse", "price": 1000},
        {"name": "Monitor", "price": 15000},
        {"name": "Keyboard", "price": 2000}
    ]


    # Get names of products costing more than 5000:

    expensive_products = [
        product["name"]
        for product in products
        if product["price"] > 5000
    ]

    assert expensive_products == [
        "Laptop",
        "Monitor"
    ]


    # ============================================================
    # 20. REAL-LIFE EXAMPLE: DICT COMPREHENSION
    # ============================================================

    products = [
        {"id": 1, "name": "Laptop"},
        {"id": 2, "name": "Mouse"},
        {"id": 3, "name": "Keyboard"}
    ]


    # Create an ID -> product name dictionary:

    product_map = {
        product["id"]: product["name"]
        for product in products
    }

    assert product_map == {
        1: "Laptop",
        2: "Mouse",
        3: "Keyboard"
    }


    # ============================================================
    # 21. AVOID SIDE EFFECTS
    # ============================================================

    numbers = [1, 2, 3]


    # DON'T do this:

    # [print(x) for x in numbers]


    # Why?

    # The purpose of a comprehension should normally be
    # creating a new collection.
    #
    # print() is being used for its side effect.
    #
    # Use a normal loop instead:

    for x in numbers:
        pass
        # print(x)


    # ============================================================
    # 22. WHEN A NORMAL LOOP IS BETTER
    # ============================================================

    numbers = [1, 2, 3, 4, 5]


    # This is technically possible:

    result = [
        x ** 2
        for x in numbers
        if x % 2 == 0
        if x > 2
    ]

    assert result == [16]


    # But when the logic becomes much more complicated,
    # a normal loop is usually easier to read:

    result = []

    for x in numbers:

        if x % 2 != 0:
            continue

        if x <= 2:
            continue

        result.append(x ** 2)

    assert result == [16]


    # ============================================================
    # 23. COMPREHENSION vs NORMAL LOOP
    # ============================================================

    numbers = [1, 2, 3, 4, 5]


    # Normal loop:

    squares = []

    for x in numbers:
        squares.append(x ** 2)


    # Comprehension:

    squares_2 = [
        x ** 2
        for x in numbers
    ]

    assert squares == squares_2


    # ============================================================
    # 24. IMPORTANT: COMPREHENSION CREATES A NEW COLLECTION
    # ============================================================

    numbers = [1, 2, 3]

    squares = [
        x ** 2
        for x in numbers
    ]

    assert numbers == [1, 2, 3]
    assert squares == [1, 4, 9]


    # Original list wasn't changed.


    # ============================================================
    # 25. EMPTY RESULT
    # ============================================================

    numbers = [1, 3, 5, 7]

    evens = [
        x
        for x in numbers
        if x % 2 == 0
    ]

    assert evens == []


    # A comprehension can legitimately return an empty collection.


# ================================================================
# MAIN
# ================================================================

if __name__ == '__main__':
    run_tests()
    print("05_comprehensions.py tests passed!")