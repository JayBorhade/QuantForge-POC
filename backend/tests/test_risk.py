"""Pre-trade risk engine invariants."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

from app.models.order import Order, OrderSide, OrderStatus
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.position import Position
from app.models.risk_limit import RiskLimit
from app.services.risk import RiskRejected, RiskService


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


def portfolio():
    return Portfolio(
        id=uuid.uuid4(),
        cash_balance=Decimal("100000"),
        daily_pnl=Decimal("0"),
        status=PortfolioStatus.ACTIVE,
    )


class RiskTests(unittest.TestCase):
    def test_kill_switch_rejects(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, kill_switch=True)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(limits))
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY, quantity=Decimal("1")
        ))
        self.assertFalse(decision.approved)
        self.assertIn("kill switch", decision.reason)

    def test_daily_loss_rejects(self):
        p = portfolio()
        p.daily_pnl = Decimal("-5001")
        limits = RiskLimit(portfolio_id=p.id, max_daily_loss=Decimal("5000"))
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(limits))
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY, quantity=Decimal("1")
        ))
        self.assertFalse(decision.approved)

    def test_order_notional_requires_price_and_enforces_limit(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, max_order_notional=Decimal("1000"))
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(limits))
        service = RiskService(db)
        missing_price = asyncio.run(service.evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY, quantity=Decimal("10")
        ))
        too_large = asyncio.run(service.evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY,
            quantity=Decimal("10"), estimated_price=Decimal("101")
        ))
        self.assertFalse(missing_price.approved)
        self.assertFalse(too_large.approved)

    def test_position_quantity_limit(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, max_position_quantity=Decimal("10"))
        position = Position(
            portfolio_id=p.id, symbol="NIFTY", quantity=Decimal("8"),
            average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(limits), Result(position)])
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY, quantity=Decimal("3")
        ))
        self.assertFalse(decision.approved)

    def test_require_approval_raises(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, kill_switch=True)
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(limits))
        with self.assertRaises(RiskRejected):
            asyncio.run(RiskService(db).require_approval(
                portfolio=p, symbol="NIFTY", side=OrderSide.BUY, quantity=Decimal("1")
            ))


if __name__ == "__main__":
    unittest.main()
