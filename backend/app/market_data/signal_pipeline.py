"""Provider-neutral market-data to strategy-signal pipeline contracts.

This layer deliberately stops before order submission. Strategy evaluators can consume
normalized quotes and emit signals; execution remains behind the existing paper-only
orchestration boundary.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable

from app.market_data.types import Quote


class SignalAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class SignalEvent:
    strategy_id: str
    symbol: str
    action: SignalAction
    price: str
    event_time: datetime
    source: str
    sequence: int | None


SignalEvaluator = Callable[[Quote], SignalAction | str | None]


class MarketSignalPipeline:
    """Deduplicates quote events before passing them to a strategy evaluator."""

    def __init__(self) -> None:
        self._last_sequence: dict[tuple[str, str], int] = {}

    def evaluate(
        self,
        *,
        strategy_id: str,
        quote: Quote,
        evaluator: SignalEvaluator,
    ) -> SignalEvent | None:
        key = (str(strategy_id), quote.symbol)
        if quote.sequence is not None:
            previous = self._last_sequence.get(key)
            if previous is not None and quote.sequence <= previous:
                return None
            self._last_sequence[key] = quote.sequence

        action = evaluator(quote)
        if action is None:
            return None
        try:
            normalized = SignalAction(action)
        except ValueError as exc:
            raise ValueError("Strategy evaluator returned an invalid signal") from exc

        return SignalEvent(
            strategy_id=str(strategy_id),
            symbol=quote.symbol,
            action=normalized,
            price=str(quote.last_price),
            event_time=quote.event_time,
            source=quote.source,
            sequence=quote.sequence,
        )
