"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUp, Search, Sun, Moon, X, ExternalLink } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const searchablePages = [
  { title: "Home", href: "/", description: "QuantForge overview and platform introduction" },
  { title: "Features", href: "/features", description: "Strategy builder, backtesting, broker adapters, risk management and analytics" },
  { title: "Pricing", href: "/pricing", description: "Plans, billing and subscription information" },
  { title: "Documentation", href: "/docs", description: "Quick start, authentication and built-in strategies" },
  { title: "Blog", href: "/blog", description: "Product articles and updates" },
  { title: "Contact", href: "/contact", description: "Contact and support information" },
  { title: "Log in", href: "/login", description: "Sign in to your QuantForge account" },
  { title: "Create account", href: "/signup", description: "Register a QuantForge account" },
  { title: "Dashboard", href: "/dashboard", description: "Portfolio overview and trading workspace" },
  { title: "Live trading", href: "/dashboard/live", description: "Live trading panel and execution feed" },
  { title: "Strategies", href: "/dashboard/strategies", description: "Create and manage trading strategies" },
  { title: "Backtesting", href: "/dashboard/backtest", description: "Run backtests and review strategy results" },
  { title: "Portfolio", href: "/dashboard/portfolio", description: "Portfolio valuation and performance analytics" },
  { title: "Risk", href: "/dashboard/risk", description: "Risk limits, exposure and risk events" },
  { title: "Broker connections", href: "/dashboard/brokers", description: "Manage connected broker integrations" },
  { title: "Deployments", href: "/dashboard/deploy", description: "Manage bot deployments" },
  { title: "System logs", href: "/dashboard/logs", description: "Review strategy, audit and system logs" },
  { title: "Settings", href: "/dashboard/settings", description: "Account and application settings" },
];

export function ProductUxControls() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [showTop, setShowTop] = useState(false);
  const [progress, setProgress] = useState(0);
  const searchDialogRef = useRef<HTMLElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const isMarketing = ["/", "/features", "/pricing", "/docs", "/blog", "/contact"].includes(pathname) || pathname.startsWith("/blog/");
  const hasReadingProgress = pathname === "/docs" || pathname.startsWith("/blog");

  useEffect(() => {
    let stored: string | null = null;
    try { stored = window.localStorage.getItem("quantforge-theme"); } catch { /* Use the system preference when storage is unavailable. */ }
    const initial = stored === "light" || stored === "dark"
      ? stored
      : window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
    document.documentElement.style.colorScheme = initial;
  }, []);

  useEffect(() => {
    const onScroll = () => {
      setShowTop(window.scrollY > 480);
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(100, Math.max(0, (window.scrollY / max) * 100)) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [pathname]);

  useEffect(() => {
    if (!searchOpen) {
      previousFocusRef.current?.focus();
      return;
    }
    searchInputRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSearchOpen(false);
        return;
      }
      if (event.key === "Tab" && searchDialogRef.current) {
        const focusable = Array.from(
          searchDialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')
        );
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [searchOpen]);

  const results = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return searchablePages.slice(0, 6);
    return searchablePages.filter((page) =>
      `${page.title} ${page.description} ${page.href}`.toLowerCase().includes(term)
    ).slice(0, 8);
  }, [query]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    document.documentElement.style.colorScheme = next;
    try { window.localStorage.setItem("quantforge-theme", next); } catch { /* The current page theme still updates if storage is blocked. */ }
  };

  const contentTarget = pathname.startsWith("/dashboard") ? "#dashboard-main-content" : "#page-content";

  return (
    <>
      <a
        href={contentTarget}
        className="skip-link"
        onClick={(event) => {
          const target = document.querySelector(contentTarget);
          if (target instanceof HTMLElement) {
            event.preventDefault();
            target.focus();
            target.scrollIntoView({ block: "start" });
          }
        }}
      >
        Skip to content
      </a>

      {hasReadingProgress && (
        <div className="fixed left-0 right-0 top-0 z-[110] h-1 bg-transparent" role="progressbar" aria-label="Reading progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)}>
          <div className="h-full bg-primary transition-[width] duration-100" style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className={`fixed right-4 z-[60] flex items-center gap-2 ${pathname.startsWith("/dashboard") ? "top-4" : "top-20"}`}>
        <button type="button" onClick={(event) => { previousFocusRef.current = event.currentTarget; setSearchOpen(true); setQuery(""); }} aria-label="Search site" title="Search site" className="ux-icon-button">
          <Search aria-hidden="true" className="h-4 w-4" />
        </button>
        <button type="button" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"} title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"} className="ux-icon-button">
          {theme === "dark" ? <Sun aria-hidden="true" className="h-4 w-4" /> : <Moon aria-hidden="true" className="h-4 w-4" />}
        </button>
      </div>

      {searchOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/60 px-4 pt-[12vh]" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSearchOpen(false); }}>
          <section ref={searchDialogRef} role="dialog" aria-modal="true" aria-labelledby="site-search-title" className="w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-card p-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <Search aria-hidden="true" className="h-5 w-5 text-muted-foreground" />
              <h2 id="site-search-title" className="sr-only">Search QuantForge</h2>
              <input ref={searchInputRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search pages and features…" aria-label="Search pages and features" className="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none" />
              {query && <button type="button" className="ux-icon-button" aria-label="Clear search" onClick={() => { setQuery(""); searchInputRef.current?.focus(); }}><X aria-hidden="true" className="h-4 w-4" /></button>}
              <button type="button" className="ux-icon-button" aria-label="Close search" onClick={() => setSearchOpen(false)}><X aria-hidden="true" className="h-4 w-4" /></button>
            </div>
            <div className="mt-3 max-h-[55vh] overflow-y-auto" aria-live="polite">
              {results.length ? results.map((page) => (
                <Link key={page.href} href={page.href} onClick={() => setSearchOpen(false)} className="block rounded-lg px-3 py-3 hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <span className="block text-sm font-medium">{page.title}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">{page.description}</span>
                </Link>
              )) : <p className="px-3 py-6 text-sm text-muted-foreground">No matching pages. Try a different search term.</p>}
            </div>
            <p className="mt-2 border-t border-border pt-3 text-xs text-muted-foreground">Searches known application pages and features. Private records are not indexed.</p>
          </section>
        </div>
      )}

      {showTop && (
        <button type="button" className={`fixed bottom-5 right-5 z-40 ux-icon-button shadow-lg ${isMarketing ? "bottom-20" : ""}`} aria-label="Back to top" title="Back to top" onClick={() => window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" })}>
          <ArrowUp aria-hidden="true" className="h-4 w-4" />
        </button>
      )}

      {isMarketing && (
        <Link href="/contact" className="fixed bottom-5 right-5 z-30 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-card px-4 py-3 text-sm font-medium shadow-lg hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          Contact <ExternalLink aria-hidden="true" className="h-4 w-4" />
        </Link>
      )}
    </>
  );
}
