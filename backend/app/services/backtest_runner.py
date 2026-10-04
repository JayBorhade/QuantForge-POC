"""Backtest execution — used by API (sync) and Celery."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from app.db.sync_session import get_sync_db
from app.models.strategy import RunMode, RunStatus, Strategy, StrategyRun


def run_backtest_for_strategy(
    strategy_id: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    run_id: str | None = None,
) -> Dict[str, Any]:
    from strategies.backtest import BacktestEngine

    with get_sync_db() as db:
        strategy = db.get(Strategy, uuid.UUID(strategy_id))
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        run = None
        if run_id:
            run = db.get(StrategyRun, uuid.UUID(run_id))
        if not run:
            run = StrategyRun(
                id=uuid.UUID(run_id) if run_id else uuid.uuid4(),
                strategy_id=strategy.id,
                mode=RunMode.BACKTEST,
                status=RunStatus.RUNNING,
                start_date=start_date,
                end_date=end_date,
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)
        else:
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
        db.flush()

        try:
            engine = BacktestEngine()
            result = engine.run(
                strategy_id=str(strategy.id),
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                strategy_type=strategy.strategy_type.value,
                symbol=strategy.symbol,
                parameters=strategy.parameters or {},
            )

            if "error" in result:
                run.status = RunStatus.FAILED
                run.error_message = result["error"]
            else:
                run.status = RunStatus.COMPLETED
                run.sharpe_ratio = Decimal(str(result.get("sharpe_ratio", 0)))
                run.max_drawdown = Decimal(str(result.get("max_drawdown", 0)))
                run.total_return = Decimal(str(result.get("total_return", 0)))
                run.win_rate = Decimal(str(result.get("win_rate", 0)))
                run.total_trades = result.get("total_trades", 0)
                run.results = result
                run.completed_at = datetime.now(timezone.utc)

            return {
                "run_id": str(run.id),
                "status": run.status.value,
                **result,
            }
        except Exception as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            raise
