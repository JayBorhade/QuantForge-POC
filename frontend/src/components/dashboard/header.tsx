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
  const unread = notifications.filter((n) => !n.is_read).length;

  useEffect(() => {
    notificationApi.list().then((r) => setNotifications(r.data)).catch(() => []);
  }, []);

  const markAllRead = async () => {
    await notificationApi.markAllRead();
    setNotifications((n) => n.map((x) => ({ ...x, is_read: true })));
  };

  return (
    <div className="mb-8 flex items-start justify-between">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="relative">
        <button
          onClick={() => setOpen(!open)}
          className="relative rounded-lg border border-white/10 bg-card/50 p-2 hover:bg-secondary"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold">
              {unread}
            </span>
          )}
        </button>
        {open && (
          <div className="absolute right-0 z-50 mt-2 w-80 glass rounded-xl p-2 shadow-xl">
            <div className="flex items-center justify-between border-b border-white/5 px-3 py-2">
              <span className="text-sm font-medium">Notifications</span>
              {unread > 0 && (
                <button onClick={markAllRead} className="text-xs text-primary hover:underline">
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-64 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="p-4 text-sm text-muted-foreground">No notifications</p>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      "border-b border-white/5 px-3 py-3 last:border-0",
                      !n.is_read && "bg-primary/5"
                    )}
                  >
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{n.message}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
