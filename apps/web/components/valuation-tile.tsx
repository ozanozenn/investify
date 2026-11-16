import { Badge } from "@/components/ui/badge";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { cn } from "@/lib/cn";
import { formatMultiple, formatPercent } from "@/lib/format";
import type { VerdictPrice } from "@/lib/types";

// Etiket ve fark backend'den gelir (hüküm kartıyla aynı eşikler,
// config/verdict.yaml lenses.history) — burada eşik veya oran hesabı yok.
const HISTORY_LABEL: Record<VerdictPrice, { label: string; tone: "positive" | "warning" | "negative"; text: string }> = {
  UCUZ: { label: "Ucuz", tone: "positive", text: "text-[var(--positive)]" },
  MAKUL: { label: "Makul", tone: "warning", text: "text-muted" },
  PAHALI: { label: "Pahalı", tone: "negative", text: "text-[var(--negative)]" },
};

export function ValuationTile({
  label,
  current,
  historical,
  ratio,
  historyLabel,
  historyDiff,
  help,
}: {
  label: string;
  current: number | null;
  historical: number | null;
  ratio: number | null;
  historyLabel: VerdictPrice | null | undefined;
  historyDiff: number | null | undefined;
  help?: string;
}) {
  const style = historyLabel ? HISTORY_LABEL[historyLabel] : null;

  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="flex items-center gap-1 text-[11px] text-muted">
        {label}
        {help && <InfoTooltip text={help} />}
      </div>
      <div className="mt-1 font-tabular text-lg font-semibold text-foreground">{formatMultiple(current)}</div>
      <div className="mt-1 text-[11px] text-muted">
        Tarihsel medyan: <span className="font-tabular">{formatMultiple(historical)}</span>
      </div>
      {style && historyDiff !== null && historyDiff !== undefined ? (
        <div className="mt-0.5 flex items-center gap-1.5 text-[11px]">
          <span className={cn("font-tabular", style.text)}>
            Tarihsele göre {historyDiff > 0 ? "+" : ""}
            {formatPercent(historyDiff, 0)}
          </span>
          <Badge tone={style.tone} className="px-1.5 py-0 text-[10px]">
            {style.label}
          </Badge>
          <InfoTooltip text="Şirketin şu anki çarpanı, kendi son yıllardaki tipik (medyan) çarpanından ne kadar farklı. Pozitif = tarihine göre daha pahalı, negatif = daha ucuz. Ucuz/Makul/Pahalı etiketi hüküm kartındaki 'Kendi geçmişine göre' yöntemiyle aynı eşiklerden gelir." />
        </div>
      ) : (
        ratio !== null && (
          <div className="mt-0.5 flex items-center gap-1 text-[11px] text-muted">
            Medyana oranı: <span className="font-tabular">{formatMultiple(ratio, 2)}</span>
            <InfoTooltip text="Bu analiz eski bir sürümle kaydedildiği için ucuz/pahalı etiketi yok. 'Yenile' ile yeni analiz alındığında hüküm kartıyla aynı eşiklerle etiketlenir." />
          </div>
        )
      )}
    </div>
  );
}
