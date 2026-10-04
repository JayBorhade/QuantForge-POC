"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/layout/navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { billingApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

interface Plan {
  id: string;
  name: string;
  price_usd: number;
  features: string[];
  stripe_enabled: boolean;
}

export default function PricingPage() {
  const router = useRouter();
  const { isAuthenticated, fetchUser } = useAuthStore();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchUser();
    billingApi.plans().then((r) => setPlans(r.data)).catch(() => {
      setPlans([
        { id: "free", name: "Free", price_usd: 0, features: ["2 strategies", "Paper only"], stripe_enabled: false },
        { id: "starter", name: "Starter", price_usd: 29, features: ["5 strategies", "Limited live"], stripe_enabled: false },
        { id: "pro", name: "Pro", price_usd: 99, features: ["Unlimited", "AI insights"], stripe_enabled: false },
      ]);
    });
  }, [fetchUser]);

  const handleCheckout = async (planId: string) => {
    if (planId === "free") {
      router.push("/signup");
      return;
    }
    if (!isAuthenticated) {
      router.push(`/login?redirect=/pricing&plan=${planId}`);
      return;
    }
    if (planId !== "starter" && planId !== "pro") return;

    setLoading(planId);
    try {
      const { data } = await billingApi.checkout(planId);
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch {
      alert("Billing unavailable. Configure Stripe keys in .env or sign up for free tier.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="mx-auto max-w-7xl px-4 py-32">
        <h1 className="text-center text-4xl font-bold">Pricing</h1>
        <p className="text-center text-muted-foreground mt-2">
          Secure payments via Stripe
        </p>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {plans.map((p) => (
            <Card
              key={p.id}
              className={`p-6 ${p.id === "pro" ? "glow-blue border-primary/50" : ""}`}
            >
              <CardHeader className="p-0">
                <CardTitle>{p.name}</CardTitle>
                <p className="text-2xl font-bold mt-2">
                  {p.price_usd === 0 ? "$0" : `$${p.price_usd}`}
                  {p.price_usd > 0 && <span className="text-sm text-muted-foreground">/mo</span>}
                </p>
              </CardHeader>
              <CardContent className="mt-4 space-y-2 p-0">
                {p.features.map((f) => (
                  <p key={f} className="text-sm text-muted-foreground">✓ {f}</p>
                ))}
                <Button
                  className="w-full mt-4"
                  variant={p.id === "pro" ? "default" : "outline"}
                  disabled={loading === p.id}
                  onClick={() => handleCheckout(p.id)}
                >
                  {loading === p.id
                    ? "Redirecting..."
                    : p.id === "free"
                    ? "Get Started"
                    : "Subscribe"}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="text-center text-xs text-muted-foreground mt-8">
          Enterprise? <Link href="/contact" className="text-primary hover:underline">Contact sales</Link>
        </p>
      </div>
    </div>
  );
}
