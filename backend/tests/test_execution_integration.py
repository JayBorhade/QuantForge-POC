"""Execution service integration tests for the canonical paper adapter."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.brokers.paper_adapter import PaperBrokerAdapter
from app.models.order import ExecutionMode, OrderSide, OrderStatus, OrderType
from app.models.portfolio import Portfolio, PortfolioStatus
from app.services.execution import ExecutionService


class Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ExecutionIntegrationTests(unittest.TestCase):
    def test_paper_submission_uses_canonical_broker_contract(self):
        portfolio = Portfolio(
            id=uuid.uuid4(),
            cash_balance=Decimal("100000"),
            daily_pnl=Decimal("0"),
            status=PortfolioStatus.ACTIVE,
        )
        portfolio.user_id = uuid.uuid4()
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[
            Result(type("User", (), {"is_verified": True, "two_factor_enabled": True})()),
            Result(),
            Result(),
        ])
        db.flush = AsyncMock()
        broker = PaperBrokerAdapter()

        order = asyncio.run(
            ExecutionService(db, broker).submit(
                portfolio=portfolio,
                symbol=" reliance ",
                side=OrderSide.BUY,
                quantity=Decimal("2"),
                mode=ExecutionMode.LIVE,
                client_order_id="client-1",
                order_type=OrderType.LIMIT,
                limit_price=Decimal("2500"),
            )
        )

        self.assertEqual(order.status, OrderStatus.SUBMITTED)
        self.assertEqual(order.symbol, "RELIANCE")
        self.assertEqual(order.broker_order_id, "paper-client-1")

    def test_paper_mode_does_not_require_network_broker(self):
        portfolio = Portfolio(
            id=uuid.uuid4(),
            cash_balance=Decimal("100000"),
            daily_pnl=Decimal("0"),
            status=PortfolioStatus.ACTIVE,
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result())
        db.flush = AsyncMock()

        order = asyncio.run(
            ExecutionService(db).submit(
                portfolio=portfolio,
                symbol="RELIANCE",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                mode=ExecutionMode.PAPER,
                client_order_id="paper-1",
            )
        )

        self.assertEqual(order.status, OrderStatus.SUBMITTED)


if __name__ == "__main__":
    unittest.main()
