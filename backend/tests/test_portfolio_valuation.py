"""Portfolio valuation invariants."""

import asyncio
import unittest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.portfolio_valuation import (
    LatestExecutionQuoteProvider,
    PortfolioValuationError,
    PortfolioValuationService,
)


class PortfolioValuationTests(unittest.TestCase):
    def _service(self, positions, price_map):
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = positions
        db.execute.return_value = result
        quote_provider = AsyncMock()
        quote_provider.get_quote.side_effect = lambda symbol: {"price": price_map[symbol]}
        return PortfolioValuationService(db, quote_provider), db

    def test_marks_positions_and_persists_equity(self):
        position = MagicMock(
            symbol="ABC",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            realized_pnl=Decimal("25"),
        )
        portfolio = MagicMock(id="portfolio", cash_balance=Decimal("500"))
        service, db = self._service([position], {"ABC": "120"})

        valuation = asyncio.run(service.value_portfolio(portfolio))

        self.assertEqual(valuation.position_market_value, Decimal("1200"))
        self.assertEqual(valuation.equity, Decimal("1700"))
        self.assertEqual(valuation.unrealized_pnl, Decimal("200"))
        self.assertEqual(valuation.realized_pnl, Decimal("25"))
        self.assertEqual(valuation.total_pnl, Decimal("225"))
        self.assertEqual(portfolio.total_value, Decimal("1700"))
        self.assertEqual(portfolio.total_pnl, Decimal("225"))
        self.assertEqual(portfolio.risk_exposure, Decimal("1200") / Decimal("1700"))
        db.flush.assert_awaited_once()

    def test_invalid_market_price_is_rejected_without_persisting(self):
        position = MagicMock(
            symbol="ABC", quantity=Decimal("10"), average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        portfolio = MagicMock(id="portfolio", cash_balance=Decimal("500"))
        service, db = self._service([position], {"ABC": "0"})

        with self.assertRaises(PortfolioValuationError):
            asyncio.run(service.value_portfolio(portfolio))
        db.flush.assert_not_awaited()

    def test_latest_execution_quote_provider_returns_latest_paper_mark(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = Decimal("125.50")
        db.execute.return_value = result
        provider = LatestExecutionQuoteProvider(db, "portfolio")

        quote = asyncio.run(provider.get_quote("ABC"))

        self.assertEqual(quote, {"price": Decimal("125.50"), "source": "latest_execution"})
        db.execute.assert_awaited_once()

    def test_latest_execution_quote_provider_rejects_missing_mark(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result
        provider = LatestExecutionQuoteProvider(db, "portfolio")

        with self.assertRaises(PortfolioValuationError):
            asyncio.run(provider.get_quote("ABC"))

    def test_can_value_without_persisting(self):
        position = MagicMock(
            symbol="ABC", quantity=Decimal("2"), average_cost=Decimal("100"), realized_pnl=Decimal("0")
        )
        portfolio = MagicMock(id="portfolio", cash_balance=Decimal("100"))
        service, db = self._service([position], {"ABC": "90"})

        valuation = asyncio.run(service.value_portfolio(portfolio, persist=False))

        self.assertEqual(valuation.equity, Decimal("280"))
        db.flush.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
