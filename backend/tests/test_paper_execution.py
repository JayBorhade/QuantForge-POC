"""Paper execution end-to-end invariants."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.models.order import OrderSide
from app.models.portfolio import Portfolio, PortfolioStatus
from app.services.paper_execution import PaperExecutionService


class Result:
    def scalar_one_or_none(self):
        return None


class PaperExecutionTests(unittest.TestCase):
    def test_paper_buy_uses_paper_cash_accounting(self):
        portfolio = Portfolio(
            id=uuid.uuid4(),
            cash_balance=Decimal("10000"),
            daily_pnl=Decimal("0"),
            status=PortfolioStatus.ACTIVE,
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result())
        db.flush = AsyncMock()

        order, fill = asyncio.run(
            PaperExecutionService(db).execute(
                portfolio=portfolio,
                symbol="NIFTY",
                side=OrderSide.BUY,
                quantity=Decimal("2"),
                client_order_id="paper-e2e-1",
                fill_price=Decimal("100"),
                fee=Decimal("2"),
            )
        )

        self.assertEqual(order.broker_order_id, "paper-paper-e2e-1")
        self.assertEqual(fill.quantity, Decimal("2"))
        self.assertEqual(portfolio.cash_balance, Decimal("9798"))
        self.assertEqual(order.filled_quantity, Decimal("2"))

    def test_paper_execution_replay_reuses_order(self):
        portfolio = Portfolio(
            id=uuid.uuid4(),
            cash_balance=Decimal("10000"),
            daily_pnl=Decimal("0"),
            status=PortfolioStatus.ACTIVE,
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result())
        db.flush = AsyncMock()

        service = PaperExecutionService(db)
        first, _ = asyncio.run(service.execute(
            portfolio=portfolio, symbol="NIFTY", side=OrderSide.BUY,
            quantity=Decimal("1"), client_order_id="paper-replay",
            fill_price=Decimal("100"),
        ))
        self.assertEqual(first.status.value, "filled")
