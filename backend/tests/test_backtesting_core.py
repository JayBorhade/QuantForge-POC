"""Regression tests for the provider-neutral backtesting core."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.backtesting.simulator import BacktestSimulator
from app.backtesting.types import BacktestBar, BacktestConfig

class BacktestingCoreTests(unittest.TestCase):
    def setUp(self):
        self.config=BacktestConfig(initial_capital=Decimal("1000"),position_size_pct=Decimal("0.10"),transaction_cost_pct=Decimal("0"),slippage_pct=Decimal("0"))
    def bars(self, rows):
        return [BacktestBar(datetime(2026,1,i+1,tzinfo=timezone.utc),*(Decimal(str(v)) for v in row)) for i,row in enumerate(rows)]
    def test_signal_executes_on_next_open(self):
        result=BacktestSimulator().run(self.bars([(100,101,99,100),(110,112,109,111)]),[{"signal":"buy"},{"signal":"hold"}],self.config)
        self.assertEqual(result.total_trades,1); self.assertEqual(result.trades[0].entry_price,Decimal("110")); self.assertGreater(result.final_capital,Decimal("1000"))
    def test_costs_reduce_returns(self):
        bars=self.bars([(100,101,99,100),(110,112,109,111)])
        free=BacktestSimulator().run(bars,[{"signal":"buy"},{"signal":"hold"}],self.config)
        costly=BacktestSimulator().run(bars,[{"signal":"buy"},{"signal":"hold"}],BacktestConfig(initial_capital=Decimal("1000"),position_size_pct=Decimal("0.10"),transaction_cost_pct=Decimal("0.01"),slippage_pct=Decimal("0.01")))
        self.assertGreater(free.final_capital,costly.final_capital)
    def test_stop_loss_gap(self):
        result=BacktestSimulator().run(self.bars([(100,101,99,100),(100,101,99,100),(90,92,88,91)]),[{"signal":"buy","stop_loss":95},{"signal":"hold","stop_loss":95},{"signal":"hold","stop_loss":95}],self.config)
        self.assertEqual(result.trades[0].reason,"stop_loss_gap")
    def test_invalid_ohlc(self):
        with self.assertRaisesRegex(ValueError,"OHLC"): BacktestSimulator().run(self.bars([(100,99,98,100)]),[{"signal":"hold"}],self.config)
    def test_mismatched_inputs(self):
        with self.assertRaisesRegex(ValueError,"equal length"): BacktestSimulator().run(self.bars([(100,101,99,100)]),[],self.config)
if __name__=="__main__": unittest.main()
