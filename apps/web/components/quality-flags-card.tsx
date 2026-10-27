import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { formatCompact, formatPercent } from "@/lib/format";
import type { QualityFlag, QualityFlagValue, QualityFlagsResult, QualitySeverity } from "@/lib/types";

const SEVERITY: Record<QualitySeverity, { label: string; tone: "negative" | "warning" | "positive" }> = {
  UYARI: { label: "Uyarı", tone: "negative" },
  DIKKAT: { label: "Dikkat", tone: "warning" },
  OLUMLU: { label: "Olumlu", tone: "positive" },
};

const HELP =
  "Finansal tablolardaki yıllık değişimlere bakan sabit kurallar: ör. gelir artarken nakit akışının düşmesi ya da alacakların gelirden hızlı büyümesi. Bir bayrak kesin bir sorun değil, yakından bakmaya değer bir sinyaldir. Yapay zekâ değil, deterministik kural motoru üretir.";

function formatValue(v: QualityFlagValue): string {
  return v.unit === "currency" ? formatCompact(v.value, "TL") : formatPercent(v.value);
}

function FlagRow({ flag }: { flag: QualityFlag }) {
  const severity = SEVERITY[flag.severity];
  return (
    <li className="rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={severity.tone}>{severity.label}</Badge>
        <span className="text-sm font-medium text-foreground">{flag.title}</span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-muted">{flag.detail}</p>
      {flag.values.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
          {flag.values.map((v) => (
            <span key={v.key}>
              {v.label}: <span className="font-tabular text-foreground">{formatValue(v)}</span>
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

/** Kalite bayrakları (ADR-016). Her şey backend'deki deterministik kural
 * motorundan gelir; bu bileşen yalnızca gösterir, hiçbir şey hesaplamaz. */
export function QualityFlagsCard({ qualityFlags }: { qualityFlags: QualityFlagsResult }) {
  // Sigorta/GYO: sayfa zaten "desteklenmiyor" uyarısı gösteriyor.
  if (qualityFlags.missing_fields.includes("unsupported_industry")) return null;

  const { flags, passed_checks, not_evaluated, as_of_period, engine_version } = qualityFlags;
  const noFinancials = qualityFlags.missing_fields.includes("no_financial_periods");
  const subtitle = `Deterministik kural motoru ${engine_version}${as_of_period ? ` · ${as_of_period} dönemi` : ""}`;

  // Bankalar analiz ediliyor ama genel kurallar bankaya uymuyor; kartı
  // sessizce gizlemek yerine nedenini söyle.
  if (qualityFlags.not_applicable_reason) {
    return (
      <Card>
        <CardHeader title="Kalite Bayrakları" subtitle={subtitle} action={<InfoTooltip text={HELP} />} />
        <CardBody>
          <p className="text-sm text-muted">{qualityFlags.not_applicable_reason}</p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Kalite Bayrakları" subtitle={subtitle} action={<InfoTooltip text={HELP} />} />
      <CardBody className="space-y-3">
        {noFinancials ? (
          <p className="text-sm text-muted">Finansal tablo verisi olmadığı için kalite kontrolleri yapılamadı.</p>
        ) : (
          flags.length === 0 && (
            <p className="text-sm text-muted">Kontrol edilen alanlarda dikkat çeken bir bulgu yok.</p>
          )
        )}

        {flags.length > 0 && (
          <ul className="space-y-2">
            {flags.map((flag) => (
              <FlagRow key={flag.key} flag={flag} />
            ))}
          </ul>
        )}

        {(passed_checks.length > 0 || not_evaluated.length > 0) && (
          <div className="space-y-1.5 border-t border-border pt-3 text-[11px] text-muted">
            {passed_checks.length > 0 && <p>Sorun görülmeyen kontroller: {passed_checks.join(" · ")}</p>}
            {not_evaluated.length > 0 && (
              <div>
                <p>Veri eksikliği nedeniyle değerlendirilemeyenler:</p>
                <ul className="mt-0.5 space-y-0.5">
                  {not_evaluated.map((check) => (
                    <li key={check.key}>
                      · {check.name} — {check.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
