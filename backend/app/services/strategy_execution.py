"""Strategy signal evaluation and paper execution orchestration."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import NAMESPACE_URL, uuid5

from app.models.order import OrderSide
from app.models.portfolio import Portfolio
from app.models.strategy import Strategy
from app.services.paper_execution import PaperExecutionService
from strategies.base import Signal


class StrategyExecutionError(ValueError):
    """Raised when a strategy signal cannot be safely executed."""


@dataclass(frozen=True)
class StrategyExecutionIntent:
    signal: Signal
    symbol: str
    price: Decimal
    quantity: Decimal
    client_order_id: str
    signal_at: str


def build_execution_intent(
    *,
    strategy: Strategy,
    portfolio: Portfolio,
    signal: str | Signal,
    price: Decimal | str | float,
    signal_at: datetime | str,
) -> StrategyExecutionIntent | None:
    """Convert one strategy signal into a deterministic paper-order intent.

    HOLD signals and SELL signals without an existing long position are no-ops.
    BUY signals use the configured portfolio allocation; SELL closes the
    current long position so a strategy reversal cannot leave a residual lot.
    """
    try:
        normalized_signal = Signal(signal)
        market_price = Decimal(str(price))
    except (ValueError, InvalidOperation) as exc:
        raise StrategyExecutionError("Strategy produced an invalid signal or price") from exc

    if market_price <= 0:
        raise StrategyExecutionError("Strategy execution price must be positive")

    if normalized_signal is Signal.HOLD:
        return None

    signal_at_text = signal_at.isoformat() if isinstance(signal_at, datetime) else str(signal_at)
    risk_fraction = Decimal(str((strategy.parameters or {}).get("position_size_pct", "0.10")))
    if risk_fraction <= 0 or risk_fraction > 1:
        raise StrategyExecutionError("position_size_pct must be in (0, 1]")

    if normalized_signal is Signal.BUY:
        allocation = portfolio.cash_balance * risk_fraction
        quantity = allocation / market_price
        side = OrderSide.BUY
    else:
        position = next(
            (p for p in portfolio.positions if p.symbol.upper() == strategy.symbol.upper()),
            None,
        )
        if position is None or position.quantity <= 0:
            return None
        quantity = position.quantity
        side = OrderSide.SELL

    if quantity <= 0:
        return None

    intent_key = (
        f"{strategy.id}:{strategy.symbol.upper()}:{normalized_signal.value}:{signal_at_text}"
    )
    client_order_id = f"strategy-{uuid5(NAMESPACE_URL, intent_key)}"

    return StrategyExecutionIntent(
        signal=normalized_signal,
        symbol=strategy.symbol.upper(),
        price=market_price,
        quantity=quantity,
        client_order_id=client_order_id[:64],
        signal_at=signal_at_text,
    )


class StrategyExecutionService:
    """Evaluate the latest strategy signal and execute it in paper mode."""

    async def execute_latest_signal(
        self,
        *,
        db,
        strategy: Strategy,
        portfolio: Portfolio,
        data,
    ):
        if not strategy.is_paper:
            raise StrategyExecutionError(
                "Live strategy execution is not enabled by this orchestration boundary"
            )
        if portfolio.status.value != "active":
            raise StrategyExecutionError("Strategy execution requires an active portfolio")
        if data is None or data.empty:
            raise StrategyExecutionError("Strategy data is empty")

        from strategies.registry import get_strategy

        engine_strategy = get_strategy(
            strategy.strategy_type.value,
            strategy.symbol,
            strategy.parameters or {},
            mode="paper",
        )
        signals = engine_strategy.generate_signals(data)
        if signals.empty or "signal" not in signals.columns:
            raise StrategyExecutionError("Strategy produced no executable signal")

        latest = signals.iloc[-1]
        price = latest.get("close")
        signal_at = latest.get("date", latest.name)
        intent = build_execution_intent(
            strategy=strategy,
            portfolio=portfolio,
            signal=latest.get("signal", Signal.HOLD),
            price=price,
            signal_at=signal_at,
        )
        if intent is None:
            return {"status": "no_action", "reason": "hold_or_no_position"}

        order, fill = await PaperExecutionService(db).execute(
            portfolio=portfolio,
            symbol=intent.symbol,
            side=OrderSide.BUY if intent.signal is Signal.BUY else OrderSide.SELL,
            quantity=intent.quantity,
            client_order_id=intent.client_order_id,
            fill_price=intent.price,
            strategy_id=strategy.id,
        )
        return {
            "status": "executed",
            "signal": intent.signal.value,
            "symbol": intent.symbol,
            "quantity": str(intent.quantity),
            "price": str(intent.price),
            "order_id": str(order.id),
            "fill_id": str(fill.id),
            "client_order_id": intent.client_order_id,
        }
