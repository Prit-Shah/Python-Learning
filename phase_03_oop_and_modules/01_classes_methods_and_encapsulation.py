"""
Phase 3: OOP & Real Application Code - Classes, Methods & Encapsulation
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Python classes use explicit 'self' to reference the instance (unlike implicit 'this' in JS).
   - Three method types:
     * Instance methods: Receive 'self' (the object instance).
     * Class methods (@classmethod): Receive 'cls' (the class object); ideal for alternative constructors/factories.
     * Static methods (@staticmethod): Receive neither 'self' nor 'cls'; plain utility functions namespaced in the class.
   - Encapsulation: Python has NO true private keyword!
     * Public: 'name'
     * Protected (convention): '_name' (signals internal use, still accessible)
     * Private (name mangling): '__name' (mangled to '_ClassName__name' to prevent accidental overrides)
   - Properties: '@property' and '@<field>.setter' provide getter/setter encapsulation without changing call-site syntax (obj.field).

2. UNDER THE HOOD (CPython & Memory):
   - Classes and instances have their own '__dict__' attribute storing their namespaces.
   - When calling 'obj.method()', Python converts it to 'Class.method(obj)'.
   - Class variables are shared across ALL instances via the class '__dict__'.
   - Modifying a mutable class variable (e.g. Class.items.append()) affects every instance!

3. COMMON GOTCHA:
   - Defining a mutable attribute at class level instead of inside '__init__':
     class User:
         roles = [] # BUG: Shared by all User instances!
     def __init__(self):
         self.roles = [] # CORRECT: Unique to this instance.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Python handle encapsulation, and what is the difference between
       @classmethod, @staticmethod, and an instance method?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Encapsulation in Python:
      "Unlike Java or TypeScript, Python does not enforce access modifiers at runtime.
       Instead, it follows the 'we are all consenting adults here' philosophy:
       - A single leading underscore (_field) is a convention indicating internal API.
       - A double leading underscore (__field) triggers name mangling, transforming it
         to _ClassName__field to avoid collision in subclasses, not for security.
       - For clean data validation, we use @property and @prop.setter to wrap attributes."
   2. The Three Method Types:
      "Instance methods take 'self' as the first parameter to access and mutate instance state.
       Class methods take '@classmethod' and receive 'cls' (the class itself), which makes
       them the standard Pythonic pattern for alternative factory constructors (e.g. from_dict, from_json).
       Static methods take '@staticmethod' and receive neither self nor cls; they are simply
       pure functions placed inside the class namespace for logical grouping."
================================================================================
"""

import sys

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class BankAccount:
    """Demonstrates instance/class/static methods, encapsulation, and properties."""
    
    # Class variable: shared across all instances
    BANK_NAME = "Pythonic Federal Bank"
    _interest_rate: float = 0.05
    _total_accounts: int = 0

    def __init__(self, owner: str, initial_balance: float = 0.0):
        # Instance variables: unique to each instance
        self.owner = owner
        self._balance = max(0.0, float(initial_balance))
        self.__account_id = f"ACC-{BankAccount._total_accounts + 1:04d}"
        BankAccount._total_accounts += 1

    # Property: Getter
    @property
    def balance(self) -> float:
        """Read-only access to balance via property decorator."""
        return self._balance

    # Property: Setter with business logic validation
    @balance.setter
    def balance(self, value: float) -> None:
        if value < 0:
            raise ValueError("Balance cannot be set to a negative number.")
        self._balance = value

    @property
    def account_id(self) -> str:
        """Expose mangled private ID cleanly."""
        return self.__account_id

    # 1. Instance Method
    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self._balance += amount
        return self._balance

    # 2. Class Method: Alternative Constructor / Factory
    @classmethod
    def from_dict(cls, data: dict) -> "BankAccount":
        """Factory constructor creating an account from a dictionary."""
        owner = data.get("owner", "Anonymous")
        balance = data.get("balance", 0.0)
        return cls(owner=owner, initial_balance=balance)

    @classmethod
    def get_total_accounts(cls) -> int:
        return cls._total_accounts

    # 3. Static Method: Pure utility function without self or cls dependency
    @staticmethod
    def is_valid_currency_code(code: str) -> bool:
        """Utility check unrelated to instance state."""
        return code.upper() in {"USD", "EUR", "GBP", "INR", "CAD"}


