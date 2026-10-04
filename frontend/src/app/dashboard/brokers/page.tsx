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

export default function BrokersPage() {
  const [connected, setConnected] = useState<Array<{ id: string; broker: string; is_active: boolean }>>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [quote, setQuote] = useState<Record<string, unknown> | null>(null);

  const load = () => brokerApi.list().then((r) => setConnected(r.data)).catch(() => []);

  useEffect(() => { load(); }, []);

  const connect = async () => {
    if (!selected) return;
    await brokerApi.connect({ broker: selected, api_key: apiKey, api_secret: apiSecret });
    setApiKey("");
    setApiSecret("");
    setSelected(null);
    load();
  };

  const fetchQuote = async () => {
    const { data } = await brokerApi.quote("BTCUSDT", "binance");
    setQuote(data);
  };

  return (
    <div>
      <DashboardHeader title="Broker Connections" subtitle="Connect Zerodha, Binance, or Angel One" />
      <div className="grid gap-4 md:grid-cols-3 mb-8">
        {BROKERS.map((b) => {
          const isConnected = connected.some((c) => c.broker === b.id && c.is_active);
          return (
            <Card key={b.id} className={`glass-hover p-6 ${selected === b.id ? "border-primary/50" : ""}`}>
              <h3 className="font-semibold">{b.name}</h3>
              <p className="text-sm text-muted-foreground">{b.region}</p>
              {isConnected ? (
                <span className="mt-3 inline-block text-xs text-emerald-400">● Connected</span>
              ) : (
                <Button className="mt-4 w-full" variant="outline" onClick={() => setSelected(b.id)}>
                  Configure
                </Button>
              )}
            </Card>
          );
        })}
      </div>

      {selected && (
        <Card className="p-6 mb-8 max-w-md space-y-4">
          <h3 className="font-semibold">Connect {BROKERS.find((b) => b.id === selected)?.name}</h3>
          <Input placeholder="API Key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
          <Input type="password" placeholder="API Secret" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} />
          <Button onClick={connect}>Connect Broker</Button>
        </Card>
      )}

      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold">Live Quote Test</h3>
          <Button variant="outline" size="sm" onClick={fetchQuote}>Fetch BTC/USDT</Button>
        </div>
        {quote && (
          <pre className="text-sm text-muted-foreground bg-secondary/50 p-4 rounded-lg overflow-x-auto">
            {JSON.stringify(quote, null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}
