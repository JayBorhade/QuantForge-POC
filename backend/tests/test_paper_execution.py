"""Paper execution idempotency tests."""

import asyncio
import unittest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.execution_fill import ExecutionFill
from app.models.order import OrderStatus
from app.services.paper_execution import PaperExecutionService


class PaperExecutionReplayTests(unittest.TestCase):
    def test_filled_order_replay_returns_existing_fill_without_regression(self):
        order = MagicMock(
            id=uuid.uuid4(),
            status=OrderStatus.FILLED,
            broker_order_id="paper-client-1",
        )
        fill = ExecutionFill(
            order_id=order.id,
            broker_fill_id="paper-fill:client-1",
            quantity=Decimal("2"),
            price=Decimal("100"),
            fee=Decimal("0"),
        )
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: fill))
        broker = MagicMock()
        portfolio = MagicMock()

        with patch(
            "app.services.paper_execution.ExecutionService.submit",
            new=AsyncMock(return_value=order),
        ) as submit:
            result_order, result_fill = asyncio.run(
                PaperExecutionService(db, broker).execute(
                    portfolio=portfolio,
                    symbol="RELIANCE",
                    side=order.side if hasattr(order, "side") else MagicMock(),
                    quantity=Decimal("2"),
                    client_order_id="client-1",
                    fill_price=Decimal("100"),
                )
            )

        self.assertIs(result_order, order)
        self.assertIs(result_fill, fill)
        self.assertEqual(order.status, OrderStatus.FILLED)
        submit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
