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
  Rocket,
  Settings,
  Shield,
  Terminal,
} from "lucide-react";
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

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-white/5 bg-card/50 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-2 border-b border-white/5 px-6">
        <Activity className="h-6 w-6 text-primary" />
        <span className="font-bold">Quant<span className="text-primary">Forge</span></span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        {links.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-primary/20 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
        {user?.role === "admin" && (
          <Link
            href="/admin"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-amber-400 hover:bg-secondary"
          >
            <Shield className="h-4 w-4" />
            Admin
          </Link>
        )}
      </nav>

      <div className="border-t border-white/5 p-4">
        <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
        <button
          onClick={() => logout().then(() => (window.location.href = "/login"))}
          className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>
    </aside>
  );
}
