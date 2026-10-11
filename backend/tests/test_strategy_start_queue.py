"""Regression tests for truthful strategy-start queue failure handling."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.routes.strategies import start_strategy
from app.models.strategy import StrategyStatus


class StrategyStartQueueTests(unittest.TestCase):
    def setUp(self):
        self.strategy_id = uuid4()
        self.current_user = SimpleNamespace(id=uuid4())
        self.strategy = SimpleNamespace(
            id=self.strategy_id,
            is_paper=True,
            status=StrategyStatus.DRAFT,
            strategy_type=SimpleNamespace(value="ema_crossover"),
            symbol="AAPL",
            parameters={},
        )
        self.db = MagicMock()

    def invoke(self):
        return asyncio.run(
            start_strategy(
                self.strategy_id,
                self.current_user,
                self.db,
            )
        )

    def test_queue_failure_returns_503_and_restores_status(self):
        with patch(
            "app.api.routes.strategies._get_user_strategy",
            new=AsyncMock(return_value=self.strategy),
        ), patch(
            "app.tasks.strategy_tasks.run_strategy_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ), patch(
            "strategies.engine.StrategyEngine.execute_strategy"
        ) as signal_only_fallback:
            with self.assertRaises(HTTPException) as raised:
                self.invoke()

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(self.strategy.status, StrategyStatus.DRAFT)
        signal_only_fallback.assert_not_called()

    def test_successful_enqueue_activates_strategy(self):
        with patch(
            "app.api.routes.strategies._get_user_strategy",
            new=AsyncMock(return_value=self.strategy),
        ), patch(
            "app.tasks.strategy_tasks.run_strategy_task.delay",
        ) as enqueue:
            result = self.invoke()

        enqueue.assert_called_once_with(str(self.strategy_id), "paper")
        self.assertEqual(self.strategy.status, StrategyStatus.ACTIVE)
        self.assertEqual(result["message"], "Strategy started")

    def test_live_strategy_is_rejected_before_queueing(self):
        self.strategy.is_paper = False
        with patch(
            "app.api.routes.strategies._get_user_strategy",
            new=AsyncMock(return_value=self.strategy),
        ), patch(
            "app.tasks.strategy_tasks.run_strategy_task.delay",
        ) as enqueue:
            with self.assertRaises(HTTPException) as raised:
                self.invoke()

        self.assertEqual(raised.exception.status_code, 409)
        enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
