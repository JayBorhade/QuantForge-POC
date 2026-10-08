"use client";

import { useEffect, useState } from "react";
import { Bot, DollarSign, Percent, TrendingUp, Zap } from "lucide-react";
import { motion } from "framer-motion";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { dashboardApi, portfolioApi } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";

interface Overview {
  portfolio_value: number;
  daily_pnl: number;
  active_bots: number;
  open_trades: number;
  risk_exposure: number;
  win_rate: number;
  market_sentiment: string;
  ai_suggestions: { type: string; message: string; confidence: number }[];
}

interface HistoryPoint {
  timestamp: string;
  equity: number;
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);

  useEffect(() => {
    dashboardApi.overview().then((r) => setOverview(r.data)).catch(() => setOverview(null));
    portfolioApi.list().then(async (r) => {
      const first = r.data?.[0];
      if (!first) return;
      const historyResponse = await portfolioApi.history(first.id, 30);
      setHistory(historyResponse.data?.map((point: HistoryPoint) => ({
        timestamp: point.timestamp,
        equity: Number(point.equity),
      })) ?? []);
    }).catch(() => setHistory([]));
  }, []);

  const stats = overview
    ? [
        { label: "Portfolio Value", value: formatCurrency(overview.portfolio_value), icon: DollarSign, color: "text-primary" },
        { label: "Daily PnL", value: formatCurrency(overview.daily_pnl), icon: TrendingUp, color: overview.daily_pnl >= 0 ? "text-emerald-400" : "text-red-400" },
        { label: "Active Bots", value: String(overview.active_bots), icon: Bot, color: "text-primary" },
        { label: "Win Rate", value: formatPercent(overview.win_rate), icon: Percent, color: "text-emerald-400" },
      ]
    : [];

  return (
    <div className="space-y-8">
      <DashboardHeader title="Dashboard Overview" subtitle="Portfolio and strategy performance" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Card className="glass-hover p-6">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <p className={`mt-2 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-6">
          <CardHeader className="p-0 pb-4"><CardTitle>Portfolio Equity</CardTitle></CardHeader>
          <CardContent className="p-0 h-64">
            {history.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history}>
                  <XAxis dataKey="timestamp" hide />
                  <YAxis hide />
                  <Tooltip />
                  <Area type="monotone" dataKey="equity" stroke="#10b981" fill="#10b98120" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No portfolio history recorded yet.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="p-6">
          <CardHeader className="p-0 pb-4 flex flex-row items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <CardTitle>Insights</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {overview?.ai_suggestions.length ? overview.ai_suggestions.map((s, i) => (
              <div key={i} className="rounded-lg bg-secondary/50 p-3 mb-3">
                <p className="text-xs uppercase text-primary">{s.type}</p>
                <p className="mt-1 text-sm">{s.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">Confidence: {(s.confidence * 100).toFixed(0)}%</p>
              </div>
            )) : (
              <p className="text-sm text-muted-foreground">No generated insights are available for the current portfolio state.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Risk Exposure</p>
          <p className="text-xl font-bold">{overview ? `${overview.risk_exposure.toFixed(1)}%` : "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Open Trades</p>
          <p className="text-xl font-bold">{overview?.open_trades ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Market Sentiment</p>
          <p className="text-xl font-bold capitalize text-muted-foreground">{overview?.market_sentiment ?? "—"}</p>
        </Card>
      </div>
    </div>
  );
}
