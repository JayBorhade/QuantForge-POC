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

    def scalars(self):
        class Scalars:
            def __init__(self, value):
                self.value = value

            def all(self):
                return self.value if isinstance(self.value, list) else [self.value]

        return Scalars(self.value)


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

    def test_gross_exposure_rejects_projected_buy(self):
        p = portfolio()
        p.total_value = Decimal("100000")
        limits = RiskLimit(portfolio_id=p.id, max_gross_exposure=Decimal("10000"))
        position = Position(
            portfolio_id=p.id, symbol="NIFTY", quantity=Decimal("50"),
            average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            Result(limits),
            Result(position),
            Result([]),
        ])
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY,
            quantity=Decimal("60"), estimated_price=Decimal("100"),
        ))
        self.assertFalse(decision.approved)
        self.assertIn("gross exposure", decision.reason)

    def test_symbol_exposure_rejects_concentrated_order(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, max_symbol_exposure=Decimal("5000"))
        position = Position(
            portfolio_id=p.id, symbol="BTCUSDT", quantity=Decimal("30"),
            average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            Result(limits),
            Result(position),
            Result([]),
            Result([position]),
        ])
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="BTCUSDT", side=OrderSide.BUY,
            quantity=Decimal("25"), estimated_price=Decimal("100"),
        ))
        self.assertFalse(decision.approved)
        self.assertIn("symbol exposure", decision.reason)

    def test_strategy_allocation_rejects_strategy_order(self):
        p = portfolio()
        p.total_value = Decimal("10000")
        limits = RiskLimit(
            portfolio_id=p.id,
            max_strategy_allocation_pct=Decimal("0.20"),
        )
        strategy_id = uuid.uuid4()
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            Result(limits),
            Result([]),
            Result([]),
        ])
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.BUY,
            quantity=Decimal("30"), estimated_price=Decimal("100"),
            strategy_id=strategy_id,
        ))
        self.assertFalse(decision.approved)
        self.assertIn("strategy allocation", decision.reason)

    def test_sell_reduces_exposure(self):
        p = portfolio()
        limits = RiskLimit(portfolio_id=p.id, max_gross_exposure=Decimal("5000"))
        position = Position(
            portfolio_id=p.id, symbol="NIFTY", quantity=Decimal("40"),
            average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            Result(limits),
            Result(position),
            Result([]),
            Result([position]),
        ])
        decision = asyncio.run(RiskService(db).evaluate(
            portfolio=p, symbol="NIFTY", side=OrderSide.SELL,
            quantity=Decimal("20"), estimated_price=Decimal("100"),
        ))
        self.assertTrue(decision.approved)

if __name__ == "__main__":

    unittest.main()
