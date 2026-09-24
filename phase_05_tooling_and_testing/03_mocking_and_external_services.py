"""
Phase 5: Professional Python Tooling - Mocking External Services (unittest.mock)
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Unit testing requires isolating code under test from external dependencies (HTTP APIs,
     databases, message queues, disk I/O, system time).
   - Python provides the built-in 'unittest.mock' module:
     * 'Mock': Flexible mock object that tracks calls, returns values, or raises exceptions.
     * 'MagicMock': Subclass of Mock that automatically implements all dunder methods (__len__, __iter__, etc.).
     * '@patch("module.target")': Decorator or context manager that temporarily replaces an attribute/function
       during test execution and automatically restores it when finished.
   - Golden Rule of Mocking:
     "Patch where an object is LOOKED UP, not where it is DEFINED!"
   - Code Coverage:
     * Statement coverage: Percentage of lines executed during tests.
     * Branch coverage: Percentage of conditional branches (if/else) evaluated in both directions.
     * Measured via 'pytest-cov' ('pytest --cov=my_pkg --cov-report=term-missing').
   - JS/TS Analogy:
     * 'jest.fn()' -> 'Mock()' / 'MagicMock()'
     * 'jest.spyOn(obj, "method")' -> '@patch.object(obj, "method")'
     * 'jest.mock("./api")' -> '@patch("my_module.api")'

2. UNDER THE HOOD (CPython & Memory):
   - The '@patch' decorator alters the dictionary of the target module ('sys.modules[mod_name].__dict__')
     by binding the name to a MagicMock instance.
   - In its '__exit__' clean-up phase, patch restores the original object pointer in the module dictionary.

3. COMMON GOTCHA:
   - THE "WHERE TO PATCH" TRAP:
     Suppose 'service.py' has: 'from httpx import get'.
     # BUG: @patch("httpx.get") -> Fails! 'service.py' already imported a local reference to 'get'.
     # FIX: @patch("service.get") -> Patch the reference where service looks it up!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "Where should you patch an object when mocking in Python, and what is the difference
       between Mock and MagicMock?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. The Patch Location Rule:
      "The cardinal rule of Python mocking is to patch where the object is looked up, not where
       it was originally defined.
       For example, if module 'order_service.py' executes 'from payment_gateway import process_charge',
       the name 'process_charge' is bound in 'order_service's local namespace. Patching
       'payment_gateway.process_charge' will have zero effect. You must patch 'order_service.process_charge'."
   2. Mock vs MagicMock:
      "MagicMock is a subclass of Mock that comes pre-configured with implementations for all
       Python dunder methods (like __str__, __iter__, __len__, and context manager protocols __enter__/__exit__).
       Use MagicMock by default whenever mocking objects that participate in Python's data model—such
       as file handles, collections, or context managers. Use Mock only when you specifically want
       magic methods to raise AttributeError unless explicitly defined."
   3. Verification Methods:
      "Always verify interactions with mock assertions: .assert_called_once(),
       .assert_called_with(expected_args), or inspecting .call_count to ensure the external
       service wasn't invoked multiple times."
================================================================================
"""

import sys
from unittest.mock import Mock, MagicMock, patch

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ==============================================================================
# SAMPLE CODE TO BE TESTED & MOCKED
# ==============================================================================

def get_external_weather(city: str) -> dict:
    """Function that would normally perform an expensive HTTP network call."""
    raise ConnectionError("Cannot reach real weather network in unit test!")


def format_city_weather(city: str) -> str:
    """Application function that depends on external weather service."""
    data = get_external_weather(city)
    temp_c = data["temperature_c"]
    condition = data["condition"]
    return f"{city.title()}: {temp_c}°C ({condition})"


def demonstrate_mock_basics():
    print("\n--- 1. Mock & MagicMock Capabilities ---")
    mock_obj = Mock()
    mock_obj.calculate.return_value = 42
    
    result = mock_obj.calculate(10, 20)
    print(f"  Mock return value: {result}")
    print(f"  Mock call count:   {mock_obj.calculate.call_count}")
    mock_obj.calculate.assert_called_once_with(10, 20)
    print("  Assertion .assert_called_once_with(10, 20) verified!")

    # MagicMock with context manager (__enter__ and __exit__)
    magic_ctx = MagicMock()
    with magic_ctx as ctx:
        print("  Inside MagicMock context manager block")
    magic_ctx.__enter__.assert_called_once()
    magic_ctx.__exit__.assert_called_once()
    print("  MagicMock __enter__ / __exit__ protocols verified!")


def demonstrate_patching():
    print("\n--- 2. Patching External Function Calls ---")
    # Patch get_external_weather in the current module's namespace
    target_path = f"{__name__}.get_external_weather"
    
    with patch(target_path) as mock_weather:
        # Configure return value
        mock_weather.return_value = {"temperature_c": 22.5, "condition": "Sunny"}
        
        # Call function under test
        output = format_city_weather("london")
        print(f"  Function result with mocked dependency: '{output}'")
        
        # Verify interaction
        mock_weather.assert_called_once_with("london")
        print("  Verified get_external_weather was called with 'london'!")


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

class NotificationService:
    def send_sms(self, phone: str, text: str) -> bool:
        raise ConnectionError("Live SMS network unavailable!")


class AlertManager:
    def __init__(self, notifier: NotificationService):
        self.notifier = notifier

    def trigger_critical_alert(self, phone: str, server_name: str) -> bool:
        message = f"CRITICAL: {server_name} is down!"
        return self.notifier.send_sms(phone, message)


def run_tests():
    print("\n[*] Running automated self-tests for 03_mocking_and_external_services.py...")
    # Mock NotificationService without network
    mock_notifier = Mock(spec=NotificationService)
    mock_notifier.send_sms.return_value = True

    manager = AlertManager(mock_notifier)
    status = manager.trigger_critical_alert("+1234567890", "prod-db-01")

    assert status is True
    mock_notifier.send_sms.assert_called_once_with("+1234567890", "CRITICAL: prod-db-01 is down!")
    
    print("[SUCCESS] All self-tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 5 - Mocking External Services (unittest.mock)")
    print("=" * 65)
    demonstrate_mock_basics()
    demonstrate_patching()
    print("-" * 65)
    run_tests()
    print("=" * 65)
