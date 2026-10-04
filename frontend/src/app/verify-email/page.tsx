"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function VerifyContent() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }
    api.post("/auth/verify-email", { token })
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"));
  }, [token]);

  if (status === "loading") return <p className="text-muted-foreground">Verifying your email...</p>;
  if (status === "success") {
    return (
      <div className="text-center">
        <p className="text-emerald-400 text-lg">Email verified successfully!</p>
        <Link href="/dashboard"><Button className="mt-6">Go to Dashboard</Button></Link>
      </div>
    );
  }
  return (
    <div className="text-center">
      <p className="text-red-400">Invalid or expired verification link.</p>
      <Link href="/login" className="mt-4 inline-block text-primary hover:underline">Back to login</Link>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md p-8 text-center">
        <h1 className="text-2xl font-bold mb-6">Email Verification</h1>
        <Suspense fallback={<p>Loading...</p>}>
          <VerifyContent />
        </Suspense>
      </Card>
    </div>
  );
}
