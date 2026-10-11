"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Bot,
  FlaskConical,
  LayoutDashboard,
  Link2,
  LogOut,
  Menu,
  Rocket,
  Settings,
  Shield,
  Terminal,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const links = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
  { href: "/dashboard/live", icon: Activity, label: "Live Trading" },
  { href: "/dashboard/strategies", icon: Bot, label: "Strategies" },
  { href: "/dashboard/backtest", icon: FlaskConical, label: "Backtesting" },
  { href: "/dashboard/portfolio", icon: BarChart3, label: "Portfolio" },
  { href: "/dashboard/risk", icon: Shield, label: "Risk" },
  { href: "/dashboard/brokers", icon: Link2, label: "Brokers" },
  { href: "/dashboard/deploy", icon: Rocket, label: "Deploy" },
  { href: "/dashboard/logs", icon: Terminal, label: "Logs" },
  { href: "/dashboard/settings", icon: Settings, label: "Settings" },
];

export function DashboardSidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuthStore();
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const wasMobileOpenRef = useRef(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) {
      if (wasMobileOpenRef.current) menuButtonRef.current?.focus();
      wasMobileOpenRef.current = false;
      return;
    }
    wasMobileOpenRef.current = true;
    sidebarRef.current?.querySelector<HTMLElement>("[data-drawer-close]")?.focus();
    const desktopQuery = window.matchMedia("(min-width: 768px)");
    const onViewportChange = (event: MediaQueryListEvent) => {
      if (event.matches) setMobileOpen(false);
    };
    desktopQuery.addEventListener("change", onViewportChange);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        menuButtonRef.current?.focus();
        return;
      }
      if (event.key === "Tab" && sidebarRef.current) {
        const focusable = Array.from(sidebarRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        ));
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
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      desktopQuery.removeEventListener("change", onViewportChange);
    };
  }, [mobileOpen]);

  const signOut = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <>
      <button
        type="button"
        ref={menuButtonRef}
        tabIndex={mobileOpen ? -1 : 0}
        aria-hidden={mobileOpen || undefined}
        className="ux-icon-button fixed left-4 top-4 z-[70] md:hidden"
        onClick={() => setMobileOpen((value) => !value)}
        aria-label={mobileOpen ? "Close dashboard navigation" : "Open dashboard navigation"}
        aria-expanded={mobileOpen}
        aria-controls="dashboard-navigation"
      >
        {mobileOpen ? <X aria-hidden="true" className="h-5 w-5" /> : <Menu aria-hidden="true" className="h-5 w-5" />}
      </button>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close dashboard navigation overlay"
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        ref={sidebarRef}
        id="dashboard-navigation"
        role={mobileOpen ? "dialog" : undefined}
        aria-label="Dashboard navigation"
        aria-modal={mobileOpen ? true : undefined}
        className={cn(
          "fixed left-0 top-0 z-50 flex h-dvh w-64 flex-col border-r border-white/5 bg-card/95 backdrop-blur-xl transition-transform duration-200 md:translate-x-0",
          mobileOpen ? "translate-x-0 visible" : "-translate-x-full invisible md:visible"
        )}
      >
        <div className="flex h-16 items-center justify-between gap-2 border-b border-white/5 px-6">
          <div className="flex items-center gap-2">
            <Activity aria-hidden="true" className="h-6 w-6 text-primary" />
            <span className="font-bold">Quant<span className="text-primary">Forge</span></span>
          </div>
          <button type="button" data-drawer-close className="ux-icon-button md:hidden" aria-label="Close dashboard navigation" onClick={() => setMobileOpen(false)}>
            <X aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>

        <nav aria-label="Dashboard navigation" className="flex-1 space-y-1 overflow-y-auto p-4">
          {links.map((link) => {
            const active = pathname === link.href || (link.href !== "/dashboard" && pathname.startsWith(`${link.href}/`));
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "bg-primary/20 text-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <link.icon aria-hidden="true" className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
          {user?.role === "admin" && (
            <Link
              href="/admin"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-amber-500 hover:bg-secondary"
            >
              <Shield aria-hidden="true" className="h-4 w-4" />
              Admin
            </Link>
          )}
        </nav>

        <div className="border-t border-white/5 p-4">
          <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          <button
            type="button"
            onClick={signOut}
            className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <LogOut aria-hidden="true" className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
