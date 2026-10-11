"use client";

import Link from "next/link";
import { useState } from "react";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch {
      setError("We couldn't submit the request. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main id="page-content" tabIndex={-1} className="flex min-h-screen items-center justify-center px-4 outline-none">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold">Reset password</h1>
        {sent ? (
          <p className="mt-4 text-muted-foreground" role="status" aria-live="polite">
            If an account exists for {email}, you will receive a reset link shortly.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="forgot-email" className="mb-1 block text-sm font-medium">Email</label>
              <Input id="forgot-email" name="email" autoComplete="email" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            {error && <p className="text-sm text-red-500" role="alert">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Sending request…" : "Send Reset Link"}
            </Button>
          </form>
        )}
        <Link href="/login" className="mt-6 block text-sm text-primary hover:underline">Back to login</Link>
      </Card>
    </main>
  );
}
