import { Navbar } from "@/components/layout/navbar";
import { Card } from "@/components/ui/card";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const features = [
  { title: "Strategy Builder", desc: "Visual and code-based strategy creation with 5 built-in algorithms." },
  { title: "Backtesting Engine", desc: "Sharpe, drawdown, win rate, equity curves, and exportable reports." },
  { title: "Live Execution", desc: "Paper and live modes with Celery workers and WebSocket feeds." },
  { title: "Multi-Broker", desc: "Zerodha Kite, Binance, Angel One — extensible adapter pattern." },
  { title: "Risk Management", desc: "Position sizing, stop loss, trailing stops, and exposure limits." },
  { title: "AI Analytics", desc: "Sentiment scoring, market summaries, and trade journaling." },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="mx-auto max-w-7xl px-4 py-32">
        <h1 className="text-4xl font-bold text-gradient">Platform Features</h1>
        <p className="mt-4 max-w-2xl text-muted-foreground">
          Institutional-grade infrastructure for systematic traders.
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <Card key={f.title} className="glass-hover p-6">
              <h3 className="text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
            </Card>
          ))}
        </div>
        <Link href="/signup" className="inline-block mt-12">
          <Button size="lg">Start Free Trial</Button>
        </Link>
      </div>
    </div>
  );
}
