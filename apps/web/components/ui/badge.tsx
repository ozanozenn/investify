import { cn } from "@/lib/cn";

type Tone = "neutral" | "positive" | "negative" | "warning" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-surface-hover text-muted border-border",
  positive: "bg-[color-mix(in_srgb,var(--positive)_14%,transparent)] text-[var(--positive)] border-[color-mix(in_srgb,var(--positive)_35%,transparent)]",
  negative: "bg-[color-mix(in_srgb,var(--negative)_14%,transparent)] text-[var(--negative)] border-[color-mix(in_srgb,var(--negative)_35%,transparent)]",
  warning: "bg-[color-mix(in_srgb,var(--warning)_14%,transparent)] text-[var(--warning)] border-[color-mix(in_srgb,var(--warning)_35%,transparent)]",
  accent: "bg-[color-mix(in_srgb,var(--accent)_14%,transparent)] text-[var(--accent)] border-[color-mix(in_srgb,var(--accent)_35%,transparent)]",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function toneForOutlook(outlook: string): Tone {
  if (outlook === "POSITIVE") return "positive";
  if (outlook === "NEUTRAL_POSITIVE") return "positive";
  if (outlook === "NEGATIVE") return "negative";
  if (outlook === "NEUTRAL_NEGATIVE") return "negative";
  return "neutral";
}

export function toneForScore(score: number): Tone {
  if (score >= 65) return "positive";
  if (score >= 40) return "warning";
  return "negative";
}
