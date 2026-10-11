"""Regression tests for strategy scheduling API schema contracts."""

import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.models.strategy import StrategyType
from app.schemas.strategy import StrategyCreate, StrategyUpdate


def create_payload(**overrides):
    payload = {
        "name": "Scheduled EMA",
        "strategy_type": StrategyType.EMA_CROSSOVER,
        "symbol": "AAPL",
    }
    payload.update(overrides)
    return payload


class StrategyScheduleSchemaTests(unittest.TestCase):
    def test_unscheduled_strategy_defaults_to_no_schedule(self):
        strategy = StrategyCreate(**create_payload())
        self.assertIsNone(strategy.schedule_cron)
        self.assertIsNone(strategy.schedule_portfolio_id)

    def test_valid_paper_schedule_accepts_portfolio_id(self):
        portfolio_id = uuid4()
        strategy = StrategyCreate(**create_payload(
            schedule_cron="*/5 * * * *",
            schedule_portfolio_id=portfolio_id,
        ))
        self.assertEqual(strategy.schedule_portfolio_id, portfolio_id)
        self.assertEqual(strategy.schedule_cron, "*/5 * * * *")

    def test_schedule_requires_portfolio(self):
        with self.assertRaises(ValidationError):
            StrategyCreate(**create_payload(schedule_cron="*/5 * * * *"))

    def test_portfolio_requires_schedule(self):
        with self.assertRaises(ValidationError):
            StrategyCreate(**create_payload(schedule_portfolio_id=uuid4()))

    def test_live_strategy_cannot_be_scheduled(self):
        with self.assertRaises(ValidationError):
            StrategyCreate(**create_payload(
                is_paper=False,
                schedule_cron="*/5 * * * *",
                schedule_portfolio_id=uuid4(),
            ))

    def test_invalid_cron_is_rejected_on_create_and_update(self):
        with self.assertRaises(ValidationError):
            StrategyCreate(**create_payload(
                schedule_cron="not a cron",
                schedule_portfolio_id=uuid4(),
            ))
        with self.assertRaises(ValidationError):
            StrategyUpdate(schedule_cron="not a cron")

    def test_update_schema_accepts_schedule_portfolio_id(self):
        portfolio_id = uuid4()
        update = StrategyUpdate(schedule_portfolio_id=portfolio_id)
        self.assertEqual(update.schedule_portfolio_id, portfolio_id)
        self.assertIn("schedule_portfolio_id", update.model_dump(exclude_unset=True))


if __name__ == "__main__":
    unittest.main()
