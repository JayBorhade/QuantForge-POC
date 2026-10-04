import { Navbar } from "@/components/layout/navbar";

export default function DocsPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="mx-auto max-w-3xl px-4 py-32 prose prose-invert">
        <h1 className="text-4xl font-bold text-gradient">Documentation</h1>
        <section className="mt-8 space-y-6 text-muted-foreground">
          <h2 className="text-xl font-semibold text-foreground">Quick Start</h2>
          <pre className="glass rounded-lg p-4 text-sm overflow-x-auto">
{`# Clone and setup
cp .env.example .env
docker compose up -d

# API docs
http://localhost:8000/api/docs`}
          </pre>
          <h2 className="text-xl font-semibold text-foreground">Authentication</h2>
          <p>JWT access tokens with rotating refresh tokens stored in httpOnly cookies.</p>
          <h2 className="text-xl font-semibold text-foreground">Strategies</h2>
          <p>Built-in: EMA Crossover, RSI Mean Reversion, VWAP Intraday, Breakout, AI Sentiment.</p>
        </section>
      </div>
    </div>
  );
}
