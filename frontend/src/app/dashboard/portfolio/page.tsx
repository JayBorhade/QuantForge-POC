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

const COLORS = ["#3b82f6", "#10b981"];

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    portfolioApi.list().then((r) => {
      setPortfolios(r.data);
      if (r.data[0]) {
        portfolioApi.analytics(r.data[0].id).then((a) => setAnalytics(a.data));
      }
    }).catch(() => setPortfolios([]));
  }, []);

  const p = portfolios[0];
  const allocation = analytics?.allocation as { equity?: number; cash?: number } | undefined;
  const pieData = allocation
    ? [
        { name: "Invested", value: allocation.equity || 0 },
        { name: "Cash", value: allocation.cash || 0 },
      ]
    : [];

  return (
    <div>
      <DashboardHeader title="Portfolio Analytics" subtitle="Allocation, performance, and trade history" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-6">
          <h3 className="font-semibold mb-4">Asset Allocation</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value" label>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-sm">No portfolio data yet.</p>
          )}
        </Card>
        <Card className="p-6 space-y-4">
          {p ? (
            <>
              <div>
                <p className="text-sm text-muted-foreground">Total Value</p>
                <p className="text-2xl font-bold">{formatCurrency(p.total_value)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Daily PnL</p>
                <p className={`text-xl font-semibold ${p.daily_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {formatCurrency(p.daily_pnl)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Win Rate</p>
                <p className="text-xl font-semibold">{p.win_rate.toFixed(1)}%</p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Sign up creates a Main Portfolio automatically.</p>
          )}
          <Button variant="outline" className="w-full" onClick={() => portfolioApi.create({ name: "Growth" }).then(() => portfolioApi.list().then((r) => setPortfolios(r.data)))}>
            Add Portfolio
          </Button>
        </Card>
      </div>
      {analytics?.recent_trades && (
        <Card className="mt-6 p-6">
          <h3 className="font-semibold mb-4">Recent Trades</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="pb-2">Symbol</th>
                  <th className="pb-2">Side</th>
                  <th className="pb-2">PnL</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(analytics.recent_trades as Array<Record<string, unknown>>).map((t, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="py-2 font-mono">{String(t.symbol)}</td>
                    <td className="capitalize">{String(t.side)}</td>
                    <td>{t.pnl != null ? formatCurrency(Number(t.pnl)) : "—"}</td>
                    <td className="capitalize">{String(t.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
