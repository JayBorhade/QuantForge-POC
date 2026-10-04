"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { strategyApi } from "@/lib/api";

const STRATEGY_TYPES = [
  { value: "ema_crossover", label: "EMA Crossover" },
  { value: "rsi_mean_reversion", label: "RSI Mean Reversion" },
  { value: "vwap_intraday", label: "VWAP Intraday" },
  { value: "breakout", label: "Breakout" },
  { value: "ai_sentiment", label: "AI Sentiment" },
];

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Array<{ id: string; name: string; symbol: string; status: string; strategy_type: string }>>([]);

  useEffect(() => {
    strategyApi.list().then((r) => setStrategies(r.data)).catch(() => setStrategies([]));
  }, []);

  const createDemo = async () => {
    await strategyApi.create({
      name: "EMA AAPL",
      strategy_type: "ema_crossover",
      symbol: "AAPL",
      parameters: { fast_ema: 20, slow_ema: 50 },
      is_paper: true,
    });
    const { data } = await strategyApi.list();
    setStrategies(data);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Strategies</h1>
        <Button onClick={createDemo}>Create Strategy</Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {strategies.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground col-span-2">
            No strategies yet. Click Create Strategy to add your first algorithm.
          </Card>
        ) : (
          strategies.map((s) => (
            <Card key={s.id} className="glass-hover p-6">
              <div className="flex justify-between">
                <div>
                  <h3 className="font-semibold">{s.name}</h3>
                  <p className="text-sm text-muted-foreground">{s.symbol} · {s.strategy_type}</p>
                </div>
                <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs text-primary capitalize">{s.status}</span>
              </div>
              <div className="mt-4 flex gap-2">
                <Button size="sm" onClick={() => strategyApi.start(s.id)}>Start</Button>
                <Button size="sm" variant="outline" onClick={() => strategyApi.stop(s.id)}>Stop</Button>
              </div>
            </Card>
          ))
        )}
      </div>
      <Card className="p-6">
        <h3 className="font-semibold mb-4">Available Algorithms</h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {STRATEGY_TYPES.map((t) => (
            <div key={t.value} className="rounded-lg bg-secondary/50 px-4 py-3 text-sm">{t.label}</div>
          ))}
        </div>
      </Card>
    </div>
  );
}