def demonstrate_oop_basics():
    print("\n--- 1. Instance, Class, and Static Methods ---")
    acc1 = BankAccount("Alice", 1000.0)
    acc2 = BankAccount.from_dict({"owner": "Bob", "balance": 500.0})
    
    print(f"  Account 1: {acc1.owner}, Balance: ${acc1.balance:.2f}, ID: {acc1.account_id}")
    print(f"  Account 2: {acc2.owner}, Balance: ${acc2.balance:.2f}, ID: {acc2.account_id}")
    print(f"  Total Accounts created (Class Method): {BankAccount.get_total_accounts()}")
    print(f"  Is 'USD' valid currency (Static Method)? {BankAccount.is_valid_currency_code('USD')}")


def demonstrate_encapsulation_and_properties():
    print("\n--- 2. Encapsulation & Name Mangling ---")
    acc = BankAccount("Charlie", 250.0)
    
    # Access via property
    print(f"  Initial balance via @property: ${acc.balance}")
    acc.balance = 300.0
    print(f"  Updated balance via @balance.setter: ${acc.balance}")
    
    # Name mangling verification:
    # Direct access acc.__account_id raises AttributeError
    try:
        _ = acc.__account_id
    except AttributeError:
        print("  acc.__account_id raised AttributeError as expected (Name Mangling active)")
    
    # The attribute actually exists under the mangled name:
    mangled_val = getattr(acc, "_BankAccount__account_id")
    print(f"  Mangled attribute accessible via '_BankAccount__account_id': {mangled_val}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

class Temperature:
    """
    Challenge:
    Implement a Temperature class that:
    1. Stores temperature internally in Celsius (_celsius).
    2. Has a @property 'celsius' with a setter that validates temperature cannot be below absolute zero (-273.15 C).
    3. Has a @property 'fahrenheit' that converts to/from Fahrenheit: F = C * 9/5 + 32.
    4. Has a @classmethod 'from_fahrenheit(f_val)' that returns a Temperature instance.
    """
    def __init__(self, celsius: float = 0.0):
        self.celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Temperature below absolute zero is impossible!")
        self._celsius = float(value)

    @property
    def fahrenheit(self) -> float:
        return (self._celsius * 9 / 5) + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        c_val = (value - 32) * 5 / 9
        self.celsius = c_val

    @classmethod
    def from_fahrenheit(cls, f_val: float) -> "Temperature":
        return cls((f_val - 32) * 5 / 9)


def run_tests():
    print("\n[*] Running automated self-tests for 01_classes_methods_and_encapsulation.py...")
    t = Temperature(100.0)
    assert t.celsius == 100.0, "Celsius getter failed"
    assert t.fahrenheit == 212.0, "Fahrenheit conversion failed"
    
    t.fahrenheit = 32.0
    assert abs(t.celsius - 0.0) < 1e-6, "Fahrenheit setter failed"
    
    t2 = Temperature.from_fahrenheit(98.6)
    assert abs(t2.celsius - 37.0) < 1e-2, "Factory constructor from_fahrenheit failed"
    
    try:
        t.celsius = -300.0
        assert False, "Should raise ValueError for temperature below absolute zero"
    except ValueError:
        pass
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 3 - Classes, Methods & Encapsulation")
    print("=" * 65)
    demonstrate_oop_basics()
    demonstrate_encapsulation_and_properties()
    print("-" * 65)
    run_tests()
    print("=" * 65)
