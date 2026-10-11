"use client";

import { useEffect, useState } from "react";
import { Rocket, Play, Square } from "lucide-react";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { deploymentApi, strategyApi } from "@/lib/api";

interface Deployment {
  id: string;
  name: string;
  status: string;
  region: string;
  strategy_id: string;
}

export default function DeployPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [strategies, setStrategies] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [deploymentResponse, strategyResponse] = await Promise.all([
        deploymentApi.list(),
        strategyApi.list(),
      ]);
      setDeployments(Array.isArray(deploymentResponse.data) ? deploymentResponse.data : []);
      setStrategies(Array.isArray(strategyResponse.data) ? strategyResponse.data : []);
      setError("");
    } catch {
      setError("Deployment data could not be loaded. Check your connection and retry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const deploy = async () => {
    if (!strategies[0] || pendingAction) return;
    setPendingAction("deploy");
    setError("");
    setMessage("");
    try {
      await deploymentApi.create({
        strategy_id: strategies[0].id,
        name: `${strategies[0].name} Bot`,
        region: "us-east-1",
      });
      await load();
      setMessage("Deployment creation request completed.");
    } catch {
      setError("The deployment could not be created. Verify your configuration and try again.");
    } finally {
      setPendingAction(null);
    }
  };

  const start = async (deployment: Deployment) => {
    if (pendingAction) return;
    setPendingAction(`start:${deployment.id}`);
    setError("");
    setMessage("");
    try {
      await deploymentApi.start(deployment.id);
      await load();
      setMessage("Deployment start request completed.");
    } catch {
      setError("The deployment could not be started. Check its current status and try again.");
    } finally {
      setPendingAction(null);
    }
  };

  const stop = async (deployment: Deployment) => {
    if (pendingAction) return;
    if (!window.confirm(`Stop deployment "${deployment.name}"? This sends a stop request to the server.`)) return;
    setPendingAction(`stop:${deployment.id}`);
    setError("");
    setMessage("");
    try {
      await deploymentApi.stop(deployment.id);
      await load();
      setMessage("Deployment stop request completed.");
    } catch {
      setError("The deployment could not be stopped. Check its current status and try again.");
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <div>
      <DashboardHeader title="Deployment Center" subtitle="Deploy and manage trading bots in the cloud" />
      <div className="mb-6 flex justify-end">
        <Button onClick={() => void deploy()} className="gap-2" disabled={!strategies.length || Boolean(pendingAction)}>
          <Rocket aria-hidden="true" className="h-4 w-4" /> {pendingAction === "deploy" ? "Deploying…" : "Deploy Bot"}
        </Button>
      </div>
      {error && <p className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert">{error} <button type="button" className="ml-2 underline" onClick={() => void load()}>Retry</button></p>}
      {message && <p className="mb-4 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p>}
      {loading ? (
        <Card className="p-12 text-center text-muted-foreground" role="status">Loading deployment data…</Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {deployments.length === 0 ? (
            <Card className="col-span-2 p-12 text-center text-muted-foreground">
              No deployments found. Create a strategy first, then deploy a bot.
            </Card>
          ) : deployments.map((deployment) => (
            <Card key={deployment.id} className="glass-hover p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-semibold">{deployment.name}</h3>
                  <p className="text-sm text-muted-foreground">{deployment.region}</p>
                </div>
                <span className={`h-fit rounded-full px-2 py-0.5 text-xs capitalize ${deployment.status === "running" ? "bg-emerald-500/20 text-emerald-500" : "bg-secondary text-muted-foreground"}`}>
                  {deployment.status}
                </span>
              </div>
              <div className="mt-4 flex gap-2">
                <Button size="sm" variant="outline" className="gap-1" disabled={Boolean(pendingAction) || deployment.status === "running"} onClick={() => void start(deployment)}>
                  <Play aria-hidden="true" className="h-3 w-3" /> {pendingAction === `start:${deployment.id}` ? "Starting…" : "Start"}
                </Button>
                <Button size="sm" variant="ghost" className="gap-1" disabled={Boolean(pendingAction) || deployment.status === "stopped"} onClick={() => void stop(deployment)}>
                  <Square aria-hidden="true" className="h-3 w-3" /> {pendingAction === `stop:${deployment.id}` ? "Stopping…" : "Stop"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
