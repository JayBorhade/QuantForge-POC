"""Scheduled portfolio snapshot task."""

import asyncio
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.services.portfolio_history import PortfolioHistoryService
from app.services.portfolio_valuation import LatestExecutionQuoteProvider, PortfolioValuationService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=0, ignore_result=False)
def record_portfolio_snapshots(self):
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Portfolio).where(Portfolio.status == "active").order_by(Portfolio.created_at)
            )
            portfolios = list(result.scalars().all())
            summary = {"recorded": 0, "skipped": 0, "failed": 0}

            for portfolio in portfolios:
                try:
                    provider = LatestExecutionQuoteProvider(db, portfolio.id)
                    valuation = await PortfolioValuationService(db, provider).value_portfolio(
                        portfolio, persist=True
                    )
                    await PortfolioHistoryService(db).record_snapshot(portfolio, valuation)
                    await db.commit()
                    summary["recorded"] += 1
                except Exception as exc:
                    await db.rollback()
                    summary["failed"] += 1
                    logger.exception("Portfolio snapshot failed for %s: %s", portfolio.id, exc)

            return summary

    return asyncio.run(_run())
