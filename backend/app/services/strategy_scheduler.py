"""Production scheduler for paper strategy signal execution.

Celery Beat invokes the dispatcher once per minute. Strategy-specific cron
expressions remain in the database so users can change schedules without
restarting workers.
"""

import logging
from datetime import datetime, timedelta, timezone

from croniter import croniter
from sqlalchemy import select, text

from app.db.sync_session import get_sync_db
from app.models.portfolio import Portfolio, PortfolioStatus
from app.models.strategy import Strategy, StrategyStatus

logger = logging.getLogger(__name__)

SCHEDULER_LOCK_KEY = "quantforge.strategy.scheduler"
MAX_CATCH_UP = timedelta(minutes=2)


def validate_cron_expression(expression: str) -> str:
    """Validate and normalize a five-field cron expression."""
    expression = expression.strip()
    if not expression:
        raise ValueError("schedule_cron cannot be empty")
    if len(expression) > 64:
        raise ValueError("schedule_cron must be at most 64 characters")
    try:
        croniter(expression, datetime.now(timezone.utc))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid schedule_cron expression: {expression}") from exc
    return expression


def _scheduled_occurrence(expression: str, now: datetime) -> datetime:
    """Return the latest cron occurrence at or before the current minute."""
    base = now.replace(second=0, microsecond=0) + timedelta(seconds=1)
    occurrence = croniter(expression, base).get_prev(datetime)
    if occurrence.tzinfo is None:
        occurrence = occurrence.replace(tzinfo=timezone.utc)
    return occurrence.astimezone(timezone.utc)


def dispatch_due_strategies(now: datetime | None = None) -> dict:
    """Dispatch each due paper strategy exactly once per scheduled occurrence."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    dispatched = 0
    skipped = 0
    invalid = 0

    with get_sync_db() as db:
        dialect = db.bind.dialect.name if db.bind is not None else ""
        if dialect == "postgresql":
            acquired = db.execute(
                text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
                {"key": SCHEDULER_LOCK_KEY},
            ).scalar()
            if not acquired:
                return {
                    "dispatched": 0,
                    "skipped": 0,
                    "invalid": 0,
                    "locked": True,
                }

        rows = db.execute(
            select(Strategy, Portfolio)
            .join(Portfolio, Strategy.schedule_portfolio_id == Portfolio.id)
            .where(
                Strategy.status == StrategyStatus.ACTIVE,
                Strategy.is_paper.is_(True),
                Strategy.schedule_cron.is_not(None),
                Strategy.schedule_portfolio_id.is_not(None),
                Portfolio.status == PortfolioStatus.ACTIVE,
            )
            .order_by(Strategy.created_at.asc())
        ).all()

        from app.tasks.strategy_tasks import execute_strategy_signal_task

        for strategy, _portfolio in rows:
            try:
                expression = validate_cron_expression(strategy.schedule_cron or "")
                occurrence = _scheduled_occurrence(expression, now)
            except ValueError:
                invalid += 1
                logger.error(
                    "Invalid schedule for strategy %s: %s",
                    strategy.id,
                    strategy.schedule_cron,
                )
                continue

            if occurrence > now or now - occurrence > MAX_CATCH_UP:
                skipped += 1
                continue

            if strategy.last_scheduled_at is not None:
                previous = strategy.last_scheduled_at
                if previous.tzinfo is None:
                    previous = previous.replace(tzinfo=timezone.utc)
                if previous >= occurrence:
                    skipped += 1
                    continue

            task_id = (
                f"scheduled-strategy:{strategy.id}:"
                f"{occurrence.strftime('%Y%m%dT%H%M')}"
            )
            execute_strategy_signal_task.apply_async(
                args=[str(strategy.id), str(strategy.schedule_portfolio_id)],
                task_id=task_id,
                expires=55,
            )
            strategy.last_scheduled_at = occurrence
            dispatched += 1

        db.commit()

    return {
        "dispatched": dispatched,
        "skipped": skipped,
        "invalid": invalid,
        "locked": False,
    }
