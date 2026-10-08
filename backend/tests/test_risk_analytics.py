import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

from app.models.order import Order, OrderSide, OrderStatus, OrderType, ExecutionMode
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.position import Position
from app.models.risk_limit import RiskLimit
from app.services.risk_analytics import RiskAnalyticsService


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        class Scalars:
            def __init__(self, value):
                self.value = value

            def all(self):
                return self.value

        return Scalars(self.value)


class RiskAnalyticsTests(unittest.TestCase):
    def test_summary_calculates_exposure_and_utilization(self):
        portfolio = Portfolio(
            id=uuid.uuid4(),
            cash_balance=Decimal("9000"),
            total_value=Decimal("10000"),
            daily_pnl=Decimal("-250"),
            status=PortfolioStatus.ACTIVE,
        )
        position = Position(
            portfolio_id=portfolio.id,
            symbol="NIFTY",
            quantity=Decimal("20"),
            average_cost=Decimal("100"),
            realized_pnl=Decimal("0"),
        )
        order = Order(
            portfolio_id=portfolio.id,
            client_order_id="risk-test",
            symbol="NIFTY",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            mode=ExecutionMode.PAPER,
            quantity=Decimal("10"),
            filled_quantity=Decimal("2"),
            limit_price=Decimal("110"),
            status=OrderStatus.SUBMITTED,
        )
        limits = RiskLimit(
            portfolio_id=portfolio.id,
            max_gross_exposure=Decimal("5000"),
            max_daily_loss=Decimal("1000"),
            max_open_orders=4,
        )
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            Result([position]),
            Result([order]),
            Result(limits),
        ])

        summary = asyncio.run(RiskAnalyticsService(db).summarize(portfolio))

        self.assertEqual(summary.gross_exposure, Decimal("2000"))
        self.assertEqual(summary.net_exposure, Decimal("2000"))
        self.assertEqual(summary.open_order_notional, Decimal("880"))
        self.assertEqual(summary.position_count, 1)
        self.assertEqual(summary.open_order_count, 1)
        self.assertEqual(summary.gross_utilization, Decimal("0.4"))
        self.assertEqual(summary.daily_loss_utilization, Decimal("0.25"))
        self.assertEqual(summary.open_order_utilization, Decimal("0.25"))
        self.assertEqual(summary.largest_symbol, "NIFTY")


if __name__ == "__main__":
    unittest.main()
