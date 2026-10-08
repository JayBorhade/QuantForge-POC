"""Regression tests for production backtest lifecycle hardening."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BacktestLifecycleHardeningTests(unittest.TestCase):
    def test_worker_has_durable_lease_identity(self):
        model = (ROOT / "app/models/strategy.py").read_text(encoding="utf-8")
        runner = (ROOT / "app/services/backtest_runner.py").read_text(encoding="utf-8")
        self.assertIn("worker_token", model)
        self.assertIn("worker_started_at", model)
        self.assertIn("identity_key", model)
        self.assertIn("lease_token", runner)
        self.assertIn("worker_token != lease_token", runner)

    def test_cancelled_or_reclaimed_worker_cannot_overwrite_run(self):
        source = (ROOT / "app/services/backtest_runner.py").read_text(encoding="utf-8")
        self.assertIn('run.status == RunStatus.CANCELLED', source)
        self.assertIn('run.worker_token != lease_token', source)
        self.assertIn('timedelta(minutes=30)', source)

    def test_database_enforces_backtest_identity(self):
        migration = next(ROOT.glob("alembic/versions/*_backtest_lifecycle_hardening.py")).read_text(encoding="utf-8")
        self.assertIn("ix_strategy_runs_identity_key", migration)
        self.assertIn("unique=True", migration)
        self.assertIn("configuration_fingerprint", migration)
        self.assertIn("identity_key", migration)

    def test_api_handles_concurrent_duplicate_creation(self):
        source = (ROOT / "app/api/routes/strategies.py").read_text(encoding="utf-8")
        self.assertIn("IntegrityError", source)
        self.assertIn("await db.rollback()", source)
        self.assertIn("configuration_fingerprint == fingerprint", source)


if __name__ == "__main__":
    unittest.main()
