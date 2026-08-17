import { cn } from "@/lib/cn";
import { InfoTooltip } from "./info-tooltip";

export function StatTile({
  label,
  value,
  hint,
  tone = "neutral",
  help,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "positive" | "negative";
  help?: string;
}) {
  const toneClass =
    tone === "positive" ? "text-[var(--positive)]" : tone === "negative" ? "text-[var(--negative)]" : "text-foreground";
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="flex items-center gap-1 text-[11px] text-muted">
        <span>{label}</span>
        {help && <InfoTooltip text={help} />}
      </div>
      <div className={cn("mt-1 font-tabular text-lg font-semibold", toneClass)}>{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-muted">{hint}</div>}
    </div>
  );
}
