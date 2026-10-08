"""Celery tasks for strategy execution and backtesting."""

import asyncio
import logging
import uuid
from datetime import datetime

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


@celery_app.task(bind=True, max_retries=3)
def run_strategy_task(self, strategy_id: str, mode: str = "paper"):
    logger.info("Running strategy %s in %s mode", strategy_id, mode)
    try:
        from app.db.sync_session import get_sync_db
        from app.models.strategy import Strategy, StrategyStatus
        from strategies.engine import StrategyEngine

        with get_sync_db() as db:
            strategy = db.get(Strategy, uuid.UUID(strategy_id))
            if not strategy:
                return {"error": "Strategy not found"}

            engine = StrategyEngine()
            result = engine.execute_strategy(
                strategy_type=strategy.strategy_type.value,
                symbol=strategy.symbol,
                parameters=strategy.parameters or {},
                mode=mode,
            )
            strategy.status = StrategyStatus.ACTIVE
            db.commit()
            return result
    except Exception as exc:
        logger.exception("Strategy execution failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True)
def run_backtest_task(
    self,
    run_id: str,
    strategy_id: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000.0,
):
    logger.info("Backtesting run %s strategy %s", run_id, strategy_id)
    from app.services.backtest_runner import run_backtest_for_strategy

    return run_backtest_for_strategy(
        strategy_id=strategy_id,
        start_date=datetime.fromisoformat(start_date.replace("Z", "+00:00")),
        end_date=datetime.fromisoformat(end_date.replace("Z", "+00:00")),
        initial_capital=initial_capital,
        run_id=run_id,
    )


@celery_app.task(bind=True, max_retries=0)
def execute_strategy_signal_task(self, strategy_id: str, portfolio_id: str):
    """Evaluate and execute the latest paper strategy signal for a portfolio."""
    async def _execute():
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.db.session import AsyncSessionLocal
        from app.models.portfolio import Portfolio
        from app.models.strategy import Strategy
        from app.services.strategy_execution import StrategyExecutionService
        from strategies.engine import StrategyEngine

        async with AsyncSessionLocal() as db:
            strategy = await db.get(Strategy, uuid.UUID(strategy_id))
            if strategy is None:
                raise ValueError("Strategy not found")

            result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.positions))
                .where(Portfolio.id == uuid.UUID(portfolio_id), Portfolio.user_id == strategy.user_id)
            )
            portfolio = result.scalar_one_or_none()
            if portfolio is None:
                raise ValueError("Portfolio not found for strategy owner")

            engine = StrategyEngine()
            data = engine.fetch_data(strategy.symbol)
            result = await StrategyExecutionService().execute_latest_signal(
                db=db,
                strategy=strategy,
                portfolio=portfolio,
                data=data,
            )
            await db.commit()
            return result

    try:
        return _run_async(_execute())
    except Exception:
        logger.exception("Strategy signal execution failed for strategy %s", strategy_id)
        raise
