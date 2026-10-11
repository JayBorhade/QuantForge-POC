"use client";

import { FormEvent, useState } from "react";
import { Navbar } from "@/components/layout/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export default function ContactPage() {
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState<{ kind: "info" | "error"; text: string } | null>(null);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setNotice(null);
    const supportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL?.trim();
    if (!supportEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(supportEmail)) {
      setNotice({
        kind: "error",
        text: "Contact delivery is not configured yet. Set NEXT_PUBLIC_SUPPORT_EMAIL to a monitored support address before accepting messages.",
      });
      return;
    }

    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    const body = String(form.get("message") ?? "").trim();
    if (!name || !email || !body) {
      setNotice({ kind: "error", text: "Complete all required fields before continuing." });
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setNotice({ kind: "error", text: "Enter a valid reply email address." });
      return;
    }

    const subject = encodeURIComponent(`QuantForge support request from ${name}`);
    const content = encodeURIComponent(`Name: ${name}\nReply email: ${email}\n\n${body}`);
    window.location.href = `mailto:${supportEmail}?subject=${subject}&body=${content}`;
    setNotice({ kind: "info", text: "Your email app should open with a draft. Review it and press Send to contact support; this website cannot confirm delivery." });
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <main id="page-content" tabIndex={-1} className="mx-auto max-w-lg px-4 py-32 outline-none">
        <h1 className="text-4xl font-bold">Contact Us</h1>
        <p className="mt-3 text-sm text-muted-foreground">Send a message to the QuantForge team.</p>
        <Card className="mt-8 p-8">
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div>
              <label htmlFor="contact-name" className="mb-1 block text-sm font-medium">Name</label>
              <Input id="contact-name" name="name" autoComplete="name" placeholder="Your name" required />
            </div>
            <div>
              <label htmlFor="contact-email" className="mb-1 block text-sm font-medium">Email</label>
              <Input id="contact-email" name="email" type="email" autoComplete="email" placeholder="you@example.com" required />
            </div>
            <div>
              <label htmlFor="contact-message" className="mb-1 block text-sm font-medium">Message</label>
              <textarea id="contact-message" name="message" className="flex min-h-[120px] w-full rounded-lg border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" placeholder="How can we help?" required />
            </div>
            {notice && <p className={notice.kind === "error" ? "text-sm text-red-500" : "text-sm text-muted-foreground"} role={notice.kind === "error" ? "alert" : "status"}>{notice.text}</p>}
            <Button type="submit" className="w-full">Prepare Email</Button>
          </form>
        </Card>
      </main>
    </div>
  );
}
