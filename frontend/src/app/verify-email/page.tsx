"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function VerifyContent() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [email, setEmail] = useState("");
  const [resendStatus, setResendStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }
    setStatus("loading");
    api.post("/auth/verify-email", { token })
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"));
  }, [token]);

  const resendVerification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setResendStatus("loading");
    try {
      await api.post("/auth/resend-verification", { email });
      setResendStatus("success");
    } catch {
      setResendStatus("error");
    }
  };

  if (status === "loading") {
    return <p className="text-muted-foreground">Verifying your email...</p>;
  }

  if (status === "success") {
    return (
      <div className="text-center">
        <p className="text-emerald-400 text-lg">Email verified successfully!</p>
        <Link href="/dashboard"><Button className="mt-6">Go to Dashboard</Button></Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 text-left">
      <p className="text-center text-muted-foreground">
        This verification link is missing or invalid. Enter your account email to request a fresh link.
      </p>
      <form onSubmit={resendVerification} className="space-y-3">
        <label htmlFor="verification-email" className="block text-sm font-medium">Account email</label>
        <Input
          id="verification-email"
          name="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
        />
        <Button type="submit" className="w-full" disabled={resendStatus === "loading"}>
          {resendStatus === "loading" ? "Sending..." : "Resend verification email"}
        </Button>
      </form>
      {resendStatus === "success" && (
        <p role="status" className="text-sm text-emerald-400">
          If the account exists and needs verification, a verification email has been sent.
        </p>
      )}
      {resendStatus === "error" && (
        <p role="alert" className="text-sm text-red-400">
          We couldn't process the request right now. Please try again later.
        </p>
      )}
      <div className="text-center">
        <Link href="/login" className="inline-block text-primary hover:underline">Back to login</Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <main id="page-content" tabIndex={-1} className="flex min-h-screen items-center justify-center px-4 outline-none">
      <Card className="w-full max-w-md p-8 text-center">
        <h1 className="mb-6 text-2xl font-bold">Email Verification</h1>
        <Suspense fallback={<p>Loading...</p>}>
          <VerifyContent />
        </Suspense>
      </Card>
    </main>
  );
}
