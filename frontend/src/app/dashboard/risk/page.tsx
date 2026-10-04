"use client";

import { useEffect, useState } from "react";
import { Shield, AlertTriangle } from "lucide-react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { aiApi } from "@/lib/api";

export default function RiskPage() {
  const [risk, setRisk] = useState<{
    overall_risk_score?: number;
    risk_level?: string;
    recommendations?: string[];
    var_95?: number;
    max_drawdown_alert?: boolean;
  } | null>(null);

  useEffect(() => {
    aiApi.riskAnalysis().then((r) => setRisk(r.data)).catch(() => setRisk(null));
  }, []);

  return (
    <div>
      <DashboardHeader title="Risk Management" subtitle="Exposure limits, VaR, and AI risk recommendations" />
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="p-6 text-center">
          <Shield className="mx-auto h-10 w-10 text-primary mb-3" />
          <p className="text-sm text-muted-foreground">Risk Score</p>
          <p className="text-4xl font-bold mt-1">{risk?.overall_risk_score?.toFixed(1) ?? "—"}/10</p>
          <p className="mt-2 text-sm capitalize text-emerald-400">{risk?.risk_level ?? "—"}</p>
        </Card>
        <Card className="p-6 text-center">
          <p className="text-sm text-muted-foreground">Value at Risk (95%)</p>
          <p className="text-3xl font-bold mt-2">${risk?.var_95?.toLocaleString() ?? "—"}</p>
        </Card>
        <Card className={`p-6 text-center ${risk?.max_drawdown_alert ? "border-red-500/50" : ""}`}>
          {risk?.max_drawdown_alert && <AlertTriangle className="mx-auto h-8 w-8 text-red-400 mb-2" />}
          <p className="text-sm text-muted-foreground">Drawdown Alert</p>
          <p className="text-lg font-semibold mt-2">
            {risk?.max_drawdown_alert ? "Active — reduce exposure" : "Within limits"}
          </p>
        </Card>
      </div>
      <Card className="mt-6 p-6">
        <h3 className="font-semibold mb-4">AI Recommendations</h3>
        <ul className="space-y-3">
          {(risk?.recommendations ?? ["Loading risk analysis..."]).map((r, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="text-primary">•</span>
              {r}
            </li>
          ))}
        </ul>
      </Card>
      <Card className="mt-6 p-6">
        <h3 className="font-semibold mb-4">Risk Controls</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {[
            { label: "Max position size", value: "10%" },
            { label: "Max daily loss", value: "2%" },
            { label: "Max open positions", value: "8" },
            { label: "Stop loss default", value: "2%" },
          ].map((c) => (
            <div key={c.label} className="rounded-lg bg-secondary/50 px-4 py-3 flex justify-between">
              <span className="text-sm text-muted-foreground">{c.label}</span>
              <span className="text-sm font-medium">{c.value}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
