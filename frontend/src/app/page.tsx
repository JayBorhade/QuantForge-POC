export default function Home() {
  return (
    <main className="min-h-screen bg-forge-black px-6 py-12">
      <div className="mx-auto max-w-6xl">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-forge-blue">
          QuantForge POC
        </p>
        <h1 className="text-5xl font-bold tracking-tight">Build. Backtest. Analyze. Paper Trade.</h1>
        <p className="mt-5 max-w-2xl text-lg text-slate-400">
          A focused proof of concept for algorithmic strategy research and paper trading.
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-4">
          {[
            ["01", "Strategies", "EMA Crossover and RSI Mean Reversion"],
            ["02", "Backtesting", "Historical strategy evaluation"],
            ["03", "Analytics", "Performance and equity-curve analysis"],
            ["04", "Paper Trading", "Controlled execution before live markets"],
          ].map(([number, title, description]) => (
            <div key={number} className="rounded-2xl border border-forge-border bg-forge-panel p-5">
              <span className="text-sm text-forge-blue">{number}</span>
              <h2 className="mt-6 text-xl font-semibold">{title}</h2>
              <p className="mt-2 text-sm text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
