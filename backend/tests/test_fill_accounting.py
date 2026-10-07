"""Execution fill accounting invariants."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

from app.models.execution_fill import ExecutionFill
from app.models.order import ExecutionMode, Order, OrderSide, OrderStatus
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.services.fill_accounting import FillAccountingError, FillService


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


def make_order(*, side=OrderSide.BUY, mode=ExecutionMode.PAPER, quantity="10"):
    return Order(
        id=uuid.uuid4(), portfolio_id=uuid.uuid4(), symbol="NIFTY",
        side=side, order_type="MARKET", mode=mode,
        quantity=Decimal(quantity), filled_quantity=Decimal("0"),
        status=OrderStatus.SUBMITTED, client_order_id="test-order",
    )


class FillAccountingTests(unittest.TestCase):
    def test_duplicate_broker_fill_is_idempotent(self):
        order = make_order()
        existing = ExecutionFill(order_id=order.id, broker_fill_id="fill-1", quantity=Decimal("1"), price=Decimal("100"))
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(order), Result(existing)])
        result = asyncio.run(FillService(db).apply_fill(
            order_id=order.id, quantity=Decimal("1"), price=Decimal("100"), broker_fill_id="fill-1"
        ))
        self.assertIs(result, existing)
        db.add.assert_not_called()

    def test_partial_fills_update_average_price_and_status(self):
        order = make_order()
        portfolio = Portfolio(id=order.portfolio_id, cash_balance=Decimal("5000"))
        position = Position(portfolio_id=order.portfolio_id, symbol="NIFTY", quantity=Decimal("0"), average_cost=Decimal("0"), realized_pnl=Decimal("0"))
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(order), Result(portfolio), Result(None), Result(order), Result(portfolio), Result(position)])
        service = FillService(db)
        asyncio.run(service.apply_fill(order_id=order.id, quantity=Decimal("4"), price=Decimal("100")))
        asyncio.run(service.apply_fill(order_id=order.id, quantity=Decimal("6"), price=Decimal("110")))
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(order.filled_quantity, Decimal("10"))
        self.assertEqual(order.average_fill_price, Decimal("106"))
        self.assertEqual(position.quantity, Decimal("6"))
        self.assertEqual(portfolio.cash_balance, Decimal("3940"))

    def test_paper_buy_rejects_insufficient_cash(self):
        order = make_order(quantity="2")
        portfolio = Portfolio(id=order.portfolio_id, cash_balance=Decimal("100"))
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(order), Result(portfolio), Result(None)])
        with self.assertRaises(FillAccountingError):
            asyncio.run(FillService(db).apply_fill(order_id=order.id, quantity=Decimal("2"), price=Decimal("60")))

    def test_sell_realizes_pnl_and_updates_cash(self):
        order = make_order(side=OrderSide.SELL, quantity="4")
        portfolio = Portfolio(id=order.portfolio_id, cash_balance=Decimal("100"))
        position = Position(portfolio_id=order.portfolio_id, symbol="NIFTY", quantity=Decimal("10"), average_cost=Decimal("100"), realized_pnl=Decimal("0"))
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(order), Result(portfolio), Result(position)])
        asyncio.run(FillService(db).apply_fill(order_id=order.id, quantity=Decimal("4"), price=Decimal("120"), fee=Decimal("2")))
        self.assertEqual(position.quantity, Decimal("6"))
        self.assertEqual(position.realized_pnl, Decimal("80"))
        self.assertEqual(portfolio.cash_balance, Decimal("578"))

    def test_live_fill_does_not_mutate_portfolio_cash(self):
        order = make_order(mode=ExecutionMode.LIVE)
        portfolio = Portfolio(id=order.portfolio_id, cash_balance=Decimal("100"))
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Result(order), Result(portfolio), Result(None)])
        asyncio.run(FillService(db).apply_fill(order_id=order.id, quantity=Decimal("1"), price=Decimal("50")))
        self.assertEqual(portfolio.cash_balance, Decimal("100"))


if __name__ == "__main__":
    unittest.main()
