"""Legacy engine must not report success without executing a strategy."""

import unittest
from strategies.engine import StrategyEngine


class StrategyEngineHonestyTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_noop_engine_fails_explicitly(self):
        with self.assertRaisesRegex(RuntimeError, "canonical paper strategy runtime"):
            await StrategyEngine().run("strategy-id", "paper")


if __name__ == "__main__":
    unittest.main()
