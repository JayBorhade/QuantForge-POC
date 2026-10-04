import { Navbar } from "@/components/layout/navbar";
import { Card } from "@/components/ui/card";
import Link from "next/link";

const posts = [
  { slug: "ema-crossover-guide", title: "Building an EMA Crossover Strategy", date: "May 15, 2026", excerpt: "Learn how to configure and backtest EMA crossover on QuantForge." },
  { slug: "risk-management", title: "Position Sizing for Algo Traders", date: "May 10, 2026", excerpt: "Dynamic risk allocation and ATR-based stop losses explained." },
  { slug: "ai-sentiment", title: "AI Sentiment Trading in 2026", date: "May 5, 2026", excerpt: "Combining news, Reddit, and social signals for systematic edge." },
];

export default function BlogPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="mx-auto max-w-3xl px-4 py-32">
        <h1 className="text-4xl font-bold">Blog</h1>
        <div className="mt-12 space-y-6">
          {posts.map((p) => (
            <Card key={p.slug} className="glass-hover p-6">
              <p className="text-xs text-muted-foreground">{p.date}</p>
              <Link href={`/blog/${p.slug}`}>
                <h2 className="mt-2 text-xl font-semibold hover:text-primary">{p.title}</h2>
              </Link>
              <p className="mt-2 text-sm text-muted-foreground">{p.excerpt}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
