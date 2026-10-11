"""Regression tests for Stripe webhook event idempotency."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.routes.billing import stripe_webhook


class Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


def request():
    return SimpleNamespace(
        body=AsyncMock(return_value=b"verified-payload"),
        headers={"stripe-signature": "valid-signature"},
    )


class StripeWebhookIdempotencyTests(unittest.TestCase):
    def test_new_event_is_recorded_before_processing(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        event = {"id": "evt_unique_1", "type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            response = asyncio.run(stripe_webhook(request(), db))

        self.assertEqual(response, {"received": True})
        db.add.assert_called_once()
        recorded = db.add.call_args.args[0]
        self.assertEqual(recorded.event_id, "evt_unique_1")
        self.assertEqual(recorded.event_type, "customer.updated")
        db.flush.assert_awaited_once()

    def test_duplicate_event_is_acknowledged_without_reprocessing(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result("evt_duplicate"))
        event = {"id": "evt_duplicate", "type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            response = asyncio.run(stripe_webhook(request(), db))

        self.assertEqual(response, {"received": True, "duplicate": True})
        db.add.assert_not_called()
        db.flush.assert_not_awaited()

    def test_concurrent_duplicate_rolls_back_and_acknowledges(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        db.flush = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate key")))
        event = {"id": "evt_race", "type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            response = asyncio.run(stripe_webhook(request(), db))

        self.assertEqual(response, {"received": True, "duplicate": True})
        db.rollback.assert_awaited_once()

    def test_verified_event_without_id_is_rejected(self):
        db = AsyncMock()
        event = {"type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(stripe_webhook(request(), db))

        self.assertEqual(error.exception.status_code, 400)
        db.add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
