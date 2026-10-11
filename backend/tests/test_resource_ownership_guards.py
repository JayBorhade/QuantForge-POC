"""Regression tests for tenant-scoped portfolio and strategy lookups."""
import unittest
import uuid
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.api.routes.portfolios import _get_portfolio
from app.api.routes.strategies import _get_user_strategy


class ResourceOwnershipGuardTests(unittest.IsolatedAsyncioTestCase):
    async def _assert_not_found_and_scoped(self, lookup, model_name):
        resource_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        db = AsyncMock()
        result = AsyncMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        with self.assertRaises(HTTPException) as raised:
            await lookup(db, resource_id, owner_id)

        self.assertEqual(raised.exception.status_code, 404)
        statement = db.execute.await_args.args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": False}))
        normalized = " ".join(compiled.lower().split())
        self.assertIn(f"from {model_name}", normalized)
        # The resource lookup must constrain both the requested identifier and
        # the authenticated owner's identifier, preventing cross-tenant reads.
        self.assertIn("user_id", normalized)
        self.assertIn(" and ", normalized)

    async def test_portfolio_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_portfolio, "portfolios")

    async def test_strategy_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_user_strategy, "strategies")


if __name__ == "__main__":
    unittest.main()
