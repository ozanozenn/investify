"use client";

import { Info } from "lucide-react";
import { useState } from "react";

/** "What does this mean?" affordance (roadmap section 88 UX principle:
 * the user is not required to be a financial analyst). */
export function InfoTooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label="Bu metrik ne anlama geliyor?"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setOpen(false)}
        className="text-muted hover:text-foreground"
      >
        <Info size={12} />
      </button>
      {open && (
        <span className="absolute bottom-full left-1/2 z-20 mb-1.5 w-56 -translate-x-1/2 rounded-md border border-border bg-surface p-2 text-[11px] leading-snug text-foreground shadow-lg">
          {text}
        </span>
      )}
    </span>
  );
}
