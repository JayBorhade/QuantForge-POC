"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CopyButton({ value, label = "Copy to clipboard" }: { value: string; label?: string }) {
  const [status, setStatus] = useState<"idle" | "copied" | "error">("idle");

  const copy = async () => {
    try {
      if (!navigator.clipboard?.writeText || !window.isSecureContext) {
        throw new Error("Clipboard access is unavailable in this context.");
      }
      await navigator.clipboard.writeText(value);
      setStatus("copied");
      window.setTimeout(() => setStatus("idle"), 1800);
    } catch {
      setStatus("error");
      window.setTimeout(() => setStatus("idle"), 3000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button type="button" onClick={copy} className="ux-icon-button" aria-label={label} title={label}>
        {status === "copied" ? <Check aria-hidden="true" className="h-4 w-4" /> : <Copy aria-hidden="true" className="h-4 w-4" />}
      </button>
      <span className="sr-only" role="status" aria-live="polite">
        {status === "copied" ? "Copied to clipboard." : status === "error" ? "Could not copy. Clipboard permission may be unavailable." : ""}
      </span>
    </div>
  );
}
