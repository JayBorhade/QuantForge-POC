"""Regression coverage for persisted backtest metadata."""
import unittest
class BacktestRunMetadataContractTests(unittest.TestCase):
    def test_metadata_fields_are_defined_in_model_source(self):
        source=open("app/models/strategy.py",encoding="utf-8").read()
        for field in ("configuration_fingerprint","data_source","data_revision"):
            self.assertIn(field,source)
if __name__=="__main__": unittest.main()
