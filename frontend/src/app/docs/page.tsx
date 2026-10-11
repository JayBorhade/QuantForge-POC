import { Navbar } from "@/components/layout/navbar";
import { CopyButton } from "@/components/ui/copy-button";

const quickStart = `# Clone and setup
cp .env.example .env
docker compose up -d

# API docs
http://localhost:8000/api/docs`;

export default function DocsPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main id="page-content" tabIndex={-1} className="mx-auto max-w-3xl px-4 py-32 outline-none">
        <h1 className="text-4xl font-bold text-gradient">Documentation</h1>
        <section className="mt-8 space-y-6 text-muted-foreground">
          <h2 className="text-xl font-semibold text-foreground">Quick Start</h2>
          <div className="relative">
            <div className="absolute right-2 top-2 z-10">
              <CopyButton value={quickStart} label="Copy quick-start commands" />
            </div>
            <pre className="glass overflow-x-auto rounded-lg p-4 pr-16 text-sm">{quickStart}</pre>
          </div>
          <h2 className="text-xl font-semibold text-foreground">Authentication</h2>
          <p>JWT access tokens with rotating refresh tokens stored in httpOnly cookies.</p>
          <h2 className="text-xl font-semibold text-foreground">Strategies</h2>
          <p>Built-in: EMA Crossover, RSI Mean Reversion, VWAP Intraday, Breakout, AI Sentiment.</p>
        </section>
      </main>
    </div>
  );
}
