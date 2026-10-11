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
  const [plansLoading, setPlansLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchUser();
    setPlansLoading(true);
    billingApi.plans()
      .then((r) => {
        if (!Array.isArray(r.data)) throw new Error("Invalid plans response");
        setPlans(r.data);
        setError("");
      })
      .catch(() => {
        setPlans([]);
        setError("Pricing is temporarily unavailable because the billing service could not be reached. Please try again later.");
      })
      .finally(() => setPlansLoading(false));
  }, [fetchUser]);

  const handleCheckout = async (planId: string) => {
    if (planId === "free") {
      router.push("/signup");
      return;
    }
    if (!isAuthenticated) {
      router.push(`/login?redirect=/pricing&plan=${encodeURIComponent(planId)}`);
      return;
    }
    if (planId !== "starter" && planId !== "pro") return;

    setLoading(planId);
    setError("");
    try {
      const { data } = await billingApi.checkout(planId);
      if (typeof data.checkout_url !== "string" || !data.checkout_url) {
        throw new Error("Checkout URL unavailable");
      }
      const checkoutUrl = new URL(data.checkout_url);
      if (checkoutUrl.protocol !== "https:" || !["checkout.stripe.com", "billing.stripe.com"].includes(checkoutUrl.hostname)) {
        throw new Error("Unexpected checkout destination");
      }
      window.location.assign(checkoutUrl.toString());
    } catch {
      setError("Checkout could not be started. Confirm billing is configured and try again.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main id="page-content" tabIndex={-1} className="mx-auto max-w-7xl px-4 py-32 outline-none">
        <h1 className="text-center text-4xl font-bold">Pricing</h1>
        <p className="mt-2 text-center text-muted-foreground">Plans and billing information provided by the billing service.</p>

        {plansLoading ? (
          <p className="mt-12 text-center text-sm text-muted-foreground" role="status" aria-live="polite">Loading current plans…</p>
        ) : plans.length ? (
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {plans.map((p) => (
              <Card key={p.id} className={`p-6 ${p.id === "pro" ? "glow-blue border-primary/50" : ""}`}>
                <CardHeader className="p-0">
                  <CardTitle>{p.name}</CardTitle>
                  <p className="mt-2 text-2xl font-bold">
                    {p.price_usd === 0 ? "$0" : `$${p.price_usd}`}
                    {p.price_usd > 0 && <span className="text-sm text-muted-foreground">/mo</span>}
                  </p>
                </CardHeader>
                <CardContent className="mt-4 space-y-2 p-0">
                  {p.features.map((feature) => <p key={feature} className="text-sm text-muted-foreground">✓ {feature}</p>)}
                  <Button className="mt-4 w-full" variant={p.id === "pro" ? "default" : "outline"} disabled={loading === p.id || (p.id !== "free" && !p.stripe_enabled)} onClick={() => handleCheckout(p.id)}>
                    {loading === p.id ? "Opening checkout…" : p.id === "free" ? "Get Started" : p.stripe_enabled ? "Subscribe" : "Billing unavailable"}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="mx-auto mt-12 max-w-xl rounded-xl border border-border p-6 text-center">
            <p className="text-sm text-muted-foreground" role="status">{error || "No plans are currently available."}</p>
            <Button className="mt-4" variant="outline" onClick={() => window.location.reload()}>Retry</Button>
          </div>
        )}

        {error && plans.length > 0 && <p className="mx-auto mt-6 max-w-2xl text-center text-sm text-red-500" role="alert">{error}</p>}

        <section className="mx-auto mt-20 max-w-3xl" aria-labelledby="pricing-faq-title">
          <h2 id="pricing-faq-title" className="text-2xl font-semibold">Pricing FAQ</h2>
          <div className="mt-5 divide-y divide-border rounded-xl border border-border px-5">
            <details className="py-4">
              <summary className="cursor-pointer font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Where do the displayed prices come from?</summary>
              <p className="mt-3 text-sm text-muted-foreground">The page loads current plans from the configured billing API. If that service is unavailable, prices are not guessed or substituted.</p>
            </details>
            <details className="py-4">
              <summary className="cursor-pointer font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Can I try strategies without connecting a live broker?</summary>
              <p className="mt-3 text-sm text-muted-foreground">The application supports creating paper strategies. Live broker access requires a separate broker connection and valid credentials.</p>
            </details>
            <details className="py-4">
              <summary className="cursor-pointer font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Why is subscription checkout unavailable?</summary>
              <p className="mt-3 text-sm text-muted-foreground">Checkout requires the billing service and Stripe configuration to be enabled. Contact the project administrator if you manage this deployment.</p>
            </details>
          </div>
        </section>

        <p className="mt-8 text-center text-xs text-muted-foreground">
          Enterprise? <Link href="/contact" className="text-primary hover:underline">Contact sales</Link>
        </p>
      </main>
    </div>
  );
}
