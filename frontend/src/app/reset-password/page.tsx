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
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    try {
      await authApi.resetPassword({ token, password, confirm_password: confirm });
      setDone(true);
    } catch {
      setError("Invalid or expired reset link");
    }
  };

  if (!token) {
    return <p className="text-red-400">Missing reset token. Request a new link.</p>;
  }

  if (done) {
    return (
      <div className="text-center">
        <p className="text-emerald-400">Password reset successfully.</p>
        <Link href="/login" className="mt-4 inline-block text-primary hover:underline">Sign in</Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input type="password" placeholder="New password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      <Input type="password" placeholder="Confirm password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Button type="submit" className="w-full">Reset Password</Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold">Set new password</h1>
        <Suspense fallback={<p className="mt-4 text-muted-foreground">Loading...</p>}>
          <div className="mt-6"><ResetForm /></div>
        </Suspense>
      </Card>
    </div>
  );
}
