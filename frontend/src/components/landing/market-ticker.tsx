"use client";

const tickers = [
  { symbol: "AAPL", price: 198.42, change: 1.24 },
  { symbol: "BTC/USD", price: 67420, change: 2.81 },
  { symbol: "ETH/USD", price: 3521, change: -0.42 },
  { symbol: "NIFTY", price: 22456, change: 0.68 },
  { symbol: "RELIANCE", price: 2847, change: -0.15 },
  { symbol: "TSLA", price: 248.91, change: 3.12 },
  { symbol: "SOL/USD", price: 142.5, change: 4.55 },
];

export function MarketTicker() {
  const items = [...tickers, ...tickers];

  return (
    <div className="overflow-hidden border-y border-white/5 bg-card/30 py-2">
      <div className="flex animate-ticker gap-8 whitespace-nowrap">
        {items.map((t, i) => (
          <span key={`${t.symbol}-${i}`} className="inline-flex items-center gap-2 text-sm">
            <span className="font-mono font-medium text-foreground">{t.symbol}</span>
            <span className="text-muted-foreground">
              {t.price > 1000 ? t.price.toLocaleString() : t.price.toFixed(2)}
            </span>
            <span className={t.change >= 0 ? "text-emerald-400" : "text-red-400"}>
              {t.change >= 0 ? "+" : ""}
              {t.change}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
