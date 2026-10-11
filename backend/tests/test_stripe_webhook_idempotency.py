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
        db.flush = AsyncMock(side_effect=IntegrityError("insert", {}, SimpleNamespace(sqlstate="23505")))
        event = {"id": "evt_race", "type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            response = asyncio.run(stripe_webhook(request(), db))

        self.assertEqual(response, {"received": True, "duplicate": True})
        db.rollback.assert_awaited_once()


    def test_non_duplicate_integrity_error_is_not_acknowledged(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        db.flush = AsyncMock(side_effect=IntegrityError("insert", {}, SimpleNamespace(sqlstate="23502")))
        event = {"id": "evt_invalid", "type": "customer.updated", "data": {}}

        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ):
            with self.assertRaises(IntegrityError):
                asyncio.run(stripe_webhook(request(), db))

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


    def test_unpaid_checkout_does_not_activate_subscription(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        event = {
            "id": "evt_unpaid_checkout",
            "type": "checkout.session.completed",
            "data": {
                "metadata": {"user_id": "00000000-0000-0000-0000-000000000001", "plan": "pro"},
                "customer": "cus_test",
                "subscription": "sub_test",
                "payment_status": "unpaid",
            },
        }
        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ), patch("app.api.routes.billing._update_subscription", new=AsyncMock()) as update:
            response = asyncio.run(stripe_webhook(request(), db))
        self.assertEqual(response, {"received": True})
        update.assert_not_awaited()

    def test_paid_checkout_activates_only_known_plan(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=Result(None))
        event = {
            "id": "evt_paid_checkout",
            "type": "checkout.session.completed",
            "data": {
                "metadata": {"user_id": "00000000-0000-0000-0000-000000000001", "plan": "pro"},
                "customer": "cus_test",
                "subscription": "sub_test",
                "payment_status": "paid",
            },
        }
        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ), patch("app.api.routes.billing._update_subscription", new=AsyncMock()) as update:
            response = asyncio.run(stripe_webhook(request(), db))
        self.assertEqual(response, {"received": True})
        update.assert_awaited_once()
        self.assertEqual(update.await_args.args[2], "pro")

    def test_unknown_subscription_status_fails_closed(self):
        db = AsyncMock()
        subscription = SimpleNamespace()
        db.execute = AsyncMock(side_effect=[Result(None), Result(subscription)])
        event = {
            "id": "evt_unknown_status",
            "type": "customer.subscription.updated",
            "data": {
                "customer": "cus_test",
                "status": "future_unknown_state",
                "id": "sub_test",
                "items": {"data": [{"price": {"id": "price_pro"}}]},
            },
        }
        with patch("app.api.routes.billing.stripe_enabled", return_value=True), patch(
            "app.api.routes.billing.handle_webhook_event", return_value=event
        ), patch("app.api.routes.billing.map_stripe_plan", return_value="pro"):
            response = asyncio.run(stripe_webhook(request(), db))
        self.assertEqual(response, {"received": True})
        self.assertEqual(subscription.status.value, "expired")


if __name__ == "__main__":
    unittest.main()
