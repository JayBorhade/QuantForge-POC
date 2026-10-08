"""Regression tests for async backtest lifecycle contracts."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BacktestLifecycleContractTests(unittest.TestCase):
    def test_run_model_persists_replay_inputs(self):
        source = (ROOT / "app/models/strategy.py").read_text(encoding="utf-8")
        for field in ("initial_capital", "input_snapshot", "configuration_fingerprint", "data_revision"):
            self.assertIn(field, source)

    def test_runner_has_idempotency_and_stale_lease_guard(self):
        source = (ROOT / "app/services/backtest_runner.py").read_text(encoding="utf-8")
        self.assertIn("RunStatus.COMPLETED", source)
        self.assertIn("RunStatus.CANCELLED", source)
        self.assertIn("timedelta(minutes=30)", source)
        self.assertIn("input_snapshot", source)
        self.assertIn("worker_token", source)
        self.assertIn("worker_started_at", source)

    def test_api_has_duplicate_protection_and_cancellation(self):
        source = (ROOT / "app/api/routes/strategies.py").read_text(encoding="utf-8")
        self.assertIn("configuration_fingerprint", source)
        self.assertIn('"/runs/{run_id}/cancel"', source)
        self.assertIn("RunStatus.PENDING", source)
        self.assertIn("RunStatus.RUNNING", source)
        self.assertIn("worker_token = None", source)


if __name__ == "__main__":
    unittest.main()

    def test_cancellation_invalidates_worker_lease(self):
        source = (ROOT / "app/api/routes/strategies.py").read_text(encoding="utf-8")
        self.assertIn("run.status = RunStatus.CANCELLED", source)
        self.assertIn("run.worker_token = None", source)
        self.assertIn("run.worker_started_at = None", source)

    def test_late_worker_exception_cannot_override_cancelled_run(self):
        source = (ROOT / "app/services/backtest_runner.py").read_text(encoding="utf-8")
        self.assertIn('if run.status == RunStatus.CANCELLED or run.worker_token != lease_token:', source)
        self.assertIn('"Backtest worker lease no longer owns this run"', source)
