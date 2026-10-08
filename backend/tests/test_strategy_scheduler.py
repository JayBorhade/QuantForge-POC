"""Deterministic tests for production strategy scheduling."""
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.services.strategy_scheduler import (
    MAX_CATCH_UP,
    _scheduled_occurrence,
    validate_cron_expression,
)


class StrategySchedulerTests(unittest.TestCase):
    def test_validates_cron_expression(self):
        self.assertEqual(validate_cron_expression("*/5 * * * *"), "*/5 * * * *")

    def test_rejects_invalid_cron_expression(self):
        with self.assertRaises(ValueError):
            validate_cron_expression("not-a-cron")

    def test_finds_current_scheduled_occurrence(self):
        now = datetime(2026, 10, 8, 10, 15, 42, tzinfo=timezone.utc)
        self.assertEqual(
            _scheduled_occurrence("*/5 * * * *", now),
            datetime(2026, 10, 8, 10, 15, tzinfo=timezone.utc),
        )

    def test_old_occurrence_is_not_caught_up_indefinitely(self):
        now = datetime(2026, 10, 8, 10, 15, 42, tzinfo=timezone.utc)
        occurrence = _scheduled_occurrence("0 * * * *", now)
        self.assertGreater(now - occurrence, MAX_CATCH_UP)

    def test_scheduler_state_is_persisted_in_model_and_migration(self):
        root = Path(__file__).resolve().parents[1]
        model = (root / "app/models/strategy.py").read_text(encoding="utf-8")
        migration = next(root.glob("alembic/versions/*_strategy_scheduler.py")).read_text(
            encoding="utf-8"
        )
        self.assertIn("schedule_portfolio_id", model)
        self.assertIn("last_scheduled_at", model)
        self.assertIn("fk_strategies_schedule_portfolio_id", migration)


if __name__ == "__main__":
    unittest.main()
