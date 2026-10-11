"use client";

import { useEffect, useState } from "react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { brokerApi } from "@/lib/api";

const BROKERS = [
  { id: "zerodha", name: "Zerodha Kite", region: "India" },
  { id: "binance", name: "Binance", region: "Global Crypto" },
  { id: "angel_one", name: "Angel One SmartAPI", region: "India" },
];

type ConnectedBroker = { id: string; broker: string; is_active: boolean };

export default function BrokersPage() {
  const [connected, setConnected] = useState<ConnectedBroker[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [quote, setQuote] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<"connect" | "quote" | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const response = await brokerApi.list();
      setConnected(Array.isArray(response.data) ? response.data : []);
      setError("");
    } catch {
      setError("Broker connections could not be loaded. Check your connection and retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const connect = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || pending) return;
    if (!apiKey.trim() || !apiSecret) {
      setError("Enter both the broker API key and secret.");
      return;
    }
    setPending("connect");
    setError("");
    setMessage("");
    try {
      await brokerApi.connect({ broker: selected, api_key: apiKey.trim(), api_secret: apiSecret });
      setApiKey("");
      setApiSecret("");
      setSelected(null);
      await load();
      setMessage("Broker connection request completed.");
    } catch {
      setError("The broker could not be connected. Verify the credentials and broker configuration.");
    } finally {
      setPending(null);
    }
  };

  const fetchQuote = async () => {
    if (pending) return;
    setPending("quote");
    setError("");
    setMessage("");
    try {
      const { data } = await brokerApi.quote("BTCUSDT", "binance");
      setQuote(data);
      setMessage("Quote request completed.");
    } catch {
      setError("The quote could not be fetched. Check broker connectivity and market-data configuration.");
    } finally {
      setPending(null);
    }
  };

  return (
    <div>
      <DashboardHeader title="Broker Connections" subtitle="Connect Zerodha, Binance, or Angel One" />
      {error && <p className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert">{error} <button type="button" className="ml-2 underline" onClick={() => void load()}>Retry</button></p>}
      {message && <p className="mb-4 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p>}
      <div className="mb-8 grid gap-4 md:grid-cols-3">
        {BROKERS.map((broker) => {
          const isConnected = connected.some((item) => item.broker === broker.id && item.is_active);
          return (
            <Card key={broker.id} className={`glass-hover p-6 ${selected === broker.id ? "border-primary/50" : ""}`}>
              <h3 className="font-semibold">{broker.name}</h3>
              <p className="text-sm text-muted-foreground">{broker.region}</p>
              {isConnected ? (
                <span className="mt-3 inline-block text-xs text-emerald-500">● Connected</span>
              ) : (
                <Button className="mt-4 w-full" variant="outline" onClick={() => { setSelected(broker.id); setError(""); }} disabled={pending !== null}>
                  Configure
                </Button>
              )}
            </Card>
          );
        })}
      </div>

      {selected && (
        <Card className="mb-8 max-w-md space-y-4 p-6">
          <h3 className="font-semibold">Connect {BROKERS.find((broker) => broker.id === selected)?.name}</h3>
          <form className="space-y-4" onSubmit={connect}>
            <div>
              <label htmlFor="broker-api-key" className="mb-1 block text-sm font-medium">API Key</label>
              <Input id="broker-api-key" name="api-key" autoComplete="off" placeholder="Broker API key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} required />
            </div>
            <div>
              <label htmlFor="broker-api-secret" className="mb-1 block text-sm font-medium">API Secret</label>
              <Input id="broker-api-secret" name="api-secret" autoComplete="off" type="password" placeholder="Broker API secret" value={apiSecret} onChange={(event) => setApiSecret(event.target.value)} required />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={pending !== null}>{pending === "connect" ? "Connecting…" : "Connect Broker"}</Button>
              <Button type="button" variant="outline" onClick={() => { setSelected(null); setApiKey(""); setApiSecret(""); }} disabled={pending !== null}>Cancel</Button>
            </div>
          </form>
          <p className="text-xs text-muted-foreground">Credentials are submitted to the configured backend. Never share them in support messages.</p>
        </Card>
      )}

      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h3 className="font-semibold">Live Quote Test</h3>
          <Button variant="outline" size="sm" onClick={() => void fetchQuote()} disabled={pending !== null}>
            {pending === "quote" ? "Fetching…" : "Fetch BTC/USDT"}
          </Button>
        </div>
        {loading ? <p className="text-sm text-muted-foreground" role="status">Loading broker connections…</p> : null}
        {quote && (
          <pre className="overflow-x-auto rounded-lg bg-secondary/50 p-4 text-sm text-muted-foreground">
            {JSON.stringify(quote, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
