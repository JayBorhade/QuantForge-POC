"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  Bot,
  Brain,
  LineChart,
  Shield,
  Zap,
} from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { HeroChart } from "@/components/landing/hero-chart";
import { MarketTicker } from "@/components/landing/market-ticker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  { icon: LineChart, title: "Advanced Backtesting", desc: "Sharpe ratio, drawdown, equity curves, and full trade history." },
  { icon: Bot, title: "Bot Deployment", desc: "Deploy strategies to paper or live with one click." },
  { icon: Brain, title: "AI Insights", desc: "Market summaries, risk analysis, and portfolio intelligence." },
  { icon: Shield, title: "Institutional Security", desc: "JWT rotation, 2FA, audit logs, and RBAC." },
  { icon: Zap, title: "Multi-Broker", desc: "Zerodha, Binance, Angel One — modular adapters." },
  { icon: BarChart3, title: "Live Analytics", desc: "Real-time PnL, risk exposure, and sentiment." },
];

const metrics = [
  { label: "Strategies Deployed", value: "12,400+" },
  { label: "Backtests Run", value: "2.1M+" },
  { label: "Avg. Sharpe Ratio", value: "1.84" },
  { label: "Uptime SLA", value: "99.97%" },
];

const plans = [
  { name: "Starter", price: "$29", features: ["5 strategies", "Paper trading", "Basic backtesting"] },
  { name: "Pro", price: "$99", features: ["Unlimited strategies", "Live trading", "AI insights", "Priority support"], popular: true },
  { name: "Enterprise", price: "Custom", features: ["Dedicated infra", "Custom brokers", "SLA", "White-label"] },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <MarketTicker />

      <section className="relative px-4 pb-24 pt-32 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }}>
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary">
                <Zap className="h-4 w-4" /> Now in public beta
              </p>
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                Build, Backtest,{" "}
                <span className="text-gradient">Automate, Scale</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg text-muted-foreground">
                QuantForge is production-grade algo trading infrastructure. Create strategies,
                backtest with institutional metrics, and deploy bots across global brokers.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link href="/signup">
                  <Button size="lg" className="gap-2">
                    Start Free Trial <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href="/docs">
                  <Button variant="outline" size="lg">View Documentation</Button>
                </Link>
              </div>
            </motion.div>
            <HeroChart />
          </div>
        </div>
      </section>

      <section className="border-y border-white/5 bg-card/20 py-12">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-4 sm:grid-cols-4 sm:px-6">
          {metrics.map((m) => (
            <div key={m.label} className="text-center">
              <p className="text-3xl font-bold text-gradient">{m.value}</p>
              <p className="mt-1 text-sm text-muted-foreground">{m.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <h2 className="text-center text-3xl font-bold">Everything you need to trade systematically</h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className="glass-hover h-full p-6">
                  <f.icon className="mb-4 h-8 w-8 text-primary" />
                  <h3 className="text-lg font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{f.desc}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="px-4 py-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <h2 className="text-center text-3xl font-bold">Simple, transparent pricing</h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {plans.map((plan) => (
              <Card
                key={plan.name}
                className={`relative p-6 ${"popular" in plan && plan.popular ? "glow-blue border-primary/50" : ""}`}
              >
                {"popular" in plan && plan.popular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-xs font-medium">
                    Most Popular
                  </span>
                )}
                <CardHeader className="p-0">
                  <CardTitle>{plan.name}</CardTitle>
                  <p className="text-3xl font-bold mt-2">
                    {plan.price}
                    {plan.price !== "Custom" && <span className="text-sm text-muted-foreground">/mo</span>}
                  </p>
                </CardHeader>
                <CardContent className="mt-6 space-y-2 p-0">
                  {plan.features.map((f) => (
                    <p key={f} className="text-sm text-muted-foreground">✓ {f}</p>
                  ))}
                  <Link href="/signup" className="block mt-6">
                    <Button variant={"popular" in plan && plan.popular ? "default" : "outline"} className="w-full">
                      Get Started
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-24 sm:px-6">
        <div className="mx-auto max-w-3xl text-center glass rounded-2xl p-12 glow-green">
          <h2 className="text-3xl font-bold">Ready to forge your edge?</h2>
          <p className="mt-4 text-muted-foreground">
            Join thousands of quant traders building on QuantForge.
          </p>
          <Link href="/signup" className="inline-block mt-8">
            <Button size="lg" variant="success" className="gap-2">
              Create Free Account <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} QuantForge. All rights reserved.
      </footer>
    </div>
  );
}
