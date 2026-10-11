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
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const response = await strategyApi.list();
      setStrategies(Array.isArray(response.data) ? response.data : []);
      setLoadError("");
    } catch {
      setLoadError("Strategies could not be loaded. Check your connection and retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const createStrategy = async () => {
    if (saving) return;
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
      setMessage("Paper strategy created successfully.");
    } catch {
      setMessage("Could not create the strategy. Check the fields and try again.");
    } finally {
      setSaving(false);
    }
  };

  const start = async (id: string) => {
    if (pendingAction) return;
    setPendingAction(`start:${id}`);
    setMessage("");
    try {
      await strategyApi.start(id);
      await load();
      setMessage("Strategy start request completed.");
    } catch {
      setMessage("Could not start strategy. Verify its configuration and status.");
    } finally {
      setPendingAction(null);
    }
  };

  const stop = async (id: string, strategyName: string) => {
    if (pendingAction) return;
    const confirmed = window.confirm(`Stop strategy "${strategyName}"? The server will receive a stop request.`);
    if (!confirmed) return;
    setPendingAction(`stop:${id}`);
    setMessage("");
    try {
      await strategyApi.stop(id);
      await load();
      setMessage("Strategy stop request completed.");
    } catch {
      setMessage("Could not stop strategy. Check its current status and try again.");
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Strategies</h1>
        <p className="text-sm text-muted-foreground">Build and run paper strategies through the canonical execution lifecycle.</p>
      </div>

      <Card className="p-6">
        <h2 className="mb-4 font-semibold">Create paper strategy</h2>
        <form onSubmit={(event) => { event.preventDefault(); void createStrategy(); }}>
          <div className="grid gap-4 md:grid-cols-3">
            <Input aria-label="Strategy name" placeholder="Strategy name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input aria-label="Symbol" placeholder="Symbol, e.g. AAPL" value={symbol} onChange={(e) => setSymbol(e.target.value)} required />
            <select aria-label="Strategy type" className="h-10 rounded-lg border border-border bg-secondary/50 px-3 text-sm" value={strategyType} onChange={(e) => setStrategyType(e.target.value)}>
              {STRATEGY_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
            </select>
          </div>
          <Button type="submit" className="mt-4" disabled={saving}>{saving ? "Creating…" : "Create Strategy"}</Button>
        </form>
        {message && <p className="mt-3 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p>}
      </Card>

      {loadError && <div className="rounded-lg border border-red-500/30 p-4 text-sm text-red-500" role="alert">{loadError} <button type="button" className="ml-2 underline" onClick={() => void load()}>Retry</button></div>}

      <div className="grid gap-4 md:grid-cols-2">
        {loading ? (
          <Card className="col-span-2 p-8 text-center text-muted-foreground" role="status">Loading strategies…</Card>
        ) : !loadError && strategies.length === 0 ? (
          <Card className="col-span-2 p-8 text-center text-muted-foreground">No strategies yet.</Card>
        ) : strategies.map((strategy) => (
          <Card key={strategy.id} className="glass-hover p-6">
            <div className="flex justify-between gap-4">
              <div>
                <h3 className="font-semibold">{strategy.name}</h3>
                <p className="text-sm text-muted-foreground">{strategy.symbol} · {strategy.strategy_type}</p>
              </div>
              <span className="h-fit rounded-full bg-primary/20 px-2 py-0.5 text-xs text-primary capitalize">{strategy.status}</span>
            </div>
            <div className="mt-4 flex gap-2">
              <Button size="sm" onClick={() => void start(strategy.id)} disabled={Boolean(pendingAction) || strategy.status === "active"}>
                {pendingAction === `start:${strategy.id}` ? "Starting…" : "Start"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => void stop(strategy.id, strategy.name)} disabled={Boolean(pendingAction) || strategy.status === "stopped"}>
                {pendingAction === `stop:${strategy.id}` ? "Stopping…" : "Stop"}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-6">
        <h3 className="mb-4 font-semibold">Available Algorithms</h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {STRATEGY_TYPES.map((type) => <div key={type.value} className="rounded-lg bg-secondary/50 px-4 py-3 text-sm">{type.label}</div>)}
        </div>
      </Card>
    </div>
  );
}
