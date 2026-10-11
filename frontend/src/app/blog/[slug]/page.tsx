"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Navbar } from "@/components/layout/navbar";
import { Card } from "@/components/ui/card";

const articles: Record<string, { title: string; published: string; intro: string; sections: Array<{ heading: string; body: string }> }> = {
  "ema-crossover-guide": {
    title: "Building an EMA Crossover Strategy",
    published: "May 15, 2026",
    intro: "An EMA crossover is a trend-following signal that compares a shorter exponential moving average with a longer one. It is a starting point for research, not a guarantee of profitable trades.",
    sections: [
      { heading: "Define the signal", body: "A common long-entry hypothesis is that the short EMA crosses above the long EMA. A reverse cross can be used as an exit signal. Specify the bar frequency, warm-up period, and handling of missing candles before testing." },
      { heading: "Backtest carefully", body: "Include realistic transaction costs, slippage assumptions, and the timing at which signals become executable. Avoid using future bars to make decisions on the current bar." },
      { heading: "Evaluate more than returns", body: "Review drawdown, trade count, exposure, turnover, and behavior across distinct market periods. Compare with a simple benchmark and reserve out-of-sample data for final evaluation." },
    ],
  },
  "risk-management": {
    title: "Position Sizing for Algo Traders",
    published: "May 10, 2026",
    intro: "Position sizing converts a risk budget into an order quantity. The right size depends on capital, stop distance, instrument specifications, liquidity, and portfolio-level exposure.",
    sections: [
      { heading: "Set risk before quantity", body: "A basic approach defines a maximum loss budget per trade, then divides that budget by the estimated loss per unit at the stop. Round down to valid lot sizes and reject quantities that violate minimums or risk limits." },
      { heading: "Account for portfolio exposure", body: "Per-trade sizing alone is not enough. Consider correlated positions, leverage, concentration, daily loss limits, and available buying power before an order is allowed." },
      { heading: "Test adverse conditions", body: "Model gaps, slippage, partial fills, and stop execution uncertainty. Backtests should not assume a stop always fills at its trigger price." },
    ],
  },
  "ai-sentiment": {
    title: "AI Sentiment Trading",
    published: "May 5, 2026",
    intro: "Sentiment signals can summarize noisy text, but they should be treated as uncertain features rather than direct instructions to trade.",
    sections: [
      { heading: "Build a traceable data pipeline", body: "Record source, publication time, ingestion time, deduplication rules, and the model version. Prevent data published after the simulated decision time from entering historical features." },
      { heading: "Validate signal quality", body: "Measure coverage, latency, class balance, calibration, and stability across sources and time periods. Compare the model against a simple baseline and check for look-ahead bias." },
      { heading: "Keep execution guarded", body: "Combine any sentiment score with explicit risk checks, position limits, stale-data handling, and an auditable decision record. A model score should never bypass broker or portfolio safeguards." },
    ],
  },
};

export default function BlogArticlePage() {
  const params = useParams<{ slug: string }>();
  const article = articles[params.slug];

  return (
    <div className="min-h-screen">
      <Navbar />
      <main id="page-content" tabIndex={-1} className="mx-auto max-w-3xl px-4 py-32 outline-none">
        {article ? (
          <article>
            <Link href="/blog" className="text-sm text-primary hover:underline">← Back to blog</Link>
            <p className="mt-8 text-xs text-muted-foreground">Published {article.published}</p>
            <h1 className="mt-3 text-4xl font-bold">{article.title}</h1>
            <p className="mt-5 text-lg text-muted-foreground">{article.intro}</p>
            <div className="mt-10 space-y-8">
              {article.sections.map((section) => (
                <section key={section.heading}>
                  <h2 className="text-xl font-semibold">{section.heading}</h2>
                  <p className="mt-3 leading-7 text-muted-foreground">{section.body}</p>
                </section>
              ))}
            </div>
            <Card className="mt-12 p-6">
              <h2 className="font-semibold">Continue exploring</h2>
              <p className="mt-2 text-sm text-muted-foreground">Review the platform documentation before using strategies with real capital.</p>
              <Link href="/docs" className="mt-3 inline-block text-sm text-primary hover:underline">Read documentation</Link>
            </Card>
          </article>
        ) : (
          <section aria-labelledby="article-not-found">
            <h1 id="article-not-found" className="text-3xl font-bold">Article not found</h1>
            <p className="mt-3 text-muted-foreground">This article does not exist or is no longer available.</p>
            <Link href="/blog" className="mt-5 inline-block text-primary hover:underline">Return to blog</Link>
          </section>
        )}
      </main>
    </div>
  );
}
