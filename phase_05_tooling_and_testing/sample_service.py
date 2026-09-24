"""
Sample user repository and currency conversion service.
Serves as the system-under-test (SUT) for modern Pytest test suite.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserAccount:
    user_id: int
    username: str
    balance_usd: float
    is_active: bool = True


class CurrencyExchangeClient:
    """External currency conversion service."""
    def get_exchange_rate(self, from_curr: str, to_curr: str) -> float:
        raise ConnectionError("Real currency exchange API requires live internet!")


class UserService:
    def __init__(self, exchange_client: Optional[CurrencyExchangeClient] = None):
        self._users: Dict[int, UserAccount] = {}
        self.exchange_client = exchange_client or CurrencyExchangeClient()

    def add_user(self, user_id: int, username: str, balance: float) -> UserAccount:
        if user_id in self._users:
            raise ValueError(f"User ID {user_id} already exists.")
        if balance < 0:
            raise ValueError("Balance cannot be negative.")
        user = UserAccount(user_id=user_id, username=username, balance_usd=balance)
        self._users[user_id] = user
        return user

    def get_user(self, user_id: int) -> Optional[UserAccount]:
        return self._users.get(user_id)

    def convert_user_balance(self, user_id: int, target_currency: str) -> float:
        user = self.get_user(user_id)
        if not user:
            raise KeyError(f"User {user_id} not found.")
        rate = self.exchange_client.get_exchange_rate("USD", target_currency)
        return round(user.balance_usd * rate, 2)
