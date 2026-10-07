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

  const load = () => {
    deploymentApi.list().then((r) => setDeployments(r.data)).catch(() => []);
    strategyApi.list().then((r) => setStrategies(r.data)).catch(() => []);
  };

  useEffect(() => { load(); }, []);

  const deploy = async () => {
    if (!strategies[0]) return;
    await deploymentApi.create({
      strategy_id: strategies[0].id,
      name: `${strategies[0].name} Bot`,
      region: "us-east-1",
    });
    load();
  };

  return (
    <div>
      <DashboardHeader title="Deployment Center" subtitle="Deploy and manage trading bots in the cloud" />
      <div className="flex justify-end mb-6">
        <Button onClick={deploy} className="gap-2" disabled={!strategies.length}>
          <Rocket className="h-4 w-4" /> Deploy Bot
        </Button>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {deployments.length === 0 ? (
          <Card className="col-span-2 p-12 text-center text-muted-foreground">
            No deployments yet. Create a strategy first, then deploy a bot.
          </Card>
        ) : (
          deployments.map((d) => (
            <Card key={d.id} className="glass-hover p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold">{d.name}</h3>
                  <p className="text-sm text-muted-foreground">{d.region}</p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${
                  d.status === "running" ? "bg-emerald-500/20 text-emerald-400" : "bg-secondary text-muted-foreground"
                }`}>
                  {d.status}
                </span>
              </div>
              <div className="mt-4 flex gap-2">
                <Button size="sm" variant="outline" className="gap-1" onClick={() => deploymentApi.start(d.id).then(load)}>
                  <Play className="h-3 w-3" /> Start
                </Button>
                <Button size="sm" variant="ghost" className="gap-1" onClick={() => deploymentApi.stop(d.id).then(load)}>
                  <Square className="h-3 w-3" /> Stop
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
