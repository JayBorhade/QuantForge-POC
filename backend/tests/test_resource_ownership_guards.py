"""Regression tests for tenant-scoped resource lookups.

These tests are deliberately explicit about both the resource identifier and
owner identifier. They are SQL-shape tests, not substitutes for PostgreSQL
integration tests or end-to-end two-account API tests.
"""
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.routes.portfolios import _get_portfolio
from app.api.routes.strategies import _get_user_strategy
from app.api.routes.deployments import _get_deployment
from app.api.routes.risk import _get_portfolio as _get_risk_portfolio


class ResourceOwnershipGuardTests(unittest.IsolatedAsyncioTestCase):
    async def _assert_not_found_and_scoped(self, lookup, table_name):
        resource_id = uuid.uuid4()
        owner_id = uuid.uuid4()
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute.return_value = result

        with self.assertRaises(HTTPException) as raised:
            await lookup(db, resource_id, owner_id)

        self.assertEqual(raised.exception.status_code, 404)
        statement = db.execute.await_args.args[0]
        compiled = statement.compile()
        normalized_sql = " ".join(str(compiled).lower().split())
        self.assertIn(f"from {table_name}", normalized_sql)

        # Confirm both tenant owner and requested resource are actual bound
        # values, rather than merely checking that a column name appears.
        predicates = " ".join(normalized_sql.split(" where ", 1)[1:])
        self.assertIn("user_id", predicates)
        self.assertIn("id", predicates)
        bound_values = list(compiled.params.values())
        self.assertIn(resource_id, bound_values)
        self.assertIn(owner_id, bound_values)

    async def test_portfolio_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_portfolio, "portfolios")

    async def test_strategy_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_user_strategy, "strategies")

    async def test_deployment_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_deployment, "deployments")

    async def test_risk_portfolio_lookup_is_owner_scoped_and_hides_foreign_resource(self):
        await self._assert_not_found_and_scoped(_get_risk_portfolio, "portfolios")


if __name__ == "__main__":
    unittest.main()
