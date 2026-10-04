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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await authApi.forgotPassword(email);
    setSent(true);
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold">Reset password</h1>
        {sent ? (
          <p className="mt-4 text-muted-foreground">
            If an account exists for {email}, you will receive a reset link shortly.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <Button type="submit" className="w-full">Send Reset Link</Button>
          </form>
        )}
        <Link href="/login" className="mt-6 block text-sm text-primary hover:underline">Back to login</Link>
      </Card>
    </div>
  );
}
