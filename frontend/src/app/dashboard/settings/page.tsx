"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DashboardHeader } from "@/components/dashboard/header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth";
import { api, aiApi, billingApi } from "@/lib/api";

type Session = { id: string; device_name: string; ip_address: string; last_used_at: string };
type JournalEntry = { date: string; reflection: string; lesson: string };
type Billing = { plan: string; status: string; stripe_enabled: boolean; has_stripe_customer?: boolean };

export default function SettingsPage() {
  const { user, fetchUser } = useAuthStore();
  const [twoFaEnabled, setTwoFaEnabled] = useState(false);
  const [qrUri, setQrUri] = useState("");
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [securityAction, setSecurityAction] = useState<"setup" | "enable" | "disable" | null>(null);
  const [billingLoading, setBillingLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [journalLoading, setJournalLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState("");
  const [journalError, setJournalError] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [billing, setBilling] = useState<Billing | null>(null);

  useEffect(() => {
    let mounted = true;
    if (user) setTwoFaEnabled(user.two_factor_enabled);

    api.get("/sessions")
      .then((response) => { if (mounted) setSessions(Array.isArray(response.data) ? response.data : []); })
      .catch(() => { if (mounted) setSessionsError("Active sessions could not be loaded."); })
      .finally(() => { if (mounted) setSessionsLoading(false); });

    aiApi.tradeJournal()
      .then((response) => { if (mounted) setJournal(Array.isArray(response.data) ? response.data : []); })
      .catch(() => { if (mounted) setJournalError("The trade journal could not be loaded."); })
      .finally(() => { if (mounted) setJournalLoading(false); });

    billingApi.subscription()
      .then((response) => { if (mounted) setBilling(response.data ?? null); })
      .catch(() => { if (mounted) setBilling(null); })
      .finally(() => { if (mounted) setBillingLoading(false); });

    return () => { mounted = false; };
  }, [user]);

  const openPortal = async () => {
    if (portalLoading) return;
    setPortalLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await billingApi.portal();
      if (!data.portal_url) {
        setError("The billing portal is not available for this account.");
        return;
      }
      const portalUrl = new URL(data.portal_url);
      if (portalUrl.protocol !== "https:" || !["billing.stripe.com", "checkout.stripe.com"].includes(portalUrl.hostname)) {
        setError("The billing service returned an unexpected destination. Contact support.");
        return;
      }
      window.location.assign(portalUrl.href);
    } catch {
      setError("The billing portal could not be opened. Check your connection and billing configuration.");
    } finally {
      setPortalLoading(false);
    }
  };

  const setup2fa = async () => {
    if (securityAction) return;
    setSecurityAction("setup");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post("/auth/2fa/setup");
      if (typeof data.qr_uri !== "string" || !data.qr_uri.startsWith("otpauth://")) {
        setError("The authenticator setup response was invalid. Please try again.");
        return;
      }
      setQrUri(data.qr_uri);
      setMessage("Add this authenticator setup URI to your authenticator app, then enter the generated code to enable two-factor authentication.");
    } catch {
      setError("Two-factor setup could not be started. Try again.");
    } finally {
      setSecurityAction(null);
    }
  };

  const enable2fa = async () => {
    if (securityAction) return;
    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the six-digit code from your authenticator app.");
      return;
    }
    setSecurityAction("enable");
    setError("");
    setMessage("");
    try {
      await api.post("/auth/2fa/enable", { otp_code: otp });
      setTwoFaEnabled(true);
      setQrUri("");
      setOtp("");
      setMessage("Two-factor authentication enabled successfully.");
      void fetchUser();
    } catch {
      setError("Two-factor authentication could not be enabled. Verify the code and try again.");
    } finally {
      setSecurityAction(null);
    }
  };

  const disable2fa = async () => {
    if (securityAction) return;
    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the six-digit code from your authenticator app.");
      return;
    }
    if (!window.confirm("Disable two-factor authentication? This reduces account protection. You will need your authenticator code to confirm.")) return;
    setSecurityAction("disable");
    setError("");
    setMessage("");
    try {
      await api.post("/auth/2fa/disable", { otp_code: otp });
      setTwoFaEnabled(false);
      setOtp("");
      setMessage("Two-factor authentication disabled.");
      void fetchUser();
    } catch {
      setError("Two-factor authentication could not be disabled. Verify the code and try again.");
    } finally {
      setSecurityAction(null);
    }
  };

  return (
    <div>
      <DashboardHeader title="Settings" subtitle="Account, security, and preferences" />
      {error && <p className="mb-4 rounded-lg border border-red-500/30 p-3 text-sm text-red-500" role="alert" aria-live="assertive">{error}</p>}
      {message && <p className="mb-4 rounded-lg border border-primary/20 p-3 text-sm text-muted-foreground" role="status" aria-live="polite">{message}</p>}
      <div className="grid max-w-2xl gap-6">
        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">Profile</h2>
          <div>
            <label htmlFor="settings-full-name" className="mb-1 block text-sm text-muted-foreground">Full name</label>
            <Input id="settings-full-name" autoComplete="name" value={user?.full_name ?? ""} disabled />
          </div>
          <div>
            <label htmlFor="settings-email" className="mb-1 block text-sm text-muted-foreground">Email address</label>
            <Input id="settings-email" autoComplete="email" value={user?.email ?? ""} disabled />
          </div>
          <p className="text-xs text-muted-foreground">
            {user?.is_verified ? "Email verified" : "Email not verified — check your inbox"}
          </p>
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">Billing &amp; Subscription</h2>
          {billingLoading ? (
            <p className="text-sm text-muted-foreground" role="status">Loading subscription…</p>
          ) : billing ? (
            <>
              <p className="text-sm">
                Plan: <span className="font-medium capitalize text-primary">{billing.plan}</span>
                {" · "}
                Status: <span className="capitalize">{billing.status}</span>
              </p>
              {billing.has_stripe_customer ? (
                <Button variant="outline" onClick={() => void openPortal()} disabled={portalLoading}>
                  {portalLoading ? "Opening billing…" : "Manage Billing"}
                </Button>
              ) : (
                <Link href="/pricing"><Button variant="outline">View plans</Button></Link>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Subscription information is unavailable. Reload the page or try again later.</p>
          )}
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">Two-Factor Authentication</h2>
          <p className="text-sm text-muted-foreground">Status: {twoFaEnabled ? "Enabled" : "Disabled"}</p>
          {!twoFaEnabled && (
            <Button variant="outline" onClick={() => void setup2fa()} disabled={securityAction !== null}>
              {securityAction === "setup" ? "Preparing setup…" : "Setup 2FA"}
            </Button>
          )}
          {qrUri && (
            <div>
              <label htmlFor="authenticator-uri" className="mb-1 block text-sm text-muted-foreground">Authenticator setup URI (keep private)</label>
              <textarea id="authenticator-uri" readOnly value={qrUri} className="w-full break-all rounded-lg border border-border bg-secondary/50 p-3 text-xs text-foreground" rows={3} />
            </div>
          )}
          <div>
            <label htmlFor="authenticator-otp" className="mb-1 block text-sm text-muted-foreground">Six-digit authenticator code</label>
            <Input id="authenticator-otp" name="otp" inputMode="numeric" autoComplete="one-time-code" placeholder="000000" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))} maxLength={6} />
          </div>
          {!twoFaEnabled ? (
            <Button onClick={() => void enable2fa()} disabled={securityAction !== null || !qrUri}>
              {securityAction === "enable" ? "Enabling…" : "Enable 2FA"}
            </Button>
          ) : (
            <Button variant="danger" onClick={() => void disable2fa()} disabled={securityAction !== null}>
              {securityAction === "disable" ? "Disabling…" : "Disable 2FA"}
            </Button>
          )}
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">Active Sessions</h2>
          {sessionsLoading ? <p className="text-sm text-muted-foreground" role="status">Loading sessions…</p> : sessionsError ? <p className="text-sm text-red-500" role="alert">{sessionsError}</p> : sessions.length ? (
            sessions.map((session) => (
              <div key={session.id} className="flex flex-wrap justify-between gap-2 rounded-lg bg-secondary/50 px-4 py-3 text-sm">
                <span>{session.device_name || "Unknown device"}</span>
                <span className="text-muted-foreground">{session.ip_address}</span>
              </div>
            ))
          ) : <p className="text-sm text-muted-foreground">No active sessions were returned.</p>}
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">AI Trade Journal</h2>
          {journalLoading ? <p className="text-sm text-muted-foreground" role="status">Loading trade journal…</p> : journalError ? <p className="text-sm text-red-500" role="alert">{journalError}</p> : journal.length ? (
            journal.map((entry, index) => (
              <div key={`${entry.date}-${index}`} className="rounded-lg bg-secondary/50 p-4 text-sm">
                <p className="text-xs text-muted-foreground">{entry.date}</p>
                <p className="mt-1">{entry.reflection}</p>
                <p className="mt-2 text-xs text-primary">Lesson: {entry.lesson}</p>
              </div>
            ))
          ) : <p className="text-sm text-muted-foreground">No trade journal entries are available.</p>}
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">Trading Preferences</h2>
          <div className="flex items-center justify-between gap-4 rounded-lg bg-secondary/50 px-4 py-3">
            <span className="text-sm">Default mode</span>
            <span className="text-sm font-medium text-primary">Paper Trading</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Email trade-alert preferences are not configurable in this version; no unsaved toggle is shown.
          </p>
        </Card>
      </div>
    </div>
  );
}
