"""Deterministic long-only bar-by-bar backtest simulator."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping, Any

from app.backtesting.metrics import max_drawdown, sharpe_ratio, total_return, win_rate
from app.backtesting.types import BacktestBar, BacktestConfig, BacktestResult, BacktestTrade

@dataclass(frozen=True)
class _PendingSignal:
    signal: str
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

class BacktestSimulator:
    """No network/database/broker dependencies; signals execute at next bar open."""
    def run(self, bars: Iterable[BacktestBar], signals: Iterable[Mapping[str, Any]], config: BacktestConfig) -> BacktestResult:
        config.validate()
        rows, signal_rows = list(bars), list(signals)
        if len(rows) != len(signal_rows): raise ValueError("bars and signals must have equal length")
        if not rows: raise ValueError("at least one bar is required")
        for bar in rows: bar.validate()

        cash = config.initial_capital
        position = Decimal("0")
        entry_price = Decimal("0")
        entry_fee = Decimal("0")
        entry_timestamp: datetime | None = None
        stop_loss = take_profit = None
        pending = _PendingSignal("hold")
        trades: list[BacktestTrade] = []
        equity = [{"timestamp": rows[0].timestamp.isoformat(), "value": str(cash)}]

        for bar, raw in zip(rows, signal_rows):
            pending_signal = _PendingSignal(str(raw.get("signal", "hold")).lower(), self._decimal_or_none(raw.get("stop_loss")), self._decimal_or_none(raw.get("take_profit")))
            if position > 0 and pending.signal == "sell":
                cash, trade = self._close(cash, position, entry_price, entry_fee, bar.open * (1-config.slippage_pct), bar.timestamp, entry_timestamp, "signal", config)
                trades.append(trade); position=Decimal("0"); entry_price=entry_fee=Decimal("0"); entry_timestamp=None; stop_loss=take_profit=None
            if pending.signal == "buy" and position == 0:
                fill = bar.open * (1+config.slippage_pct)
                allocation = cash * config.position_size_pct
                quantity = allocation / (fill * (1+config.transaction_cost_pct))
                cost, fee = quantity*fill, quantity*fill*config.transaction_cost_pct
                if quantity > 0 and cost + fee <= cash:
                    cash -= cost + fee; position=quantity; entry_price=fill; entry_fee=fee; entry_timestamp=bar.timestamp
                    stop_loss, take_profit = pending.stop_loss, pending.take_profit
            if position > 0:
                exit_price, reason = self._protective_exit(bar, stop_loss, take_profit, config.slippage_pct)
                if exit_price is not None:
                    cash, trade = self._close(cash, position, entry_price, entry_fee, exit_price, bar.timestamp, entry_timestamp, reason, config)
                    trades.append(trade); position=Decimal("0"); entry_price=entry_fee=Decimal("0"); entry_timestamp=None; stop_loss=take_profit=None
            equity.append({"timestamp": bar.timestamp.isoformat(), "value": str(cash + position*bar.close)})
            pending = pending_signal

        if position > 0:
            last=rows[-1]; exit_price=last.close*(1-config.slippage_pct)
            cash, trade=self._close(cash, position, entry_price, entry_fee, exit_price, last.timestamp, entry_timestamp, "end_of_period", config)
            trades.append(trade); position=Decimal("0"); equity[-1]["value"]=str(cash)

        values=[Decimal(p["value"]) for p in equity]
        wins=sum(1 for t in trades if t.pnl > 0)
        return BacktestResult(config.initial_capital, cash, total_return(config.initial_capital,cash)*100, sharpe_ratio(values), max_drawdown(values)*100, win_rate(wins,len(trades))*100, len(trades), equity, trades)

    @staticmethod
    def _decimal_or_none(value): return None if value is None else Decimal(str(value))

    @staticmethod
    def _protective_exit(bar, stop_loss, take_profit, slippage):
        if stop_loss is not None and bar.open <= stop_loss: return bar.open*(1-slippage), "stop_loss_gap"
        if take_profit is not None and bar.open >= take_profit: return bar.open*(1-slippage), "take_profit_gap"
        if stop_loss is not None and bar.low <= stop_loss: return stop_loss*(1-slippage), "stop_loss"
        if take_profit is not None and bar.high >= take_profit: return take_profit*(1-slippage), "take_profit"
        return None, ""

    @staticmethod
    def _close(cash, position, entry_price, entry_fee, exit_price, exit_timestamp, entry_timestamp, reason, config):
        gross=position*exit_price; exit_fee=gross*config.transaction_cost_pct
        updated_cash=cash+gross-exit_fee
        pnl=(exit_price-entry_price)*position-entry_fee-exit_fee
        return_pct=(exit_price-entry_price)/entry_price*100 if entry_price else Decimal("0")
        return updated_cash, BacktestTrade(entry_timestamp or exit_timestamp, exit_timestamp, entry_price, exit_price, position, pnl, return_pct, reason)
