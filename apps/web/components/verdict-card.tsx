import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import type { Verdict, VerdictConfidence, VerdictPrice, VerdictQuality, VerdictSignal } from "@/lib/types";

type Tone = "positive" | "negative" | "warning" | "neutral";

const PRICE: Record<VerdictPrice, { label: string; tone: Tone }> = {
  UCUZ: { label: "Ucuz", tone: "positive" },
  MAKUL: { label: "Makul", tone: "warning" },
  PAHALI: { label: "Pahalı", tone: "negative" },
};

const QUALITY: Record<VerdictQuality, { label: string; tone: Tone }> = {
  GUCLU: { label: "Güçlü", tone: "positive" },
  ORTA: { label: "Orta", tone: "warning" },
  ZAYIF: { label: "Zayıf", tone: "negative" },
};

const CONFIDENCE: Record<VerdictConfidence, { label: string; tone: Tone }> = {
  YUKSEK: { label: "Yüksek", tone: "positive" },
  ORTA: { label: "Orta", tone: "warning" },
  DUSUK: { label: "Düşük", tone: "negative" },
};

const SIGNAL: Record<VerdictSignal, { label: string; tone: Tone }> = {
  AL: { label: "AL", tone: "positive" },
  TUT: { label: "TUT", tone: "warning" },
  SAT: { label: "SAT", tone: "negative" },
};

function Cell({
  title,
  help,
  value,
  emptyText = "Veri yetersiz",
}: {
  title: string;
  help: string;
  value: { label: string; tone: Tone } | null;
  emptyText?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center gap-1 text-xs font-medium text-muted">
        {title}
        <InfoTooltip text={help} />
      </div>
      <div className="mt-2">
        {value ? (
          <Badge tone={value.tone} className="px-3 py-1 text-sm">
            {value.label}
          </Badge>
        ) : (
          <span className="text-sm text-muted">{emptyText}</span>
        )}
      </div>
    </div>
  );
}

/** Sayfanın en üstündeki "tek bakışta" kartı (ADR-011). Her şey
 * deterministik hüküm motorundan gelir; bu bileşen hiçbir şey hesaplamaz. */
export function VerdictCard({ verdict }: { verdict: Verdict }) {
  if (verdict.unsupported_reason) return null;

  return (
    <Card>
      <CardBody className="space-y-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">Hüküm</div>
          <p className="mt-1 text-base font-semibold text-foreground">{verdict.headline}</p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Cell
            title="Fiyat"
            help="Üç değerleme yönteminin oylaması: şirketin kendi geçmiş çarpanları, sektördeki benzer şirketler ve indirgenmiş nakit akışı (DCF)."
            value={verdict.price ? PRICE[verdict.price] : null}
            emptyText={verdict.lenses.some((l) => l.verdict) ? "Net değil" : "Veri yetersiz"}
          />
          <Cell
            title="Şirket Kalitesi"
            help="Büyüme, kârlılık, bilanço, nakit akışı ve değerleme skorlarından oluşan genel skora göre."
            value={verdict.quality ? QUALITY[verdict.quality] : null}
          />
          <Cell
            title="Hükmün Güvenilirliği"
            help="Kaç değerleme yönteminin veri sağladığına, birbiriyle ne kadar uyuştuğuna ve verinin ne kadar tam/güncel olduğuna göre."
            value={CONFIDENCE[verdict.confidence]}
          />
          {verdict.signal_is_demo && (
            <Cell
              title="Sinyal (Demo)"
              help="Fiyat ve kalite hükmünden kurala göre türetilen deneme amaçlı bir sinyaldir. Hükmün güvenilirliği düşükse verilmez. Yatırım tavsiyesi değildir."
              value={verdict.signal ? SIGNAL[verdict.signal] : null}
              emptyText="Verilmedi"
            />
          )}
        </div>

        <ul className="space-y-1.5 border-t border-border pt-3 text-sm">
          {verdict.lenses.map((lens) => (
            <li key={lens.key} className="flex flex-wrap items-center gap-2">
              <span className="shrink-0 text-xs text-muted sm:w-56">{lens.label}</span>
              {lens.verdict ? (
                <Badge tone={PRICE[lens.verdict].tone}>{PRICE[lens.verdict].label}</Badge>
              ) : (
                <Badge tone="neutral">Veri yok</Badge>
              )}
              <span className="text-xs text-foreground">{lens.reason}</span>
            </li>
          ))}
        </ul>

        {verdict.signal_is_demo && (
          <p className="text-[11px] text-muted">
            Sinyal deneme amaçlıdır ve yatırım tavsiyesi değildir; kararlar sana aittir.
          </p>
        )}
      </CardBody>
    </Card>
  );
}
