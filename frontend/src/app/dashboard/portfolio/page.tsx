"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { portfolioApi } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface Portfolio {
  id: string;
  name: string;
  total_value: number;
  cash_balance: number;
  daily_pnl: number;
  total_pnl: number;
  win_rate: number;
}

interface RecentTrade {
  symbol?: unknown;
  side?: unknown;
  pnl?: unknown;
  status?: unknown;
}

interface PortfolioAnalytics {
  allocation?: { equity?: number; cash?: number };
  recent_trades?: RecentTrade[];
}

const COLORS = ["#3b82f6", "#10b981"];

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [analytics, setAnalytics] = useState<PortfolioAnalytics | null>(null);
  const [performance, setPerformance] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const response = await portfolioApi.list();
      const items = Array.isArray(response.data) ? response.data : [];
      setPortfolios(items);
      if (items[0]) {
        const [analyticsResponse, performanceResponse] = await Promise.all([
          portfolioApi.analytics(items[0].id),
          portfolioApi.performance(items[0].id, 30),
        ]);
        setAnalytics(analyticsResponse.data);
        setPerformance(performanceResponse.data);
      } else {
        setAnalytics(null);
        setPerformance(null);
      }
      setError("");
    } catch {
      setError("Portfolio data could not be loaded. Check the API connection and retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const addPortfolio = async () => {
    if (adding) return;
    setAdding(true);
    setError("");
    setMessage("");
    try {
      await portfolioApi.create({ name: "Growth" });
      await load();
      setMessage("Portfolio created successfully.");
    } catch {
      setError("The portfolio could not be created. Try again after checking your connection.");
    } finally {
      setAdding(false);
    }
  };

  const portfolio = portfolios[0];
  const allocation = analytics?.allocation;
  const pieData = allocation
    ? [
        { name: "Invested", value: allocation.equity || 0 },
        { name: "Cash", value: allocation.cash || 0 },
      ]
    : [];

  return (
    <div>
      <DashboardHeader title="Portfolio Analytics" subtitle="Allocation, performance, and trade history" />
      {error && <p className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert">{error} <button type="button" className="ml-2 underline" onClick={() => void load()}>Retry</button></p>}
      {message && <p className="mb-4 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p>}
      {loading ? (
        <Card className="p-8 text-center text-sm text-muted-foreground" role="status">Loading portfolio data…</Card>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="p-6 lg:col-span-2">
              <h3 className="mb-4 font-semibold">Asset Allocation</h3>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" label>
                      {pieData.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground">{error ? "Allocation data is unavailable." : "No allocation data is available for this portfolio yet."}</p>
              )}
            </Card>
            <Card className="space-y-4 p-6">
              {portfolio ? (
                <>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Value</p>
                    <p className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Daily PnL</p>
                    <p className={`text-xl font-semibold ${portfolio.daily_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>{formatCurrency(portfolio.daily_pnl)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Win Rate</p>
                    <p className="text-xl font-semibold">{portfolio.win_rate.toFixed(1)}%</p>
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No portfolio exists for this account yet.</p>
              )}
              {performance && (
                <div className="rounded-lg bg-secondary/50 p-3 text-sm">
                  <p className="text-muted-foreground">30-day return</p>
                  <p className="font-semibold">{((performance.return ?? 0) * 100).toFixed(2)}%</p>
                  <p className="mt-1 text-muted-foreground">Max drawdown: {((performance.max_drawdown ?? 0) * 100).toFixed(2)}%</p>
                </div>
              )}
              <Button variant="outline" className="w-full" onClick={() => void addPortfolio()} disabled={adding}>
                {adding ? "Creating…" : "Add Portfolio"}
              </Button>
            </Card>
          </div>

          {Array.isArray(analytics?.recent_trades) && analytics.recent_trades.length > 0 && (
            <Card className="mt-6 p-6">
              <h3 className="mb-4 font-semibold">Recent Trades</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="text-left text-muted-foreground"><th className="pb-2">Symbol</th><th className="pb-2">Side</th><th className="pb-2">PnL</th><th className="pb-2">Status</th></tr></thead>
                  <tbody>
                    {analytics.recent_trades.map((trade, index) => (
                      <tr key={index} className="border-t border-white/5">
                        <td className="py-2 font-mono">{String(trade.symbol ?? "—")}</td>
                        <td className="capitalize">{String(trade.side ?? "—")}</td>
                        <td>{trade.pnl != null ? formatCurrency(Number(trade.pnl)) : "—"}</td>
                        <td className="capitalize">{String(trade.status ?? "—")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
