"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { strategyApi } from "@/lib/api";

const STRATEGY_TYPES = [
  { value: "ema_crossover", label: "EMA Crossover" },
  { value: "rsi_mean_reversion", label: "RSI Mean Reversion" },
  { value: "vwap_intraday", label: "VWAP Intraday" },
  { value: "breakout", label: "Breakout" },
  { value: "ai_sentiment", label: "AI Sentiment" },
];

type Strategy = { id: string; name: string; symbol: string; status: string; strategy_type: string };

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [strategyType, setStrategyType] = useState(STRATEGY_TYPES[0].value);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => strategyApi.list().then((r) => setStrategies(r.data)).catch(() => setStrategies([]));

  useEffect(() => { load(); }, []);

  const createStrategy = async () => {
    if (!name.trim() || !symbol.trim()) {
      setMessage("Name and symbol are required.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      await strategyApi.create({
        name: name.trim(),
        strategy_type: strategyType,
        symbol: symbol.trim().toUpperCase(),
        parameters: {},
        is_paper: true,
      });
      setName("");
      setSymbol("");
      await load();
      setMessage("Paper strategy created.");
    } catch {
      setMessage("Could not create the strategy.");
    } finally {
      setSaving(false);
    }
  };

  const start = async (id: string) => {
    try { await strategyApi.start(id); await load(); } catch { setMessage("Could not start strategy."); }
  };
  const stop = async (id: string) => {
    try { await strategyApi.stop(id); await load(); } catch { setMessage("Could not stop strategy."); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Strategies</h1>
        <p className="text-sm text-muted-foreground">Build and run paper strategies through the canonical execution lifecycle.</p>
      </div>

      <Card className="p-6">
        <h2 className="mb-4 font-semibold">Create paper strategy</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Input aria-label="Strategy name" placeholder="Strategy name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input aria-label="Symbol" placeholder="Symbol, e.g. AAPL" value={symbol} onChange={(e) => setSymbol(e.target.value)} />
          <select
            aria-label="Strategy type"
            className="h-10 rounded-lg border border-border bg-secondary/50 px-3 text-sm"
            value={strategyType}
            onChange={(e) => setStrategyType(e.target.value)}
          >
            {STRATEGY_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
          </select>
        </div>
        <Button className="mt-4" onClick={createStrategy} disabled={saving}>
          {saving ? "Creating..." : "Create Strategy"}
        </Button>
        {message && <p className="mt-3 text-sm text-muted-foreground">{message}</p>}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {strategies.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground col-span-2">No strategies yet.</Card>
        ) : strategies.map((s) => (
          <Card key={s.id} className="glass-hover p-6">
            <div className="flex justify-between">
              <div>
                <h3 className="font-semibold">{s.name}</h3>
                <p className="text-sm text-muted-foreground">{s.symbol} · {s.strategy_type}</p>
              </div>
              <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs text-primary capitalize">{s.status}</span>
            </div>
            <div className="mt-4 flex gap-2">
              <Button size="sm" onClick={() => start(s.id)} disabled={s.status === "active"}>Start</Button>
              <Button size="sm" variant="outline" onClick={() => stop(s.id)} disabled={s.status === "stopped"}>Stop</Button>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-6">
        <h3 className="font-semibold mb-4">Available Algorithms</h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {STRATEGY_TYPES.map((t) => <div key={t.value} className="rounded-lg bg-secondary/50 px-4 py-3 text-sm">{t.label}</div>)}
        </div>
      </Card>
    </div>
  );
}
