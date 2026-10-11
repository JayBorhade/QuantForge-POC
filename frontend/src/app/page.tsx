"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Bot, Brain, LineChart, Shield, Zap, FlaskConical, Settings2 } from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const features = [
  { icon: LineChart, title: "Backtesting", desc: "Evaluate strategies with performance metrics, equity curves, and trade history." },
  { icon: Bot, title: "Strategy workflows", desc: "Create and manage strategies with a paper-trading workflow." },
  { icon: Brain, title: "AI analytics", desc: "Explore the configured market-summary, risk-analysis, and portfolio-insight tools." },
  { icon: Shield, title: "Account security", desc: "Authentication, refresh-token handling, and role-aware application access." },
  { icon: Zap, title: "Broker adapters", desc: "The repository includes adapters for Zerodha Kite, Binance, and Angel One." },
  { icon: BarChart3, title: "Portfolio and risk", desc: "Review portfolio data, risk limits, and performance views." },
];

const capabilities = [
  { label: "Built-in strategy templates", value: "5 algorithms" },
  { label: "Listed broker adapters", value: "3 integrations" },
  { label: "Strategy evaluation", value: "Backtesting" },
  { label: "Safe development path", value: "Paper workflow" },
];

const pillars = [
  { title: "Build strategies", description: "Start from one of the included algorithm templates and configure a strategy for your workflow.", href: "/dashboard/strategies", action: "Explore strategies" },
  { title: "Evaluate before deployment", description: "Use backtesting and performance views to inspect strategy behavior before making execution decisions.", href: "/dashboard/backtest", action: "Explore backtesting" },
  { title: "Understand the platform", description: "Review setup instructions, authentication notes, and the available integrations.", href: "/docs", action: "Read documentation" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main id="page-content" tabIndex={-1} className="outline-none">
        <section className="relative px-4 pb-24 pt-32 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <div className="grid items-center gap-12 lg:grid-cols-2">
              <motion.div initial={{ opacity: 0, x: -30 }} animate={{ opacity: 1, x: 0 }}>
                <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary">
                  <Zap aria-hidden="true" className="h-4 w-4" /> Algorithmic trading workspace
                </p>
                <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                  Build, Backtest,{" "}
                  <span className="text-gradient">Automate, Scale</span>
                </h1>
                <p className="mt-6 max-w-xl text-lg text-muted-foreground">
                  QuantForge brings strategy configuration, historical evaluation, portfolio analytics, and broker-adapter workflows into one workspace.
                </p>
                <div className="mt-8 flex flex-wrap gap-4">
                  <Link href="/signup"><Button size="lg" className="gap-2">Create an account <ArrowRight aria-hidden="true" className="h-4 w-4" /></Button></Link>
                  <Link href="/docs"><Button variant="outline" size="lg">View documentation</Button></Link>
                </div>
              </motion.div>

              <Card className="p-6 sm:p-8">
                <p className="text-sm font-semibold text-primary">Workspace overview</p>
                <h2 className="mt-2 text-2xl font-bold">A connected research workflow</h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Explore the application's real strategy, testing, portfolio, risk, and integration modules. This preview intentionally contains no simulated prices or performance figures.
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {[
                    { icon: Bot, label: "Strategy builder" },
                    { icon: FlaskConical, label: "Backtesting" },
                    { icon: BarChart3, label: "Portfolio analytics" },
                    { icon: Shield, label: "Risk controls" },
                    { icon: Zap, label: "Broker adapters" },
                    { icon: Settings2, label: "Deployment settings" },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-3 rounded-lg border border-border bg-secondary/40 p-3">
                      <item.icon aria-hidden="true" className="h-5 w-5 shrink-0 text-primary" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </section>

        <section aria-label="Platform capabilities" className="border-y border-white/5 bg-card/20 py-12">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-8 px-4 sm:grid-cols-4 sm:px-6">
            {capabilities.map((capability) => (
              <div key={capability.label} className="text-center">
                <p className="text-2xl font-bold text-gradient">{capability.value}</p>
                <p className="mt-1 text-sm text-muted-foreground">{capability.label}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-4 py-24 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <h2 className="text-center text-3xl font-bold">Tools for systematic trading workflows</h2>
            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature, index) => (
                <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08 }} viewport={{ once: true }}>
                  <Card className="glass-hover h-full p-6">
                    <feature.icon aria-hidden="true" className="mb-4 h-8 w-8 text-primary" />
                    <h3 className="text-lg font-semibold">{feature.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{feature.desc}</p>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 py-24 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">
            <h2 className="text-center text-3xl font-bold">A clear path through the platform</h2>
            <p className="mt-3 text-center text-sm text-muted-foreground">Current subscription prices are provided by the billing service on the pricing page.</p>
            <div className="mt-12 grid gap-6 md:grid-cols-3">
              {pillars.map((pillar) => (
                <Card key={pillar.title} className="glass-hover flex h-full flex-col p-6">
                  <h3 className="text-lg font-semibold">{pillar.title}</h3>
                  <p className="mt-3 flex-1 text-sm text-muted-foreground">{pillar.description}</p>
                  <Link href={pillar.href} className="mt-6"><Button variant="outline" className="w-full">{pillar.action}</Button></Link>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="px-4 py-24 sm:px-6">
          <div className="mx-auto max-w-3xl rounded-2xl border border-border bg-card p-12 text-center">
            <h2 className="text-3xl font-bold">Ready to explore QuantForge?</h2>
            <p className="mt-4 text-muted-foreground">Create an account to access the workspace, or review the documentation first.</p>
            <Link href="/signup" className="mt-8 inline-block">
              <Button size="lg" variant="success" className="gap-2">Create account <ArrowRight aria-hidden="true" className="h-4 w-4" /></Button>
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5 py-8 text-center text-sm text-muted-foreground">
        © {new Date().getFullYear()} QuantForge. All rights reserved.
      </footer>
    </div>
  );
}
