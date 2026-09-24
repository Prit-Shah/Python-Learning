"""
Phase 3: OOP & Real Application Code - Inheritance, Composition & ABCs
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Inheritance: 'class Child(Parent):', invoking 'super().__init__()'.
   - Multiple Inheritance: Python supports inheriting from multiple base classes!
   - Method Resolution Order (MRO): Python uses the C3 Linearization algorithm to determine method lookup order.
   - Composition Over Inheritance: Prefer "has-a" (injecting components) over "is-a" (deep subclass trees).
   - Abstract Base Classes (ABCs):
     * Created using 'from abc import ABC, abstractmethod'.
     * Classes inheriting from ABC with '@abstractmethod' CANNOT be instantiated until all abstract methods are implemented.
   - JS/TS Analogy:
     * In TypeScript, you use 'abstract class' and 'implements'. In Python, you inherit from 'ABC'.
     * TypeScript does not support multiple implementation inheritance; Python does (and relies on MRO).

2. UNDER THE HOOD (CPython & Memory):
   - MRO is inspectable via 'Class.__mro__' or 'Class.mro()'.
   - When calling 'super().method()', CPython searches the MRO starting at the class immediately following the current one.
   - ABC instantiation checks occur in CPython's 'type.__call__' during instance creation.

3. COMMON GOTCHA:
   - Forgetting to call 'super().__init__()' in a derived class, leaving parent attributes uninitialized.
   - Instantiating an ABC directly raises 'TypeError: Can't instantiate abstract class with abstract methods'.

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Python handle multiple inheritance, what is MRO, and when should you
       use an Abstract Base Class (ABC) vs typing.Protocol?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Multiple Inheritance & MRO:
      "Python supports multiple inheritance and resolves method name collisions using
       Method Resolution Order (MRO) based on the C3 Linearization algorithm.
       You can inspect any class hierarchy with Class.mro(). When using super(), Python
       does not simply call the immediate parent; it walks the MRO cooperatively."
   2. ABC vs Protocol (Static Duck Typing):
      "Both define interfaces, but they enforce them differently:
       - Use an Abstract Base Class (ABC) when you want nominal subtyping and runtime enforcement.
         If a subclass forgets an @abstractmethod, Python throws an error at instantiation time.
         ABCs can also provide default template method implementations.
       - Use typing.Protocol (PEP 544) when you want structural subtyping (static duck typing).
         Subclasses don't need to inherit from the Protocol explicitly; static type checkers (mypy)
         verify compliance purely by signature matching. In modern Python AI/backend systems,
         Protocols are preferred for loose coupling."
================================================================================
"""

import sys
from abc import ABC, abstractmethod

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# 1. ABSTRACT BASE CLASS (INTERFACE SPECIFICATION)
# ==============================================================================

class MessageNotifier(ABC):
    """Abstract Base Class defining a contract for notification services."""

    @abstractmethod
    def send_notification(self, recipient: str, message: str) -> bool:
        """Must be implemented by all concrete subclasses."""
        pass

    # Template method with default implementation
    def format_message(self, message: str) -> str:
        return f"[ALERT] {message.strip()}"


class EmailNotifier(MessageNotifier):
    """Concrete implementation of MessageNotifier."""
    
    def __init__(self, smtp_server: str):
        self.smtp_server = smtp_server

    def send_notification(self, recipient: str, message: str) -> bool:
        formatted = self.format_message(message)
        print(f"  [Email via {self.smtp_server}] To: {recipient} -> {formatted}")
        return True


class SlackNotifier(MessageNotifier):
    """Concrete implementation for Slack webhooks."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_notification(self, recipient: str, message: str) -> bool:
        formatted = self.format_message(message)
        print(f"  [Slack Webhook {self.webhook_url[:15]}...] Channel: {recipient} -> {formatted}")
        return True


# ==============================================================================
# 2. COMPOSITION OVER INHERITANCE
# ==============================================================================

class UserService:
    """
    Demonstrates Composition:
    UserService 'has-a' MessageNotifier injected into it.
    Decoupled from email or Slack implementations!
    """
    def __init__(self, notifier: MessageNotifier):
        self.notifier = notifier

    def register_user(self, email: str, username: str) -> bool:
        print(f"  Registering user '{username}' ({email})...")
        # Delegate message delivery to the injected component
        return self.notifier.send_notification(email, f"Welcome to the platform, {username}!")


# ==============================================================================
# 3. MULTIPLE INHERITANCE & MRO DEMO
# ==============================================================================

class Loggable:
    def log(self, msg: str):
        return f"Log: {msg}"

class Serializable:
    def serialize(self):
        return str(self.__dict__)

class AuditedRecord(Loggable, Serializable):
    def __init__(self, record_id: int):
        self.record_id = record_id


def demonstrate_abcs_and_composition():
    print("\n--- 1. Abstract Base Classes & Composition ---")
    email_notifier = EmailNotifier("smtp.company.com")
    slack_notifier = SlackNotifier("https://hooks.slack.com/services/XYZ")
    
    # Injected dependencies:
    service1 = UserService(email_notifier)
    service1.register_user("alice@corp.com", "Alice")
    
    service2 = UserService(slack_notifier)
    service2.register_user("#dev-alerts", "Bob")


def demonstrate_mro():
    print("\n--- 2. Method Resolution Order (MRO) ---")
    record = AuditedRecord(42)
    print(f"  Loggable method: {record.log('Created record')}")
    print(f"  Serializable method: {record.serialize()}")
    print("  MRO Chain:")
    for idx, cls in enumerate(AuditedRecord.mro()):
        print(f"    {idx}: {cls.__name__}")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> str:
        pass


class StripeProcessor(PaymentProcessor):
    def process_payment(self, amount: float) -> str:
        return f"STRIPE_PAID_${amount:.2f}"


class PayPalProcessor(PaymentProcessor):
    def process_payment(self, amount: float) -> str:
        return f"PAYPAL_PAID_${amount:.2f}"


class OrderCheckout:
    def __init__(self, processor: PaymentProcessor):
        self.processor = processor

    def checkout(self, total: float) -> str:
        return self.processor.process_payment(total)


def run_tests():
    print("\n[*] Running automated self-tests for 03_inheritance_composition_and_abcs.py...")
    
    # 1. ABC prevention test
    try:
        PaymentProcessor()
        assert False, "Cannot instantiate abstract class"
    except TypeError:
        pass
    
    # 2. Polymorphic processors test
    stripe_checkout = OrderCheckout(StripeProcessor())
    paypal_checkout = OrderCheckout(PayPalProcessor())
    
    assert stripe_checkout.checkout(99.99) == "STRIPE_PAID_$99.99"
    assert paypal_checkout.checkout(49.50) == "PAYPAL_PAID_$49.50"
    
    # 3. MRO check
    mro_names = [c.__name__ for c in AuditedRecord.mro()]
    assert mro_names == ["AuditedRecord", "Loggable", "Serializable", "object"]
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 3 - Inheritance, Composition & ABCs")
    print("=" * 65)
    demonstrate_abcs_and_composition()
    demonstrate_mro()
    print("-" * 65)
    run_tests()
    print("=" * 65)
