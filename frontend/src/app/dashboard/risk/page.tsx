"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Shield, Activity, Save } from "lucide-react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { portfolioApi, riskApi } from "@/lib/api";

type Portfolio = { id: string; name: string; total_value?: number; cash_balance?: number };
type Summary = {
  equity: number;
  gross_exposure: number;
  net_exposure: number;
  open_order_notional: number;
  position_count: number;
  open_order_count: number;
  daily_pnl: number;
  kill_switch: boolean;
  gross_utilization?: number | null;
  daily_loss_utilization?: number | null;
  open_order_utilization?: number | null;
  largest_symbol?: string | null;
  largest_symbol_exposure: number;
  largest_strategy_exposure: number;
};

type Limits = {
  max_order_notional?: number | null;
  max_position_quantity?: number | null;
  max_daily_loss?: number | null;
  max_open_orders?: number | null;
  max_gross_exposure?: number | null;
  max_symbol_exposure?: number | null;
  max_strategy_exposure?: number | null;
  max_strategy_allocation_pct?: number | null;
  kill_switch: boolean;
};

const emptyLimits: Limits = { kill_switch: false };

const pct = (value?: number | null) =>
  value == null ? "—" : `${(value * 100).toFixed(1)}%`;
const money = (value?: number | null) =>
  value == null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 2 });

export default function RiskPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [portfolioId, setPortfolioId] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [limits, setLimits] = useState<Limits>(emptyLimits);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const load = async (id: string) => {
    if (!id) return;
    const [summaryRes, limitsRes] = await Promise.all([
      riskApi.summary(id),
      riskApi.limits(id),
    ]);
    setSummary(summaryRes.data);
    setLimits(limitsRes.data ?? emptyLimits);
  };

  useEffect(() => {
    portfolioApi.list().then((r) => {
      setPortfolios(r.data);
      if (r.data[0]) setPortfolioId(r.data[0].id);
    }).catch(() => setPortfolios([]));
  }, []);

  useEffect(() => {
    if (portfolioId) load(portfolioId).catch(() => {
      setSummary(null);
      setMessage("Unable to load risk controls.");
    });
  }, [portfolioId]);

  const update = (key: keyof Limits, value: string) => {
    setLimits((current) => ({ ...current, [key]: value === "" ? null : Number(value) }));
  };

  const save = async () => {
    if (!portfolioId) return;
    setSaving(true);
    setMessage("");
    try {
      await riskApi.updateLimits(portfolioId, limits);
      await load(portfolioId);
      setMessage("Risk controls saved.");
    } catch {
      setMessage("Could not save risk controls.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <DashboardHeader title="Risk Management" subtitle="Exposure limits, utilization, and portfolio controls" />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          aria-label="Portfolio"
          className="h-10 rounded-lg border border-border bg-secondary/50 px-3 text-sm"
          value={portfolioId}
          onChange={(e) => setPortfolioId(e.target.value)}
        >
          {portfolios.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {summary?.kill_switch && (
          <span className="inline-flex items-center gap-2 rounded-full border border-red-500/40 px-3 py-1 text-sm text-red-400">
            <AlertTriangle className="h-4 w-4" /> Kill switch active
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Equity", money(summary?.equity)],
          ["Gross Exposure", money(summary?.gross_exposure)],
          ["Net Exposure", money(summary?.net_exposure)],
          ["Daily P&L", money(summary?.daily_pnl)],
        ].map(([label, value]) => (
          <Card key={label} className="p-5">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-2 text-2xl font-bold">{value}</p>
          </Card>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Risk Utilization</h3>
          </div>
          {[
            ["Gross exposure", pct(summary?.gross_utilization)],
            ["Daily loss", pct(summary?.daily_loss_utilization)],
            ["Open orders", pct(summary?.open_order_utilization)],
          ].map(([label, value]) => (
            <div key={label} className="mb-4">
              <div className="mb-1 flex justify-between text-sm">
                <span>{label}</span><span>{value}</span>
              </div>
              <div className="h-2 rounded-full bg-secondary">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{ width: `${Math.min(100, Number.parseFloat(String(value)) || 0)}%` }}
                />
              </div>
            </div>
          ))}
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm text-muted-foreground">
            <span>Positions: {summary?.position_count ?? "—"}</span>
            <span>Open orders: {summary?.open_order_count ?? "—"}</span>
            <span>Largest symbol: {summary?.largest_symbol ?? "—"}</span>
            <span>Symbol exposure: {money(summary?.largest_symbol_exposure)}</span>
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-5 flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <h3 className="font-semibold">Risk Controls</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {([
              ["max_order_notional", "Max order notional"],
              ["max_position_quantity", "Max position quantity"],
              ["max_daily_loss", "Max daily loss"],
              ["max_open_orders", "Max open orders"],
              ["max_gross_exposure", "Max gross exposure"],
              ["max_symbol_exposure", "Max symbol exposure"],
              ["max_strategy_exposure", "Max strategy exposure"],
              ["max_strategy_allocation_pct", "Max strategy allocation (0–1)"],
            ] as [keyof Limits, string][]).map(([key, label]) => (
              <label key={key} className="text-sm">
                <span className="mb-1 block text-muted-foreground">{label}</span>
                <Input
                  type="number"
                  min="0"
                  step="any"
                  value={limits[key] ?? ""}
                  onChange={(e) => update(key, e.target.value)}
                />
              </label>
            ))}
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={limits.kill_switch}
              onChange={(e) => setLimits((current) => ({ ...current, kill_switch: e.target.checked }))}
            />
            Enable portfolio kill switch
          </label>
          <Button className="mt-5" onClick={save} disabled={saving || !portfolioId}>
            <Save className="mr-2 h-4 w-4" /> {saving ? "Saving..." : "Save controls"}
          </Button>
          {message && <p className="mt-3 text-sm text-muted-foreground">{message}</p>}
        </Card>
      </div>
    </div>
  );
}
