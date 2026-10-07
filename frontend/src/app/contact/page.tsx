"use client";

import { Navbar } from "@/components/layout/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export default function ContactPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="mx-auto max-w-lg px-4 py-32">
        <h1 className="text-4xl font-bold">Contact Us</h1>
        <Card className="mt-8 p-8">
          <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
            <Input placeholder="Name" required />
            <Input type="email" placeholder="Email" required />
            <textarea
              className="flex min-h-[120px] w-full rounded-lg border border-border bg-secondary/50 px-3 py-2 text-sm"
              placeholder="Message"
              required
            />
            <Button type="submit" className="w-full">Send Message</Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
