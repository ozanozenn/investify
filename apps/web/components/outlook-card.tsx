import { Badge, toneForOutlook } from "@/components/ui/badge";
import type { HorizonOutlook } from "@/lib/types";

const OUTLOOK_LABEL: Record<string, string> = {
  POSITIVE: "Olumlu",
  NEUTRAL_POSITIVE: "Nötr / Olumlu",
  NEUTRAL: "Nötr",
  NEUTRAL_NEGATIVE: "Nötr / Olumsuz",
  NEGATIVE: "Olumsuz",
};

export function OutlookCard({ title, horizon }: { title: string; horizon: HorizonOutlook }) {
  // v4 snapshot'ları tek bir `rationale` taşır; v1-v3 snapshot'ları
  // drivers/risks listeleri. Hangisi varsa o gösterilir (ADR-005: eski
  // snapshot'lar değişmez, yeniden üretilmez).
  const drivers = horizon.drivers ?? [];
  const risks = horizon.risks ?? [];

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      {/* LLM'in kendi "güven" puanı gösterilmez — sayı üretmek LLM'in işi
          değil (ADR-003); v4'te alan tamamen kalktı. Güvenilirlik
          deterministik Hüküm kartında. */}
      <span className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</span>
      <div className="mt-2">
        <Badge tone={toneForOutlook(horizon.outlook)}>{OUTLOOK_LABEL[horizon.outlook] ?? horizon.outlook}</Badge>
      </div>
      {horizon.rationale && <p className="mt-3 text-xs leading-relaxed text-muted">{horizon.rationale}</p>}
      {drivers.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs text-foreground">
          {drivers.slice(0, 3).map((d, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-[var(--positive)]">+</span>
              <span className="text-muted">{d}</span>
            </li>
          ))}
        </ul>
      )}
      {risks.length > 0 && (
        <ul className="mt-1.5 space-y-1 text-xs">
          {risks.slice(0, 2).map((d, i) => (
            <li key={i} className="flex gap-1.5">
              <span className="text-[var(--negative)]">−</span>
              <span className="text-muted">{d}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
