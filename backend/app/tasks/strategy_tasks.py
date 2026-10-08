"""Celery tasks for strategy execution and backtesting."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

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


def build_paper_run_identity(strategy_id: str, scheduled_for: str | None) -> str:
    """Build the stable identity used to make scheduled paper runs replay-safe."""
    slot = scheduled_for or datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
    return f"{strategy_id}:paper:{slot}"


@celery_app.task(bind=True, max_retries=3)
def run_strategy_task(self, strategy_id: str, mode: str = "paper"):
    """Compatibility task that routes strategy starts through the canonical runtime."""
    logger.info("Starting strategy %s in %s mode", strategy_id, mode)
    try:
        from app.db.sync_session import get_sync_db
        from app.models.strategy import Strategy, StrategyStatus

        with get_sync_db() as db:
            strategy = db.get(Strategy, uuid.UUID(strategy_id))
            if not strategy:
                return {"error": "Strategy not found"}
            if mode != "paper" or not strategy.is_paper:
                raise ValueError("Only paper strategy runtime is enabled")
            strategy.status = StrategyStatus.ACTIVE
            db.commit()

        if strategy.schedule_portfolio_id is None:
            return {
                "status": "activated",
                "strategy_id": strategy_id,
                "reason": "no execution portfolio configured",
            }

        return execute_strategy_signal_task.apply(
            args=[strategy_id, str(strategy.schedule_portfolio_id), None]
        ).get()
    except Exception as exc:
        logger.exception("Strategy start failed: %s", exc)
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


@celery_app.task(bind=True, max_retries=2, ignore_result=False)
def execute_strategy_signal_task(
    self,
    strategy_id: str,
    portfolio_id: str,
    scheduled_for: str | None = None,
):
    """Evaluate one paper signal, persist its run, and execute it exactly once."""
    async def _execute():
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.db.session import AsyncSessionLocal
        from app.models.portfolio import Portfolio
        from app.models.strategy import RunMode, RunStatus, Strategy, StrategyRun
        from app.services.strategy_execution import StrategyExecutionService
        from strategies.engine import StrategyEngine

        identity_key = build_paper_run_identity(strategy_id, scheduled_for)
        async with AsyncSessionLocal() as db:
            strategy = await db.get(Strategy, uuid.UUID(strategy_id))
            if strategy is None:
                raise ValueError("Strategy not found")
            if not strategy.is_paper:
                raise ValueError("Only paper strategies can enter the runtime")

            result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.positions))
                .where(
                    Portfolio.id == uuid.UUID(portfolio_id),
                    Portfolio.user_id == strategy.user_id,
                )
            )
            portfolio = result.scalar_one_or_none()
            if portfolio is None:
                raise ValueError("Portfolio not found for strategy owner")

            run_result = await db.execute(
                select(StrategyRun).where(StrategyRun.identity_key == identity_key).limit(1)
            )
            run = run_result.scalar_one_or_none()
            if run is None:
                run = StrategyRun(
                    strategy_id=strategy.id,
                    mode=RunMode.PAPER,
                    status=RunStatus.RUNNING,
                    identity_key=identity_key,
                    start_date=datetime.now(timezone.utc),
                    input_snapshot={
                        "strategy_type": strategy.strategy_type.value,
                        "symbol": strategy.symbol,
                        "parameters": strategy.parameters or {},
                        "portfolio_id": str(portfolio.id),
                        "scheduled_for": scheduled_for,
                    },
                    data_source="strategy_engine",
                    data_revision="provider-runtime",
                    started_at=datetime.now(timezone.utc),
                )
                db.add(run)
                await db.flush()
            elif run.status is RunStatus.COMPLETED:
                return run.results or {"status": "completed", "run_id": str(run.id)}
            else:
                run.status = RunStatus.RUNNING
                run.error_message = None
                run.started_at = datetime.now(timezone.utc)

            try:
                engine = StrategyEngine()
                data = engine.fetch_data(strategy.symbol)
                execution_result = await StrategyExecutionService().execute_latest_signal(
                    db=db,
                    strategy=strategy,
                    portfolio=portfolio,
                    data=data,
                )
                completed_at = datetime.now(timezone.utc)
                run.status = RunStatus.COMPLETED
                run.completed_at = completed_at
                run.end_date = completed_at
                run.total_trades = 1 if execution_result.get("status") == "executed" else 0
                run.results = {
                    "execution": execution_result,
                    "scheduled_for": scheduled_for,
                }
                await db.commit()
                return {"run_id": str(run.id), **execution_result}
            except Exception as exc:
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now(timezone.utc)
                run.end_date = run.completed_at
                run.error_message = str(exc)[:2000]
                await db.commit()
                raise

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.exception("Strategy signal execution failed for strategy %s", strategy_id)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=0, ignore_result=False)
def dispatch_scheduled_strategy_tasks(self):
    """Dispatch due paper strategy schedules; the next beat tick handles recovery."""
    from app.services.strategy_scheduler import dispatch_due_strategies

    try:
        return dispatch_due_strategies()
    except Exception:
        logger.exception("Scheduled strategy dispatcher failed")
        raise
