"""Canonical fingerprints for reproducible backtest configurations."""
import hashlib
import json
from decimal import Decimal
from typing import Any

def _jsonable(value: Any):
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, dict): return {str(k): _jsonable(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)): return [_jsonable(v) for v in value]
    return value

def configuration_fingerprint(*, strategy_type: str, symbol: str, parameters: dict, config: dict, start_date: str, end_date: str) -> str:
    payload={"strategy_type":strategy_type,"symbol":symbol.upper(),"parameters":_jsonable(parameters),"config":_jsonable(config),"start_date":start_date,"end_date":end_date}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
