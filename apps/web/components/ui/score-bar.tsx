import { cn } from "@/lib/cn";

function colorForScore(score: number): string {
  if (score >= 65) return "var(--positive)";
  if (score >= 40) return "var(--warning)";
  return "var(--negative)";
}

export function ScoreBar({ label, score, className }: { label: string; score: number; className?: string }) {
  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="font-tabular font-semibold text-foreground">{score.toFixed(0)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.max(2, Math.min(100, score))}%`, background: colorForScore(score) }}
        />
      </div>
    </div>
  );
}

export function BigScore({ score, label }: { score: number; label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-border bg-surface-hover px-6 py-4">
      <span
        className="font-tabular text-4xl font-bold"
        style={{ color: colorForScore(score) }}
      >
        {score.toFixed(0)}
      </span>
      <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
    </div>
  );
}
