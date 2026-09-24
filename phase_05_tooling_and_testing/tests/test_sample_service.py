"""
Comprehensive Pytest Test Suite demonstrating:
- Plain assertions
- Fixtures with dependency injection
- Parametrized tests
- Mocking external dependencies
"""
import pytest
from unittest.mock import Mock

try:
    from phase_05_tooling_and_testing.sample_service import (
        UserService,
        UserAccount,
        CurrencyExchangeClient
    )
except ModuleNotFoundError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sample_service import (
        UserService,
        UserAccount,
        CurrencyExchangeClient
    )


# ==============================================================================
# 1. FIXTURES
# ==============================================================================

@pytest.fixture
def mock_exchange_client() -> Mock:
    """Fixture providing a mocked currency client."""
    client = Mock(spec=CurrencyExchangeClient)
    # Default rate USD -> EUR = 0.90
    client.get_exchange_rate.return_value = 0.90
    return client


@pytest.fixture
def user_service(mock_exchange_client) -> UserService:
    """Fixture injecting the mock exchange client into UserService."""
    service = UserService(exchange_client=mock_exchange_client)
    service.add_user(1, "alice", 100.0)
    service.add_user(2, "bob", 250.0)
    return service


# ==============================================================================
# 2. TESTS USING FIXTURES
# ==============================================================================

def test_add_and_get_user(user_service: UserService):
    user = user_service.get_user(1)
    assert user is not None
    assert user.username == "alice"
    assert user.balance_usd == 100.0


def test_add_duplicate_user_raises_error(user_service: UserService):
    with pytest.raises(ValueError, match="already exists"):
        user_service.add_user(1, "duplicate_alice", 50.0)


def test_convert_balance_with_mock(user_service: UserService, mock_exchange_client: Mock):
    # Test balance conversion using injected mock exchange client
    eur_balance = user_service.convert_user_balance(1, "EUR")
    assert eur_balance == 90.0  # 100 USD * 0.90 = 90.0 EUR
    
    mock_exchange_client.get_exchange_rate.assert_called_once_with("USD", "EUR")


# ==============================================================================
# 3. PARAMETRIZED TESTS
# ==============================================================================

@pytest.mark.parametrize(
    "user_id, expected_usd, expected_eur",
    [
        (1, 100.0, 90.0),
        (2, 250.0, 225.0),
    ]
)
def test_parametrized_balance_conversion(
    user_service: UserService,
    user_id: int,
    expected_usd: float,
    expected_eur: float
):
    user = user_service.get_user(user_id)
    assert user.balance_usd == expected_usd
    assert user_service.convert_user_balance(user_id, "EUR") == expected_eur
