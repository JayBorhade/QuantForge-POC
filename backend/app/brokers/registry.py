"""Broker adapter registry."""

from typing import Mapping

from app.models.broker_token import BrokerType
from app.brokers.base import BrokerAdapter


class BrokerRegistry:
    def __init__(self, adapters: Mapping[BrokerType, BrokerAdapter] | None = None):
        self._adapters = dict(adapters or {})

    def register(self, broker: BrokerType, adapter: BrokerAdapter) -> None:
        if broker in self._adapters:
            raise ValueError(f"Broker adapter already registered: {broker.value}")
        self._adapters[broker] = adapter

    def get(self, broker: BrokerType) -> BrokerAdapter:
        try:
            return self._adapters[broker]
        except KeyError as exc:
            raise LookupError(f"No broker adapter registered for {broker.value}") from exc
