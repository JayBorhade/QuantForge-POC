"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";

export default function AdminPage() {
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null);
  const [users, setUsers] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    api.get("/admin/analytics").then((r) => setAnalytics(r.data)).catch(() => null);
    api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => []);
  }, []);

  return (
    <div className="min-h-screen p-8 ml-0">
      <h1 className="text-2xl font-bold">Admin Panel</h1>
      <div className="mt-6 grid gap-4 sm:grid-cols-4">
        {analytics &&
          Object.entries(analytics).map(([k, v]) => (
            <Card key={k} className="p-4">
              <p className="text-xs text-muted-foreground capitalize">{k.replace(/_/g, " ")}</p>
              <p className="text-xl font-bold">{String(v)}</p>
            </Card>
          ))}
      </div>
      <Card className="mt-8 p-6">
        <h2 className="font-semibold mb-4">Users</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={String(u.id)} className="border-t border-white/5">
                  <td className="py-2">{String(u.email)}</td>
                  <td>{String(u.role)}</td>
                  <td>{u.is_banned ? "Banned" : "Active"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
