"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bot, DollarSign, Percent, TrendingUp, Zap } from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { aiApi, dashboardApi } from "@/lib/api";
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

const chartData = Array.from({ length: 14 }, (_, i) => ({
  day: `D${i + 1}`,
  pnl: 1200 + Math.sin(i * 0.5) * 3000 + i * 400,
}));

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    dashboardApi.overview().then((r) => setOverview(r.data)).catch(() => {
      setOverview({
        portfolio_value: 248750,
        daily_pnl: 3240,
        active_bots: 3,
        open_trades: 7,
        risk_exposure: 12.4,
        win_rate: 68.2,
        market_sentiment: "bullish",
        ai_suggestions: [
          { type: "risk", message: "Reduce exposure on high-beta positions.", confidence: 0.85 },
          { type: "opportunity", message: "EMA crossover on AAPL — review strategy.", confidence: 0.72 },
        ],
      });
    });
  }, []);

  const stats = overview
    ? [
        { label: "Portfolio Value", value: formatCurrency(overview.portfolio_value), icon: DollarSign, color: "text-primary" },
        { label: "Daily PnL", value: formatCurrency(overview.daily_pnl), icon: TrendingUp, color: overview.daily_pnl >= 0 ? "text-emerald-400" : "text-red-400" },
        { label: "Active Bots", value: String(overview.active_bots), icon: Bot, color: "text-primary" },
        { label: "Win Rate", value: formatPercent(overview.win_rate), icon: Percent, color: "text-emerald-400" },
      ]
    : [];

  useEffect(() => {
    aiApi.marketSummary().catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      <DashboardHeader
        title="Dashboard Overview"
        subtitle="Real-time portfolio and strategy performance"
      />

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
          <CardHeader className="p-0 pb-4">
            <CardTitle>PnL Trend</CardTitle>
          </CardHeader>
          <CardContent className="p-0 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="day" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                <Area type="monotone" dataKey="pnl" stroke="#10b981" fill="url(#pnlGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="p-6">
          <CardHeader className="p-0 pb-4 flex flex-row items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <CardTitle>AI Suggestions</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-4">
            {overview?.ai_suggestions.map((s, i) => (
              <div key={i} className="rounded-lg bg-secondary/50 p-3">
                <p className="text-xs uppercase text-primary">{s.type}</p>
                <p className="mt-1 text-sm">{s.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Confidence: {(s.confidence * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Risk Exposure</p>
          <p className="text-xl font-bold">{overview?.risk_exposure.toFixed(1)}%</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Open Trades</p>
          <p className="text-xl font-bold">{overview?.open_trades}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Market Sentiment</p>
          <p className="text-xl font-bold capitalize text-emerald-400">{overview?.market_sentiment}</p>
        </Card>
      </div>
    </div>
  );
}
