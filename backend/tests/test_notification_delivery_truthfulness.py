"""Notification task results must reflect actual email delivery."""

import unittest
from unittest.mock import patch


class NotificationDeliveryTests(unittest.TestCase):
    def test_email_task_does_not_claim_delivery_when_smtp_unavailable(self):
        from app.tasks.notification_tasks import send_email_notification

        with patch("app.tasks.notification_tasks._user_email", return_value="user@example.com"), patch(
            "app.services.email.send_email", return_value=False
        ):
            result = send_email_notification.run("00000000-0000-0000-0000-000000000001", "Notice", "body")

        self.assertFalse(result["sent"])

    def test_trade_alert_rejects_invalid_side(self):
        from app.tasks.notification_tasks import send_trade_alert

        with patch("app.tasks.notification_tasks._user_email", return_value="user@example.com"):
            result = send_trade_alert.run(
                "00000000-0000-0000-0000-000000000001",
                {"symbol": "AAPL", "side": "short", "pnl": 12},
            )

        self.assertFalse(result["alert_sent"])
        self.assertEqual(result["reason"], "invalid_trade_data")


if __name__ == "__main__":
    unittest.main()
