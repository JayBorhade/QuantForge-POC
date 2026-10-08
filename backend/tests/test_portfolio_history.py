"""Portfolio history and performance tests."""

import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.portfolio_history import PortfolioHistoryService


class PortfolioHistoryTests(unittest.TestCase):
    def test_record_snapshot_calculates_return_and_drawdown(self):
        db = AsyncMock()
        previous = PortfolioSnapshot(
            portfolio_id="p",
            recorded_at=datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
            equity=Decimal("1000"),
            cash_balance=Decimal("1000"),
            position_market_value=Decimal("0"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
        )
        previous_result = MagicMock()
        previous_result.scalar_one_or_none.return_value = previous
        peak_result = MagicMock()
        peak_result.scalar_one_or_none.return_value = Decimal("1200")
        db.execute = AsyncMock(side_effect=[previous_result, peak_result])
        db.add = MagicMock()
        db.flush = AsyncMock()

        portfolio = MagicMock(id="p", total_value=Decimal("1000"))
        valuation = MagicMock(
            equity=Decimal("1080"),
            cash_balance=Decimal("500"),
            position_market_value=Decimal("580"),
            realized_pnl=Decimal("10"),
            unrealized_pnl=Decimal("70"),
            total_pnl=Decimal("80"),
        )
        now = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)

        snapshot = asyncio.run(
            PortfolioHistoryService(db).record_snapshot(portfolio, valuation, recorded_at=now)
        )

        self.assertEqual(snapshot.daily_return, Decimal("0.08"))
        self.assertEqual(snapshot.drawdown, Decimal("-0.10"))
        db.add.assert_called_once()
        db.flush.assert_awaited_once()

    def test_metrics_returns_empty_period_without_snapshots(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        metrics = asyncio.run(PortfolioHistoryService(db).metrics("p", days=30))

        self.assertEqual(metrics["observations"], 0)
        self.assertEqual(metrics["return"], Decimal("0"))

    def test_metrics_calculates_return_drawdown_and_volatility(self):
        db = AsyncMock()
        now = datetime.now(timezone.utc)
        snapshots = [
            PortfolioSnapshot(
                portfolio_id="p",
                recorded_at=now - timedelta(hours=2),
                equity=Decimal("1000"),
                cash_balance=Decimal("1000"),
                position_market_value=Decimal("0"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                total_pnl=Decimal("0"),
                daily_return=Decimal("0"),
                drawdown=Decimal("0"),
            ),
            PortfolioSnapshot(
                portfolio_id="p",
                recorded_at=now - timedelta(hours=1),
                equity=Decimal("1100"),
                cash_balance=Decimal("1000"),
                position_market_value=Decimal("100"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("100"),
                total_pnl=Decimal("100"),
                daily_return=Decimal("0.10"),
                drawdown=Decimal("0"),
            ),
            PortfolioSnapshot(
                portfolio_id="p",
                recorded_at=now,
                equity=Decimal("990"),
                cash_balance=Decimal("900"),
                position_market_value=Decimal("90"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("-10"),
                total_pnl=Decimal("-10"),
                daily_return=Decimal("-0.10"),
                drawdown=Decimal("-0.10"),
            ),
        ]
        result = MagicMock()
        result.scalars.return_value.all.return_value = snapshots
        db.execute.return_value = result

        metrics = asyncio.run(PortfolioHistoryService(db).metrics("p", days=30))

        self.assertEqual(metrics["observations"], 3)
        self.assertEqual(metrics["return"], Decimal("-0.01"))
        self.assertEqual(metrics["max_drawdown"], Decimal("-0.10"))
        self.assertEqual(metrics["best_period_return"], Decimal("0.10"))
        self.assertEqual(metrics["worst_period_return"], Decimal("-0.10"))


if __name__ == "__main__":
    unittest.main()
