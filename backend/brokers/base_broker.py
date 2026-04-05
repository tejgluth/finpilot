from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models.trade import Order


class BrokerAdapter(ABC):
    @abstractmethod
    async def submit_order(self, order: Order) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def cancel_all_orders(self) -> dict:
        raise NotImplementedError
