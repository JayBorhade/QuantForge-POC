"""Regression tests for reproducibility contracts."""
import unittest
from datetime import datetime,timezone
from decimal import Decimal
from app.backtesting.data import validate_historical_bars,HistoricalDataError
from app.backtesting.fingerprint import configuration_fingerprint
from app.backtesting.run_spec import BacktestRunSpec
from app.backtesting.types import BacktestBar

class ReproducibilityTests(unittest.TestCase):
    def test_fingerprint_is_order_independent(self):
        a=dict(strategy_type="ema_crossover",symbol="aapl",parameters={"slow":20,"fast":10},config={"slippage_pct":Decimal(".001")},start_date="2026-01-01",end_date="2026-02-01")
        b=dict(strategy_type="ema_crossover",symbol="AAPL",parameters={"fast":10,"slow":20},config={"slippage_pct":Decimal(".001")},start_date="2026-01-01",end_date="2026-02-01")
        self.assertEqual(configuration_fingerprint(**a),configuration_fingerprint(**b))
    def test_fingerprint_changes_with_execution_config(self):
        common=dict(strategy_type="ema_crossover",symbol="AAPL",parameters={},config={"slippage_pct":"0.001"},start_date="2026-01-01",end_date="2026-02-01")
        self.assertNotEqual(configuration_fingerprint(**common),configuration_fingerprint(**{**common,"config":{"slippage_pct":"0.002"}}))
    def test_historical_bars_must_be_chronological(self):
        bar=lambda day: BacktestBar(datetime(2026,1,day,tzinfo=timezone.utc),Decimal("100"),Decimal("101"),Decimal("99"),Decimal("100"))
        with self.assertRaisesRegex(HistoricalDataError,"chronological"): validate_historical_bars([bar(2),bar(1)],"AAPL","fixture","v1")
    def test_run_spec_fingerprint_is_stable(self):
        spec=BacktestRunSpec("ema_crossover","AAPL",{"fast":10,"slow":20},Decimal("1000"),Decimal(".1"),Decimal("0"),Decimal("0"),datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,2,1,tzinfo=timezone.utc),"fixture","v1")
        self.assertEqual(spec.fingerprint(),spec.fingerprint())
if __name__=="__main__": unittest.main()
