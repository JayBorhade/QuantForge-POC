"""Canonical projection from execution fills to portfolio trades."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import ExecutionMode, Order, OrderSide
from app.models.trade import Trade, TradeMode, TradeSide, TradeStatus


class TradeLedgerError(ValueError):
    """Raised when a fill cannot be projected safely into trade history."""


_MODE_MAP = {
    ExecutionMode.PAPER: TradeMode.PAPER,
    ExecutionMode.LIVE: TradeMode.LIVE,
}


class TradeLedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_fill(
        self,
        *,
        order: Order,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        executed_at: datetime,
        entry_cost_before: Decimal,
    ) -> Trade:
        """Project one fill into an auditable trade record.

        BUY fills accumulate into one open trade for the position. SELL fills
        close against the current position cost and create a closed trade.
        Partial exits reduce the open trade without losing historical P&L.
        """
        mode = _MODE_MAP.get(order.mode)
        if mode is None:
            raise TradeLedgerError(f"Unsupported execution mode: {order.mode}")

        if order.side is OrderSide.BUY:
            result = await self.db.execute(
                select(Trade)
                .where(
                    Trade.portfolio_id == order.portfolio_id,
                    Trade.symbol == order.symbol,
                    Trade.strategy_id == order.strategy_id,
                    Trade.side == TradeSide.BUY,
                    Trade.mode == mode,
                    Trade.status == TradeStatus.OPEN,
                )
                .order_by(Trade.created_at.asc())
                .limit(1)
                .with_for_update()
            )
            trade = result.scalar_one_or_none()

            if trade is None:
                trade = Trade(
                    portfolio_id=order.portfolio_id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=TradeSide.BUY,
                    status=TradeStatus.OPEN,
                    mode=mode,
                    quantity=quantity,
                    entry_price=price,
                    fees=fee,
                    broker_order_id=order.broker_order_id,
                    opened_at=executed_at,
                )
                self.db.add(trade)
            else:
                old_qty = trade.quantity
                new_qty = old_qty + quantity
                trade.entry_price = (
                    (old_qty * (trade.entry_price or Decimal("0")) + quantity * price) / new_qty
                )
                trade.quantity = new_qty
                trade.fees += fee
                trade.broker_order_id = order.broker_order_id or trade.broker_order_id
            await self.db.flush()
            return trade

        if entry_cost_before <= 0:
            raise TradeLedgerError("Sell fill requires a positive entry cost")

        remaining = quantity
        last_closed_trade = None
        result = await self.db.execute(
            select(Trade)
            .where(
                Trade.portfolio_id == order.portfolio_id,
                Trade.symbol == order.symbol,
                Trade.strategy_id == order.strategy_id,
                Trade.side == TradeSide.BUY,
                Trade.mode == mode,
                Trade.status == TradeStatus.OPEN,
            )
            .order_by(Trade.created_at.asc())
            .with_for_update()
        )
        open_trades = list(result.scalars().all())

        for trade in open_trades:
            if remaining <= 0:
                break
            close_qty = min(remaining, trade.quantity)
            closed = Trade(
                portfolio_id=order.portfolio_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                side=TradeSide.SELL,
                status=TradeStatus.CLOSED,
                mode=mode,
                quantity=close_qty,
                entry_price=trade.entry_price,
                exit_price=price,
                pnl=(price - (trade.entry_price or entry_cost_before)) * close_qty,
                fees=fee * (close_qty / quantity),
                broker_order_id=order.broker_order_id,
                opened_at=trade.opened_at,
                closed_at=executed_at,
            )
            self.db.add(closed)
            last_closed_trade = closed
            trade.quantity -= close_qty
            trade.fees += fee * (close_qty / quantity)
            if trade.quantity == 0:
                trade.status = TradeStatus.CLOSED
                trade.closed_at = executed_at
            remaining -= close_qty

        if remaining > 0:
            # Preserve an auditable closed trade even when the position
            # predates the Trade ledger.
            self.db.add(
                Trade(
                    portfolio_id=order.portfolio_id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=TradeSide.SELL,
                    status=TradeStatus.CLOSED,
                    mode=mode,
                    quantity=remaining,
                    entry_price=entry_cost_before,
                    exit_price=price,
                    pnl=(price - entry_cost_before) * remaining,
                    fees=fee * (remaining / quantity),
                    broker_order_id=order.broker_order_id,
                    closed_at=executed_at,
                )
            )

        await self.db.flush()
        return last_closed_trade or Trade(
            portfolio_id=order.portfolio_id,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            side=TradeSide.SELL,
            status=TradeStatus.CLOSED,
            mode=mode,
            quantity=remaining,
            entry_price=entry_cost_before,
            exit_price=price,
            pnl=(price - entry_cost_before) * remaining,
            fees=fee,
            broker_order_id=order.broker_order_id,
            closed_at=executed_at,
        )
