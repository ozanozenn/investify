import { StatTile } from "@/components/ui/stat-tile";
import { formatPercent } from "@/lib/format";
import type { RealGrowth } from "@/lib/types";

const HELP =
  "Büyümenin enflasyondan arındırılmış hali: (1 + nominal büyüme) ÷ (1 + yıllık TÜFE) − 1. Yaklaşık bir değerdir: son mali yılın büyümesi, o yılın kendi enflasyonu yerine en son açıklanan yıllık TÜFE ile arındırılır. Negatifse şirket nominal olarak büyüse bile enflasyonun gerisinde kalmıştır.";

function formatMonth(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("tr-TR", { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(iso));
}

/** Değer neden yok ya da neye dayanıyor — kısa, sade açıklama. */
function hintFor(rg: RealGrowth, nominal: number | null, real: number | null, baseCode: string): string {
  const missing = rg.missing_fields;
  if (missing.includes("cpi_yoy_mock")) return "Gerçek TÜFE verisi yok (mock) — hesaplanmadı";
  if (missing.includes("cpi_yoy")) return "TÜFE verisi alınamadı — hesaplanmadı";
  if (missing.includes("cpi_period_mismatch")) return "TÜFE dönemi mali yılla uyuşmuyor — hesaplanmadı";
  if (missing.includes(baseCode)) return "Önceki yıl sıfır/negatif — anlamlı değil";
  if (real === null) return "Veri eksik — hesaplanmadı";
  return `Nominal ${formatPercent(nominal)} · TÜFE ${formatPercent(rg.cpi_yoy)} (${formatMonth(rg.cpi_observation_date)}) ile yaklaşık`;
}

/** "Finansal Göstergeler" ızgarasına iki kutu ekler (ADR-016). Değerler
 * backend'den hazır gelir; burada yalnızca biçimlendirilir. */
export function RealGrowthTiles({ realGrowth }: { realGrowth: RealGrowth }) {
  if (realGrowth.missing_fields.includes("unsupported_industry")) return null;
  const { revenue_growth_real, net_income_growth_real } = realGrowth;
  return (
    <>
      <StatTile
        label="Reel Gelir Büyümesi"
        value={formatPercent(revenue_growth_real)}
        tone={revenue_growth_real !== null && revenue_growth_real < 0 ? "negative" : "neutral"}
        hint={hintFor(realGrowth, realGrowth.revenue_growth_nominal, revenue_growth_real, "non_positive_base:REVENUE")}
        help={HELP}
      />
      <StatTile
        label="Reel Net Kâr Büyümesi"
        value={formatPercent(net_income_growth_real)}
        tone={net_income_growth_real !== null && net_income_growth_real < 0 ? "negative" : "neutral"}
        hint={hintFor(realGrowth, realGrowth.net_income_growth_nominal, net_income_growth_real, "non_positive_base:NET_INCOME")}
        help={HELP}
      />
    </>
  );
}
