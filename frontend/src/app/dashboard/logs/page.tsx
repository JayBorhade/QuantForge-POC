"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { logsApi } from "@/lib/api";

type StrategyLog = {
  timestamp: string;
  level: string;
  message: string;
  run_id: string | null;
  metrics?: { sharpe?: number | null; return?: number | null };
};

type AuditLog = {
  timestamp: string;
  action: string;
  resource: string;
  ip: string | null;
};

type LogTab = "strategy" | "audit";

function formatTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

export default function LogsPage() {
  const [tab, setTab] = useState<LogTab>("strategy");
  const [strategyLogs, setStrategyLogs] = useState<StrategyLog[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (background = false) => {
    if (background) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      if (tab === "strategy") {
        const response = await logsApi.strategy();
        setStrategyLogs(Array.isArray(response.data) ? response.data : []);
      } else {
        const response = await logsApi.audit();
        setAuditLogs(Array.isArray(response.data) ? response.data : []);
      }
    } catch {
      setError(tab === "strategy"
        ? "Strategy run history could not be loaded. Check your connection and retry."
        : "Audit history could not be loaded. Check your connection and retry.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [tab]);

  useEffect(() => { void load(); }, [load]);

  const visibleStrategyLogs = strategyLogs;
  const visibleAuditLogs = auditLogs;

  return (
    <div>
      <DashboardHeader title="Activity & Logs" subtitle="Review your strategy run history and account audit events" />
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Log category">
          <Button type="button" variant={tab === "strategy" ? "default" : "outline"} aria-pressed={tab === "strategy"} onClick={() => setTab("strategy")}>Strategy runs</Button>
          <Button type="button" variant={tab === "audit" ? "default" : "outline"} aria-pressed={tab === "audit"} onClick={() => setTab("audit")}>Audit events</Button>
        </div>
        <Button type="button" variant="outline" onClick={() => void load(true)} disabled={loading || refreshing}>
          <RefreshCw aria-hidden="true" className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin motion-reduce:animate-none" : ""}`} />
          {refreshing ? "Refreshing…" : "Refresh"}
        </Button>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert">{error} <button type="button" className="ml-2 underline" onClick={() => void load()}>Retry</button></div>}

      {tab === "strategy" ? (
        <Card className="overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-semibold">Strategy run history</h2>
            <p className="mt-1 text-xs text-muted-foreground">Run status and errors returned by the strategy API.</p>
          </div>
          {loading ? <p className="p-6 text-sm text-muted-foreground" role="status">Loading strategy runs…</p> : error ? <p className="p-6 text-sm text-muted-foreground">Run history is unavailable.</p> : visibleStrategyLogs.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No strategy run history is available.</p> : (
            <div className="divide-y divide-border">
              {visibleStrategyLogs.map((entry, index) => (
                <article key={entry.run_id ?? `${entry.timestamp}-${index}`} className="px-5 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-medium ${entry.level === "ERROR" ? "bg-red-500/10 text-red-500" : "bg-secondary text-muted-foreground"}`}>{entry.level}</span>
                    <time className="text-xs text-muted-foreground" dateTime={entry.timestamp}>{formatTimestamp(entry.timestamp)}</time>
                  </div>
                  <p className="mt-3 break-words text-sm">{entry.message}</p>
                  {entry.run_id && <p className="mt-2 break-all font-mono text-xs text-muted-foreground">Run ID: {entry.run_id}</p>}
                  {entry.metrics && (
                    <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
                      {entry.metrics.sharpe != null && <span>Sharpe: {entry.metrics.sharpe.toFixed(2)}</span>}
                      {entry.metrics.return != null && <span>Return: {entry.metrics.return.toFixed(2)}%</span>}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-semibold">Account audit events</h2>
            <p className="mt-1 text-xs text-muted-foreground">Events associated with your account, as returned by the audit API.</p>
          </div>
          {loading ? <p className="p-6 text-sm text-muted-foreground" role="status">Loading audit events…</p> : error ? <p className="p-6 text-sm text-muted-foreground">Audit history is unavailable.</p> : visibleAuditLogs.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No audit events are available.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead><tr className="border-b border-border text-xs text-muted-foreground"><th scope="col" className="px-5 py-3 font-medium">Time</th><th scope="col" className="px-5 py-3 font-medium">Action</th><th scope="col" className="px-5 py-3 font-medium">Resource</th><th scope="col" className="px-5 py-3 font-medium">IP address</th></tr></thead>
                <tbody>
                  {visibleAuditLogs.map((entry, index) => (
                    <tr key={`${entry.timestamp}-${entry.action}-${index}`} className="border-b border-border last:border-0">
                      <td className="whitespace-nowrap px-5 py-3 text-xs text-muted-foreground"><time dateTime={entry.timestamp}>{formatTimestamp(entry.timestamp)}</time></td>
                      <td className="px-5 py-3">{entry.action}</td>
                      <td className="px-5 py-3 break-all">{entry.resource}</td>
                      <td className="px-5 py-3 font-mono text-xs text-muted-foreground">{entry.ip || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
