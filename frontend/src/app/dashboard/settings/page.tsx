"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth";
import { api, aiApi, billingApi } from "@/lib/api";

export default function SettingsPage() {
  const { user, fetchUser } = useAuthStore();
  const [twoFaEnabled, setTwoFaEnabled] = useState(false);
  const [qrUri, setQrUri] = useState("");
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [sessions, setSessions] = useState<Array<{ id: string; device_name: string; ip_address: string; last_used_at: string }>>([]);
  const [journal, setJournal] = useState<Array<{ date: string; reflection: string; lesson: string }>>([]);
  const [billing, setBilling] = useState<{
    plan: string;
    status: string;
    stripe_enabled: boolean;
    has_stripe_customer?: boolean;
  } | null>(null);

  useEffect(() => {
    if (user) setTwoFaEnabled(user.two_factor_enabled);
    api.get("/sessions").then((r) => setSessions(r.data)).catch(() => {});
    aiApi.tradeJournal().then((r) => setJournal(r.data)).catch(() => {});
    billingApi.subscription().then((r) => setBilling(r.data)).catch(() => {});
  }, [user]);

  const openPortal = async () => {
    try {
      const { data } = await billingApi.portal();
      if (data.portal_url) window.location.href = data.portal_url;
    } catch {
      setMessage("Billing portal unavailable — configure Stripe in .env");
    }
  };

  const setup2fa = async () => {
    const { data } = await api.post("/auth/2fa/setup");
    setQrUri(data.qr_uri);
    setMessage("Scan the URI in your authenticator app, then enter OTP below to enable.");
  };

  const enable2fa = async () => {
    await api.post("/auth/2fa/enable", { otp_code: otp });
    setMessage("2FA enabled successfully");
    fetchUser();
  };

  const disable2fa = async () => {
    await api.post("/auth/2fa/disable", { otp_code: otp });
    setMessage("2FA disabled");
    fetchUser();
  };

  return (
    <div>
      <DashboardHeader title="Settings" subtitle="Account, security, and preferences" />
      <div className="grid gap-6 max-w-2xl">
        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">Profile</h3>
          <Input defaultValue={user?.full_name} placeholder="Full name" disabled />
          <Input defaultValue={user?.email} placeholder="Email" disabled />
          <p className="text-xs text-muted-foreground">
            {user?.is_verified ? "✓ Email verified" : "Email not verified — check your inbox"}
          </p>
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">Billing & Subscription</h3>
          {billing ? (
            <>
              <p className="text-sm">
                Plan: <span className="font-medium capitalize text-primary">{billing.plan}</span>
                {" · "}
                Status: <span className="capitalize">{billing.status}</span>
              </p>
              {billing.has_stripe_customer ? (
                <Button variant="outline" onClick={openPortal}>Manage Billing</Button>
              ) : (
                <Link href="/pricing">
                  <Button variant="outline">Upgrade Plan</Button>
                </Link>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Loading billing...</p>
          )}
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">Two-Factor Authentication</h3>
          <p className="text-sm text-muted-foreground">
            Status: {twoFaEnabled ? "Enabled" : "Disabled"}
          </p>
          {!twoFaEnabled && (
            <Button variant="outline" onClick={setup2fa}>Setup 2FA</Button>
          )}
          {qrUri && (
            <p className="text-xs break-all text-muted-foreground bg-secondary/50 p-2 rounded">{qrUri}</p>
          )}
          <Input placeholder="6-digit OTP" value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} />
          {!twoFaEnabled ? (
            <Button onClick={enable2fa}>Enable 2FA</Button>
          ) : (
            <Button variant="danger" onClick={disable2fa}>Disable 2FA</Button>
          )}
          {message && <p className="text-sm text-emerald-400">{message}</p>}
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">Active Sessions</h3>
          {sessions.map((s) => (
            <div key={s.id} className="flex justify-between rounded-lg bg-secondary/50 px-4 py-3 text-sm">
              <span>{s.device_name || "Unknown device"}</span>
              <span className="text-muted-foreground">{s.ip_address}</span>
            </div>
          ))}
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">AI Trade Journal</h3>
          {journal.map((j, i) => (
            <div key={i} className="rounded-lg bg-secondary/50 p-4 text-sm">
              <p className="text-xs text-muted-foreground">{j.date}</p>
              <p className="mt-1">{j.reflection}</p>
              <p className="mt-2 text-primary text-xs">Lesson: {j.lesson}</p>
            </div>
          ))}
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="font-semibold">Trading Preferences</h3>
          <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
            <span className="text-sm">Default mode</span>
            <span className="text-sm font-medium text-primary">Paper Trading</span>
          </div>
          <div className="flex items-center justify-between rounded-lg bg-secondary/50 px-4 py-3">
            <span className="text-sm">Email trade alerts</span>
            <input type="checkbox" defaultChecked />
          </div>
        </Card>
      </div>
    </div>
  );
}
