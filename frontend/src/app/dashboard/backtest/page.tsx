"use client";

import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [strategyId, setStrategyId] = useState("");
  const [startDate, setStartDate] = useState("2025-01-01");
  const [endDate, setEndDate] = useState("2026-01-01");
  const [capital, setCapital] = useState("100000");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    strategyApi.list().then((r) => {
      setStrategies(r.data);
      if (r.data[0]) setStrategyId(r.data[0].id);
    });
  }, []);

  const pollRun = async (runId: string, attempts = 30) => {
    for (let i = 0; i < attempts; i++) {
      const { data } = await strategyApi.getRun(runId);
      if (data.status === "completed" || data.status === "failed") {
        setResult(data);
        return;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    setResult({ status: "timeout", error_message: "Backtest still running — refresh later" });
  };

  const runBacktest = async () => {
    if (!strategyId) return;
    setRunning(true);
    setResult(null);
    try {
      const { data } = await strategyApi.backtest({
        strategy_id: strategyId,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        initial_capital: parseFloat(capital),
      });
      if (data.run_id) {
        await pollRun(data.run_id);
      } else {
        setResult(data);
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setResult({ status: "failed", error_message: String(detail || "Backtest failed") });
    } finally {
      setRunning(false);
    }
  };

  const equity = (result?.equity_curve as Array<{ index: number; value: number }>) || [];
  const trades = (result?.trade_history as Array<{ pnl: number; return_pct: number }>) || [];

  return (
    <div>
      <DashboardHeader title="Backtesting Engine" subtitle="Historical simulation with institutional metrics" />
      <Card className="p-6 mb-6 max-w-2xl">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm text-muted-foreground">Strategy</label>
            <select
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-secondary/50 px-3 text-sm"
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.symbol})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-muted-foreground">Initial Capital</label>
            <Input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">Start Date</label>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="mt-1" />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">End Date</label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="mt-1" />
          </div>
        </div>
        <Button className="mt-4" onClick={runBacktest} disabled={running || !strategyId}>
          {running ? "Running backtest..." : "Run Backtest"}
        </Button>
      </Card>

      {result && (
        <>
          <div className="grid gap-4 sm:grid-cols-4 mb-6">
            {[
              { label: "Sharpe Ratio", value: result.sharpe_ratio },
              { label: "Max Drawdown", value: `${result.max_drawdown}%` },
              { label: "Total Return", value: `${result.total_return}%` },
              { label: "Win Rate", value: `${result.win_rate}%` },
            ].map((m) => (
              <Card key={m.label} className="p-4 text-center">
                <p className="text-xs text-muted-foreground">{m.label}</p>
                <p className="text-xl font-bold mt-1">{String(m.value ?? "—")}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Equity Curve</h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={equity}>
                  <XAxis dataKey="index" hide />
                  <YAxis hide />
                  <Tooltip />
                  <Area type="monotone" dataKey="value" stroke="#3b82f6" fill="#3b82f640" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
            <Card className="p-6">
              <h3 className="font-semibold mb-4">Trade PnL</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={trades}>
                  <XAxis hide />
                  <YAxis hide />
                  <Tooltip />
                  <Bar dataKey="pnl" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
