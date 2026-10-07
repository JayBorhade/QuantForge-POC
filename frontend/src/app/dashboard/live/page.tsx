"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { dashboardApi } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { formatCurrency } from "@/lib/utils";

interface Trade {
  id: string;
  symbol: string;
  side: string;
  status: string;
  pnl: number | null;
  quantity: number;
}

export default function LiveTradingPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const { connected, lastMessage } = useWebSocket();

  useEffect(() => {
    dashboardApi.recentTrades().then((r) => setTrades(r.data)).catch(() => setTrades([]));
    const interval = setInterval(() => {
      dashboardApi.recentTrades().then((r) => setTrades(r.data)).catch(() => {});
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <DashboardHeader title="Live Trading Panel" subtitle="Real-time positions and execution feed" />
      <div className="mb-4 flex items-center gap-2">
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
        </span>
        <span className="text-sm text-emerald-400">
          {connected ? "WebSocket connected" : "Connecting..."}
        </span>
        {lastMessage?.type === "trade" && (
          <span className="text-xs text-muted-foreground ml-4">Last event: trade</span>
        )}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Open Positions</h3>
          {trades.filter((t) => t.status === "open").length === 0 ? (
            <p className="text-sm text-muted-foreground">No open positions</p>
          ) : (
            trades.filter((t) => t.status === "open").map((t) => (
              <motion.div
                key={t.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-between border-b border-white/5 py-3 last:border-0"
              >
                <div>
                  <span className="font-mono font-medium">{t.symbol}</span>
                  <span className={`ml-2 text-xs capitalize ${t.side === "buy" ? "text-emerald-400" : "text-red-400"}`}>
                    {t.side}
                  </span>
                </div>
                <span>{t.pnl != null ? formatCurrency(t.pnl) : "—"}</span>
              </motion.div>
            ))
          )}
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Recent Executions</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto font-mono text-xs">
            {trades.length === 0 ? (
              <p className="text-muted-foreground">Waiting for trades...</p>
            ) : (
              trades.map((t) => (
                <div key={t.id} className="flex gap-2 text-muted-foreground">
                  <span className="text-emerald-400">EXEC</span>
                  <span>{t.side.toUpperCase()}</span>
                  <span>{t.quantity}</span>
                  <span>{t.symbol}</span>
                  <span className="capitalize">{t.status}</span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
