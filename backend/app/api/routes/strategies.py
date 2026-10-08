"""Strategy management routes."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.strategy import RunMode, RunStatus, Strategy, StrategyRun, StrategyStatus
from app.schemas.strategy import (
    BacktestRequest,
    BacktestResponse,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
)
from app.services.audit import log_audit
from app.services.backtest_runner import run_backtest_for_strategy
from app.backtesting.fingerprint import configuration_fingerprint

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("", response_model=List[StrategyResponse])
async def list_strategies(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Strategy).where(Strategy.user_id == current_user.id).order_by(Strategy.created_at.desc())
    )
    return result.scalars().all()


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    data: BacktestRequest,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Run backtest — creates StrategyRun, queues Celery or runs inline."""
    strategy = await _get_user_strategy(db, data.strategy_id, current_user.id)

    fingerprint = configuration_fingerprint(
        strategy_type=strategy.strategy_type.value,
        symbol=strategy.symbol,
        parameters=strategy.parameters or {},
        config={"initial_capital": data.initial_capital},
        start_date=data.start_date.isoformat(),
        end_date=data.end_date.isoformat(),
    )
    existing = await db.execute(
        select(StrategyRun)
        .where(
            StrategyRun.strategy_id == strategy.id,
            StrategyRun.mode == RunMode.BACKTEST,
            StrategyRun.configuration_fingerprint == fingerprint,
            StrategyRun.status.in_([RunStatus.PENDING, RunStatus.RUNNING, RunStatus.COMPLETED]),
        )
        .order_by(StrategyRun.created_at.desc())
        .limit(1)
    )
    existing_run = existing.scalar_one_or_none()
    if existing_run:
        return BacktestResponse(
            run_id=existing_run.id,
            status=existing_run.status.value,
            sharpe_ratio=float(existing_run.sharpe_ratio) if existing_run.sharpe_ratio is not None else None,
            max_drawdown=float(existing_run.max_drawdown) if existing_run.max_drawdown is not None else None,
            total_return=float(existing_run.total_return) if existing_run.total_return is not None else None,
            win_rate=float(existing_run.win_rate) if existing_run.win_rate is not None else None,
            total_trades=existing_run.total_trades,
            equity_curve=(existing_run.results or {}).get("equity_curve"),
            trade_history=(existing_run.results or {}).get("trade_history"),
        )

    run = StrategyRun(
        strategy_id=strategy.id,
        mode=RunMode.BACKTEST,
        status=RunStatus.PENDING,
        start_date=data.start_date,
        end_date=data.end_date,
        initial_capital=data.initial_capital,
        configuration_fingerprint=fingerprint,
        data_source="yfinance",
        data_revision="provider-runtime",
        input_snapshot={
            "strategy_type": strategy.strategy_type.value,
            "symbol": strategy.symbol,
            "parameters": strategy.parameters or {},
            "initial_capital": str(data.initial_capital),
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
        },
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    def _execute():
        run_backtest_for_strategy(
            str(strategy.id),
            data.start_date,
            data.end_date,
            data.initial_capital,
            run_id=str(run.id),
        )

    try:
        from app.tasks.strategy_tasks import run_backtest_task

        run_backtest_task.delay(
            str(run.id),
            str(strategy.id),
            data.start_date.isoformat(),
            data.end_date.isoformat(),
            data.initial_capital,
        )
        run.status = RunStatus.RUNNING
    except Exception:
        background_tasks.add_task(_execute)
        run.status = RunStatus.RUNNING

    await log_audit(db, action="strategy.backtest", user_id=current_user.id, resource_id=str(run.id))

    return BacktestResponse(
        run_id=run.id,
        status=run.status.value,
        total_trades=0,
        sharpe_ratio=None,
        max_drawdown=None,
        total_return=None,
        win_rate=None,
        equity_curve=None,
        trade_history=None,
    )


@router.get("/runs/{run_id}")
async def get_backtest_run(run_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(StrategyRun)
        .join(Strategy)
        .where(StrategyRun.id == run_id, Strategy.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    results = run.results or {}
    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "sharpe_ratio": float(run.sharpe_ratio) if run.sharpe_ratio else None,
        "max_drawdown": float(run.max_drawdown) if run.max_drawdown else None,
        "total_return": float(run.total_return) if run.total_return else None,
        "win_rate": float(run.win_rate) if run.win_rate else None,
        "total_trades": run.total_trades,
        "equity_curve": results.get("equity_curve"),
        "trade_history": results.get("trade_history"),
        "error_message": run.error_message,
    }


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    data: StrategyCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    strategy = Strategy(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        strategy_type=data.strategy_type,
        symbol=data.symbol.upper(),
        parameters=data.parameters,
        is_paper=data.is_paper,
        schedule_cron=data.schedule_cron,
    )
    db.add(strategy)
    await db.flush()
    await db.refresh(strategy)
    await log_audit(
        db,
        action="strategy.create",
        user_id=current_user.id,
        resource_id=str(strategy.id),
    )
    return strategy


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)
    return strategy


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: uuid.UUID,
    data: StrategyUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(strategy, key, value)
    await db.flush()
    await db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(strategy_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)
    await db.delete(strategy)


@router.post("/{strategy_id}/start")
async def start_strategy(strategy_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)

    # Live broker execution is not implemented yet. Do not expose a route that
    # can report a strategy as live while the engine only evaluates signals.
    if not strategy.is_paper:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Live execution is not enabled yet. Use paper mode until broker execution is implemented.",
        )

    strategy.status = StrategyStatus.ACTIVE
    mode = "paper"
    try:
        from app.tasks.strategy_tasks import run_strategy_task

        run_strategy_task.delay(str(strategy.id), mode)
    except Exception:
        from strategies.engine import StrategyEngine

        engine = StrategyEngine()
        engine.execute_strategy(
            strategy.strategy_type.value,
            strategy.symbol,
            strategy.parameters or {},
            mode,
        )
    return {"message": "Strategy started", "strategy_id": str(strategy.id)}


@router.post("/{strategy_id}/execute")
async def execute_strategy_signal(
    strategy_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Queue one deterministic paper execution from the latest strategy signal."""
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)

    if not strategy.is_paper:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Live strategy execution is not enabled yet; use paper mode.",
        )

    portfolio = await db.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    if portfolio.status is not PortfolioStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Strategy execution requires an active portfolio",
        )

    try:
        from app.tasks.strategy_tasks import execute_strategy_signal_task
        task = execute_strategy_signal_task.delay(str(strategy.id), str(portfolio.id))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Strategy execution queue is unavailable",
        ) from exc

    await log_audit(
        db,
        action="strategy.signal_execution_queued",
        user_id=current_user.id,
        resource_id=str(strategy.id),
        details={"portfolio_id": str(portfolio.id), "task_id": task.id},
    )
    return {
        "status": "queued",
        "strategy_id": str(strategy.id),
        "portfolio_id": str(portfolio.id),
        "task_id": task.id,
    }


@router.post("/{strategy_id}/stop")
async def stop_strategy(strategy_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    strategy = await _get_user_strategy(db, strategy_id, current_user.id)
    strategy.status = StrategyStatus.STOPPED
    return {"message": "Strategy stopped"}


async def _get_user_strategy(db, strategy_id: uuid.UUID, user_id: uuid.UUID) -> Strategy:
    result = await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return strategy
