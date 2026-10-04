"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth";

export default function SignupPage() {
  const router = useRouter();
  const { signup, isLoading } = useAuthStore();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.confirm_password) {
      setError("Passwords do not match");
      return;
    }
    try {
      await signup(form);
      router.push("/login?registered=1");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string | object } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed");
    }
  };

  const update = (key: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md p-8">
        <div className="mb-8 flex flex-col items-center">
          <Activity className="h-10 w-10 text-primary mb-2" />
          <h1 className="text-2xl font-bold">Create your account</h1>
          <p className="text-sm text-muted-foreground">Start building strategies today</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: "full_name", label: "Full Name", type: "text" },
            { key: "email", label: "Email", type: "email" },
            { key: "phone", label: "Phone (optional)", type: "tel" },
            { key: "password", label: "Password", type: "password" },
            { key: "confirm_password", label: "Confirm Password", type: "password" },
          ].map((field) => (
            <div key={field.key}>
              <label className="text-sm text-muted-foreground">{field.label}</label>
              <Input
                type={field.type}
                value={form[field.key as keyof typeof form]}
                onChange={update(field.key)}
                required={field.key !== "phone"}
                className="mt-1"
              />
            </div>
          ))}
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Creating account..." : "Create Account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="text-primary hover:underline">Sign in</Link>
        </p>
      </Card>
    </div>
  );
}
