"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth";

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [needs2fa, setNeeds2fa] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login(email, password, remember, needs2fa ? otp : undefined);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (msg === "2FA code required") {
        setNeeds2fa(true);
      } else {
        setError(msg || "Invalid credentials");
      }
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md p-8">
        <div className="mb-8 flex flex-col items-center">
          <Activity className="h-10 w-10 text-primary mb-2" />
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="text-sm text-muted-foreground">Sign in to QuantForge</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground">Email</label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="mt-1" />
          </div>
          <div>
            <label className="text-sm text-muted-foreground">Password</label>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="mt-1" />
          </div>
          {needs2fa && (
            <div>
              <label className="text-sm text-muted-foreground">2FA Code</label>
              <Input value={otp} onChange={(e) => setOtp(e.target.value)} maxLength={6} className="mt-1" />
            </div>
          )}
          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember me
            </label>
            <Link href="/forgot-password" className="text-primary hover:underline">Forgot password?</Link>
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Signing in..." : "Sign In"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-primary hover:underline">Sign up</Link>
        </p>
      </Card>
    </div>
  );
}
