"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { strategyApi } from "@/lib/api";

interface Strategy {
  id: string;
  name: string;
  symbol: string;
}

type BacktestResult = Record<string, unknown>;

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState("");
  const [startDate, setStartDate] = useState("2025-01-01");
  const [endDate, setEndDate] = useState("2026-01-01");
  const [capital, setCapital] = useState("100000");
  const [running, setRunning] = useState(false);
  const [loadingStrategies, setLoadingStrategies] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<BacktestResult | null>(null);

  useEffect(() => {
    let mounted = true;
    strategyApi.list()
      .then((response) => {
        const items = Array.isArray(response.data) ? response.data : [];
        if (mounted) {
          setStrategies(items);
          if (items[0]) setStrategyId(items[0].id);
        }
      })
      .catch(() => {
        if (mounted) setError("Strategies could not be loaded. Check the API connection and retry.");
      })
      .finally(() => { if (mounted) setLoadingStrategies(false); });
    return () => { mounted = false; };
  }, []);

  const pollRun = async (runId: string, attempts = 30) => {
    for (let attempt = 0; attempt < attempts; attempt++) {
      const { data } = await strategyApi.getRun(runId);
      if (data.status === "completed" || data.status === "failed") {
        setResult(data);
        return;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
    }
    setResult({ status: "timeout" });
  };

  const runBacktest = async () => {
    if (running) return;
    setError("");
    const start = new Date(startDate);
    const end = new Date(endDate);
    const initialCapital = Number(capital);
    if (!strategyId) {
      setError("Select a strategy before starting a backtest.");
      return;
    }
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || end <= start) {
      setError("Choose a valid date range where the end date is after the start date.");
      return;
    }
    if (!Number.isFinite(initialCapital) || initialCapital <= 0) {
      setError("Initial capital must be a positive number.");
      return;
    }

    setRunning(true);
    setResult(null);
    try {
      const { data } = await strategyApi.backtest({
        strategy_id: strategyId,
        start_date: start.toISOString(),
        end_date: end.toISOString(),
        initial_capital: initialCapital,
      });
      if (data.run_id) await pollRun(data.run_id);
      else setResult(data);
    } catch {
      setError("The backtest could not be completed. Check the API connection and strategy configuration.");
    } finally {
      setRunning(false);
    }
  };

  const equity = (result?.equity_curve as Array<{ index: number; value: number }>) || [];
  const trades = (result?.trade_history as Array<{ pnl: number; return_pct: number }>) || [];
  const hasResults = Boolean(result && result.status !== "failed" && result.status !== "timeout" &&
    (result.sharpe_ratio != null || result.total_return != null || equity.length > 0 || trades.length > 0));
  const resultError = result?.status === "timeout"
    ? "The backtest is still running. Check the run again later."
    : result?.status === "failed"
      ? "The backtest failed. Review the strategy configuration and try again."
      : "";

  return (
    <div>
      <DashboardHeader title="Backtesting Engine" subtitle="Historical simulation with performance metrics" />
      {error && <p className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert">{error}</p>}
      {resultError && <p className="mb-4 rounded-lg border border-amber-500/30 p-3 text-sm text-amber-600" role="status">{resultError}</p>}
      <Card className="mb-6 max-w-2xl p-6">
        <form onSubmit={(event) => { event.preventDefault(); void runBacktest(); }}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="backtest-strategy" className="text-sm text-muted-foreground">Strategy</label>
              <select id="backtest-strategy" className="mt-1 flex h-10 w-full rounded-lg border border-border bg-secondary/50 px-3 text-sm" value={strategyId} onChange={(event) => setStrategyId(event.target.value)} disabled={loadingStrategies || !strategies.length}>
                {strategies.map((strategy) => <option key={strategy.id} value={strategy.id}>{strategy.name} ({strategy.symbol})</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="backtest-capital" className="text-sm text-muted-foreground">Initial Capital</label>
              <Input id="backtest-capital" name="initial-capital" type="number" min="0.01" step="any" value={capital} onChange={(event) => setCapital(event.target.value)} className="mt-1" required />
            </div>
            <div>
              <label htmlFor="backtest-start" className="text-sm text-muted-foreground">Start Date</label>
              <Input id="backtest-start" name="start-date" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="mt-1" required />
            </div>
            <div>
              <label htmlFor="backtest-end" className="text-sm text-muted-foreground">End Date</label>
              <Input id="backtest-end" name="end-date" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="mt-1" required />
            </div>
          </div>
          {loadingStrategies && <p className="mt-3 text-sm text-muted-foreground" role="status">Loading strategies…</p>}
          {!loadingStrategies && strategies.length === 0 && !error && <p className="mt-3 text-sm text-muted-foreground">Create a strategy before running a backtest.</p>}
          <Button type="submit" className="mt-4" disabled={running || loadingStrategies || !strategyId}>
            {running ? "Running backtest…" : "Run Backtest"}
          </Button>
        </form>
      </Card>

      {running && <p className="mb-4 text-sm text-muted-foreground" role="status" aria-live="polite">Backtest running. Waiting for the server result…</p>}

      {hasResults && result && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Sharpe Ratio", value: result.sharpe_ratio },
              { label: "Max Drawdown", value: result.max_drawdown == null ? null : `${result.max_drawdown}%` },
              { label: "Total Return", value: result.total_return == null ? null : `${result.total_return}%` },
              { label: "Win Rate", value: result.win_rate == null ? null : `${result.win_rate}%` },
            ].map((metric) => (
              <Card key={metric.label} className="p-4 text-center">
                <p className="text-xs text-muted-foreground">{metric.label}</p>
                <p className="mt-1 text-xl font-bold">{metric.value == null ? "—" : String(metric.value)}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <h3 className="mb-4 font-semibold">Equity Curve</h3>
              {equity.length ? <ResponsiveContainer width="100%" height={220}><AreaChart data={equity}><XAxis dataKey="index" hide /><YAxis hide /><Tooltip /><Area type="monotone" dataKey="value" stroke="#3b82f6" fill="#3b82f640" /></AreaChart></ResponsiveContainer> : <p className="text-sm text-muted-foreground">No equity curve was returned for this run.</p>}
            </Card>
            <Card className="p-6">
              <h3 className="mb-4 font-semibold">Trade PnL</h3>
              {trades.length ? <ResponsiveContainer width="100%" height={220}><BarChart data={trades}><XAxis hide /><YAxis hide /><Tooltip /><Bar dataKey="pnl" fill="#10b981" /></BarChart></ResponsiveContainer> : <p className="text-sm text-muted-foreground">No trade history was returned for this run.</p>}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
