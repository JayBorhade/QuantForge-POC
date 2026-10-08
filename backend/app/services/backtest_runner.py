"""Backtest execution — used by API (sync) and Celery."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

from app.db.sync_session import get_sync_db
from app.models.strategy import RunMode, RunStatus, Strategy, StrategyRun
from app.backtesting.fingerprint import configuration_fingerprint


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
        lease_token = str(uuid.uuid4())
        if run_id:
            run = db.get(StrategyRun, uuid.UUID(run_id))
        if run_id:
            run = db.get(StrategyRun, uuid.UUID(run_id))
            if not run:
                raise ValueError(f"Backtest run {run_id} not found")
            if run.strategy_id != strategy.id or run.mode != RunMode.BACKTEST:
                raise ValueError("Backtest run does not belong to the requested strategy")
            if run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
                return {"run_id": str(run.id), "status": run.status.value, **(run.results or {})}
            if run.status == RunStatus.RUNNING and run.started_at is not None:
                age = datetime.now(timezone.utc) - run.started_at
                if age < timedelta(minutes=30):
                    return {"run_id": str(run.id), "status": run.status.value, "message": "Backtest already running"}
                run.error_message = "Previous backtest worker lease expired; execution reclaimed."
        else:
            run = StrategyRun(
                id=uuid.uuid4(),
                strategy_id=strategy.id,
                mode=RunMode.BACKTEST,
                status=RunStatus.RUNNING,
                start_date=start_date,
                end_date=end_date,
                started_at=datetime.now(timezone.utc),
            )
            db.add(run)

        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc)
        run.worker_token = lease_token
        run.worker_started_at = run.started_at
        run.initial_capital = Decimal(str(initial_capital))
        run.input_snapshot = {
            "strategy_type": strategy.strategy_type.value,
            "symbol": strategy.symbol.upper(),
            "parameters": strategy.parameters or {},
            "initial_capital": str(initial_capital),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        run.configuration_fingerprint = configuration_fingerprint(
            strategy_type=strategy.strategy_type.value,
            symbol=strategy.symbol,
            parameters=strategy.parameters or {},
            config={"initial_capital": initial_capital},
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        run.identity_key = f"{strategy.id}:{RunMode.BACKTEST.value}:{run.configuration_fingerprint}"
        run.data_source = "yfinance"
        run.data_revision = "provider-runtime"
        db.flush()

        try:
            engine = BacktestEngine()
            snapshot = run.input_snapshot or {}
            result = engine.run(
                strategy_id=str(strategy.id),
                start_date=start_date,
                end_date=end_date,
                initial_capital=float(snapshot.get("initial_capital", initial_capital)),
                strategy_type=str(snapshot.get("strategy_type", strategy.strategy_type.value)),
                symbol=str(snapshot.get("symbol", strategy.symbol)),
                parameters=snapshot.get("parameters", strategy.parameters or {}),
            )

            db.refresh(run)
            if run.status == RunStatus.CANCELLED or run.worker_token != lease_token:
                return {"run_id": str(run.id), "status": run.status.value, "message": "Backtest worker lease no longer owns this run"}

            if "error" in result:
                run.status = RunStatus.FAILED
                run.identity_key = None
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
            run.worker_token = None
            run.worker_started_at = None

            return {
                "run_id": str(run.id),
                "status": run.status.value,
                **result,
            }
        except Exception as e:
            # Cancellation or lease loss wins over a late worker exception.
            # Never convert a run that another actor cancelled/reclaimed into FAILED.
            db.refresh(run)
            if run.status == RunStatus.CANCELLED or run.worker_token != lease_token:
                return {
                    "run_id": str(run.id),
                    "status": run.status.value,
                    "message": "Backtest worker lease no longer owns this run",
                }
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            run.worker_token = None
            run.worker_started_at = None
            run.identity_key = None
            raise
