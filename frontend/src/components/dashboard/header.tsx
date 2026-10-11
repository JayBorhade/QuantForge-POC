"use client";

import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { notificationApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Notification {
  id: string;
  title: string;
  message: string;
  is_read: boolean;
  type: string;
}

export function DashboardHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [markingRead, setMarkingRead] = useState(false);
  const [error, setError] = useState("");
  const unread = notifications.filter((notification) => !notification.is_read).length;

  useEffect(() => {
    notificationApi.list()
      .then((response) => setNotifications(Array.isArray(response.data) ? response.data : []))
      .catch(() => setError("Notifications could not be loaded."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const markAllRead = async () => {
    if (markingRead || unread === 0) return;
    setMarkingRead(true);
    setError("");
    try {
      await notificationApi.markAllRead();
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })));
    } catch {
      setError("Notifications could not be marked as read. Try again.");
    } finally {
      setMarkingRead(false);
    }
  };

  return (
    <div className="mb-8 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="relative rounded-lg border border-white/10 bg-card/50 p-2 hover:bg-secondary"
          aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
          aria-expanded={open}
          aria-controls="dashboard-notifications"
        >
          <Bell aria-hidden="true" className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </button>
        {open && (
          <section id="dashboard-notifications" aria-label="Notifications" className="glass absolute right-0 z-50 mt-2 w-[min(20rem,calc(100vw-2rem))] rounded-xl p-2 shadow-xl">
            <div className="flex items-center justify-between border-b border-white/5 px-3 py-2">
              <span className="text-sm font-medium">Notifications</span>
              {unread > 0 && (
                <button type="button" onClick={() => void markAllRead()} disabled={markingRead} className="text-xs text-primary hover:underline disabled:opacity-50">
                  {markingRead ? "Marking…" : "Mark all read"}
                </button>
              )}
            </div>
            {error && <p className="px-3 py-2 text-xs text-red-500" role="alert">{error}</p>}
            <div className="max-h-64 overflow-y-auto" aria-live="polite">
              {loading ? (
                <p className="p-4 text-sm text-muted-foreground" role="status">Loading notifications…</p>
              ) : notifications.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">No notifications</p>
              ) : (
                notifications.map((notification) => (
                  <div key={notification.id} className={cn("border-b border-white/5 px-3 py-3 last:border-0", !notification.is_read && "bg-primary/5")}>
                    <p className="text-sm font-medium">{notification.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{notification.message}</p>
                  </div>
                ))
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
