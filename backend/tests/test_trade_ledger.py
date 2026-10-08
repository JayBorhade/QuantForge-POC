"""Fill-to-trade projection invariants."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.models.order import ExecutionMode, Order, OrderSide
from app.models.trade import TradeSide, TradeStatus
from app.services.trade_ledger import TradeLedgerService


class Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return self

    def all(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


def make_order(side=OrderSide.BUY):
    return Order(
        id=uuid.uuid4(),
        portfolio_id=uuid.uuid4(),
        strategy_id=uuid.uuid4(),
        symbol="AAPL",
        side=side,
        order_type="MARKET",
        mode=ExecutionMode.PAPER,
        quantity=Decimal("10"),
        filled_quantity=Decimal("0"),
        client_order_id="trade-test",
    )


class TradeLedgerTests(unittest.TestCase):
    def test_buy_creates_open_trade(self):
        order = make_order()
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result(None))
        db.flush = AsyncMock()

        trade = asyncio.run(
            TradeLedgerService(db).record_fill(
                order=order,
                quantity=Decimal("10"),
                price=Decimal("100"),
                fee=Decimal("1"),
                executed_at=MagicMock(),
                entry_cost_before=Decimal("0"),
            )
        )

        self.assertEqual(trade.side, TradeSide.BUY)
        self.assertEqual(trade.status, TradeStatus.OPEN)
        self.assertEqual(trade.quantity, Decimal("10"))
        self.assertEqual(trade.entry_price, Decimal("100"))
        self.assertEqual(trade.fees, Decimal("1"))

    def test_sell_closes_open_trade_and_realizes_pnl(self):
        order = make_order(OrderSide.SELL)
        open_trade = MagicMock(
            portfolio_id=order.portfolio_id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=TradeSide.BUY,
            mode=order.mode,
            status=TradeStatus.OPEN,
            quantity=Decimal("10"),
            entry_price=Decimal("100"),
            fees=Decimal("1"),
            opened_at=MagicMock(),
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result([open_trade]))
        db.flush = AsyncMock()

        closed = asyncio.run(
            TradeLedgerService(db).record_fill(
                order=order,
                quantity=Decimal("4"),
                price=Decimal("120"),
                fee=Decimal("2"),
                executed_at=MagicMock(),
                entry_cost_before=Decimal("100"),
            )
        )

        self.assertEqual(closed.side, TradeSide.SELL)
        self.assertEqual(closed.status, TradeStatus.CLOSED)
        self.assertEqual(closed.quantity, Decimal("4"))
        self.assertEqual(closed.entry_price, Decimal("100"))
        self.assertEqual(closed.exit_price, Decimal("120"))
        self.assertEqual(closed.pnl, Decimal("80"))
        self.assertEqual(open_trade.quantity, Decimal("6"))

    def test_sell_without_trade_history_still_creates_auditable_close(self):
        order = make_order(OrderSide.SELL)
        db = MagicMock()
        db.execute = AsyncMock(return_value=Result([]))
        db.flush = AsyncMock()

        closed = asyncio.run(
            TradeLedgerService(db).record_fill(
                order=order,
                quantity=Decimal("2"),
                price=Decimal("120"),
                fee=Decimal("1"),
                executed_at=MagicMock(),
                entry_cost_before=Decimal("100"),
            )
        )

        self.assertEqual(closed.status, TradeStatus.CLOSED)
        self.assertEqual(closed.pnl, Decimal("40"))
        self.assertEqual(closed.entry_price, Decimal("100"))


if __name__ == "__main__":
    unittest.main()
