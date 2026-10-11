"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

function ResetForm() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) return;
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await authApi.resetPassword({ token, password, confirm_password: confirm });
      setDone(true);
    } catch {
      setError("Password reset failed. The link may be invalid or expired.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return <p className="text-red-500" role="alert">Missing reset token. Request a new link.</p>;
  }

  if (done) {
    return (
      <div className="text-center">
        <p className="text-emerald-500" role="status" aria-live="polite">Password reset successfully.</p>
        <Link href="/login" className="mt-4 inline-block text-primary hover:underline">Sign in</Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="new-password" className="mb-1 block text-sm font-medium">New password</label>
        <Input id="new-password" name="new-password" autoComplete="new-password" type="password" placeholder="New password" value={password} onChange={(event) => setPassword(event.target.value)} required />
      </div>
      <div>
        <label htmlFor="confirm-password" className="mb-1 block text-sm font-medium">Confirm password</label>
        <Input id="confirm-password" name="confirm-password" autoComplete="new-password" type="password" placeholder="Confirm password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required />
      </div>
      {error && <p className="text-sm text-red-500" role="alert" aria-live="assertive">{error}</p>}
      <Button type="submit" className="w-full" disabled={loading}>{loading ? "Resetting…" : "Reset Password"}</Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <main id="page-content" tabIndex={-1} className="flex min-h-screen items-center justify-center px-4 outline-none">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold">Set new password</h1>
        <Suspense fallback={<p className="mt-4 text-muted-foreground" role="status">Loading reset form…</p>}>
          <div className="mt-6"><ResetForm /></div>
        </Suspense>
      </Card>
    </main>
  );
}
