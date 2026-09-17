"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { InfoTooltip } from "@/components/ui/info-tooltip";
import { StatTile } from "@/components/ui/stat-tile";
import { cn } from "@/lib/cn";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import {
  getCompanyDcf,
  type DcfAssumptions,
  type DcfScenarioResult,
  type SensitivityCell,
} from "@/lib/api-dcf";

/**
 * DCF (indirgenmiş nakit akışı) paneli — Phase 2 backend valuation_engine
 * için frontend görünümü. Sadece yeni dosyalarda çalışır (lib/api-dcf.ts,
 * bu dosya) — app/company/[ticker]/page.tsx, lib/api.ts ve lib/types.ts
 * bilerek değiştirilmedi; entegrasyon ayrı bir geçişte yapılacak.
 */

type Scenario = "bear" | "base" | "bull";

const SCENARIO_LABELS: Record<Scenario, string> = {
  bear: "Kötümser",
  base: "Baz",
  bull: "İyimser",
};

type AssumptionKey = Exclude<keyof DcfAssumptions, "overridden_fields">;

interface FieldConfig {
  key: AssumptionKey;
  label: string;
  /** Percent-style fields are entered/displayed as whole percentages (12 for 0.12)
   * and converted to a fraction before being sent as an override. */
  isPercent: boolean;
  help: string;
}

const FIELD_CONFIG: FieldConfig[] = [
  {
    key: "revenue_growth_rate",
    label: "Gelir Büyümesi",
    isPercent: true,
    help: "Şirketin gelirinin önümüzdeki her yıl ne kadar büyüyeceği varsayımı. Boş bırakırsan geçmiş verilerden tahmin edilir.",
  },
  {
    key: "ebit_margin",
    label: "FAVÖK/EBIT Marjı",
    isPercent: true,
    help: "Her 100 liralık satıştan, faiz ve vergi öncesi ne kadar faaliyet kârı kaldığı. Yüksek olması daha kârlı bir iş modeli demektir.",
  },
  {
    key: "tax_rate",
    label: "Vergi Oranı",
    isPercent: true,
    help: "Şirketin kârı üzerinden ödediği varsayılan kurumlar vergisi oranı.",
  },
  {
    key: "da_percent_of_revenue",
    label: "Amortisman %",
    isPercent: true,
    help: "Amortisman ve İtfa Payı — makine/bina gibi varlıkların değer kaybının muhasebeye yansıtılan payı, gelirin yüzdesi olarak. Nakit çıkışı değildir, bu yüzden nakit akışına geri eklenir.",
  },
  {
    key: "capex_percent_of_revenue",
    label: "Yatırım Harcaması %",
    isPercent: true,
    help: "CAPEX — şirketin yeni makine/tesis/ekipmana yaptığı yatırım harcamasının, gelirin yüzdesi olarak tahmini.",
  },
  {
    key: "working_capital_change_percent_of_revenue",
    label: "İşletme Sermayesi Değişimi %",
    isPercent: true,
    help: "Şirketin büyümek için stok/alacak gibi kalemlere bağlaması gereken ek nakdin, gelirin yüzdesi olarak tahmini.",
  },
  {
    key: "wacc",
    label: "WACC",
    isPercent: true,
    help: "Ağırlıklı Ortalama Sermaye Maliyeti — şirketin hem hissedarlarına hem de borç verenlerine ödemesi gereken 'ortalama getiri bedeli'. Gelecekteki nakit akışlarını bugüne indirgemek için kullanılır; yükseldikçe hesaplanan bugünkü değer düşer.",
  },
  {
    key: "terminal_growth_rate",
    label: "Terminal Büyüme",
    isPercent: true,
    help: "Tahmin ufkunun (birkaç yıl) ötesinde, şirketin sonsuza kadar sabit bir hızda büyüyeceği varsayılan oran. WACC'tan düşük olmalı, aksi halde hesap anlamsızlaşır.",
  },
  {
    key: "net_debt",
    label: "Net Borç",
    isPercent: false,
    help: "Toplam Borç eksi Nakit. Firma Değerinden bu tutar düşülerek hissedarlara kalan Özkaynak Değeri bulunur.",
  },
  {
    key: "shares_outstanding",
    label: "Hisse Sayısı",
    isPercent: false,
    help: "Şirketin toplam dolaşımdaki hisse senedi adedi. Özkaynak Değeri buna bölünerek hisse başına içsel değer bulunur.",
  },
];

/** Machine keys observed/expected in missing_fields -> short Turkish labels.
 * Unmapped keys fall back to the raw key so nothing is silently hidden. */
const MISSING_FIELD_LABELS: Record<string, string> = {
  revenue_growth_rate_defaulted_from_config: "Gelir büyümesi varsayılan",
  ebit_margin_defaulted_from_config: "FAVÖK marjı varsayılan",
  tax_rate_defaulted_from_config: "Vergi oranı varsayılan",
  da_percent_of_revenue_defaulted_from_config: "Amortisman % varsayılan",
  capex_percent_of_revenue_defaulted_from_config: "Yatırım harcaması % varsayılan",
  working_capital_change_percent_of_revenue_defaulted_from_config: "İşletme sermayesi % varsayılan",
  wacc_defaulted_from_config: "WACC varsayılan",
  terminal_growth_rate_defaulted_from_config: "Terminal büyüme varsayılan",
  net_debt_defaulted_from_config: "Net borç varsayılan",
  shares_outstanding_defaulted_from_config: "Hisse sayısı varsayılan",
  net_debt_missing: "Net borç verisi eksik",
  shares_outstanding_missing: "Hisse sayısı verisi eksik",
  current_price_missing: "Güncel fiyat eksik",
};

function missingFieldLabel(key: string): string {
  return MISSING_FIELD_LABELS[key] ?? key;
}

type DraftState = Partial<Record<AssumptionKey, string>>;

export function DcfPanel({
  ticker,
  currentPrice,
  currency,
}: {
  ticker: string;
  currentPrice: number | null;
  currency: string;
}) {
  const [scenario, setScenario] = useState<Scenario>("base");
  const [draft, setDraft] = useState<DraftState>({});
  const [appliedOverrides, setAppliedOverrides] = useState<Partial<DcfAssumptions>>({});

  const { data, isLoading, isError } = useQuery({
    queryKey: ["dcf", ticker, appliedOverrides],
    queryFn: () => getCompanyDcf(ticker, appliedOverrides),
    retry: false,
  });

  function handleApply() {
    const overrides: Partial<DcfAssumptions> = {};
    for (const field of FIELD_CONFIG) {
      const raw = draft[field.key];
      if (raw === undefined || raw.trim() === "") continue;
      const parsed = Number(raw);
      if (Number.isNaN(parsed)) continue;
      overrides[field.key] = field.isPercent ? parsed / 100 : parsed;
    }
    setAppliedOverrides(overrides);
  }

  function handleReset() {
    setDraft({});
    setAppliedOverrides({});
  }

  return (
    <Card>
      <CardHeader
        title="DCF Değerleme"
        subtitle="İndirgenmiş nakit akışı — senaryo bazlı içsel değer tahmini"
      />
      <CardBody className="space-y-5">
        {isLoading && (
          <div className="flex items-center gap-2 py-8 text-xs text-muted">
            <Loader2 className="animate-spin" size={16} />
            DCF hesaplanıyor...
          </div>
        )}

        {isError && !isLoading && (
          <p className="py-4 text-xs text-muted">
            DCF verisi alınamadı — bu şirket için henüz bir analiz üretilmemiş olabilir.
          </p>
        )}

        {data && !isLoading && (
          <>
            <ScenarioTabs scenario={scenario} onChange={setScenario} />
            <ScenarioSummary
              result={data[scenario]}
              currentPrice={currentPrice}
              currency={currency}
            />
            <AssumptionsForm
              base={data.base.assumptions}
              draft={draft}
              onDraftChange={setDraft}
              onApply={handleApply}
              onReset={handleReset}
            />
            <SensitivityMatrix
              matrix={data.sensitivity_matrix}
              base={data.base.assumptions}
              currency={currency}
            />
          </>
        )}
      </CardBody>
    </Card>
  );
}

function ScenarioTabs({
  scenario,
  onChange,
}: {
  scenario: Scenario;
  onChange: (s: Scenario) => void;
}) {
  return (
    <div className="inline-flex rounded-md border border-border bg-surface-hover p-0.5">
      {(["bear", "base", "bull"] as const).map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={cn(
            "rounded px-3 py-1.5 text-xs font-medium transition-colors",
            scenario === s ? "bg-surface text-foreground shadow-sm" : "text-muted hover:text-foreground"
          )}
        >
          {SCENARIO_LABELS[s]}
        </button>
      ))}
    </div>
  );
}

function ScenarioSummary({
  result,
  currentPrice,
  currency,
}: {
  result: DcfScenarioResult;
  currentPrice: number | null;
  currency: string;
}) {
  const value = result.intrinsic_value_per_share;
  const upside = result.upside_vs_current_price;
  const isNegative = value !== null && value < 0;
  const tone = value === null ? "text-muted" : isNegative ? "text-[var(--negative)]" : "text-[var(--positive)]";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-1 text-[11px] text-muted">
            İçsel Değer / Hisse
            <InfoTooltip text="DCF modelinin hesapladığı, bu senaryonun varsayımları altında bir hissenin 'gerçekte' etmesi gereken değer. Borsadaki güncel fiyatla karşılaştırmak, hissenin ucuz mu pahalı mı olduğuna dair bir fikir verir — kesin bir hedef fiyat değildir." />
          </div>
          <div className={cn("mt-1 font-tabular text-3xl font-semibold", tone)}>
            {value === null ? "—" : formatCurrency(value, currency)}
          </div>
          {currentPrice !== null && upside !== null && (
            <div className="mt-1 text-xs">
              <span className={upside >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}>
                Güncel fiyata göre {upside >= 0 ? "+" : ""}
                {formatPercent(upside, 1)}
              </span>
              <span className="ml-1.5 text-muted">
                (Güncel: {formatCurrency(currentPrice, currency)})
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <StatTile
            label="Firma Değeri (EV)"
            value={formatCurrency(result.enterprise_value, currency, 0)}
            help="Enterprise Value — şirketin tamamını (hem hisseleri hem borcunu) satın almanın toplam maliyeti. Gelecekteki tüm nakit akışlarının bugünkü değerinin toplamıdır."
          />
          <StatTile
            label="Özkaynak Değeri"
            value={formatCurrency(result.equity_value, currency, 0)}
            help="Firma Değerinden net borç düşüldükten sonra, sadece hissedarlara kalan değer. Bu tutar hisse sayısına bölünerek hisse başına içsel değer bulunur."
          />
        </div>
      </div>

      {isNegative && (
        <div className="flex items-start gap-2 rounded-md border border-border bg-surface-hover px-3 py-2 text-xs leading-relaxed text-foreground">
          <InfoTooltip text="Negatif içsel değer, bu senaryonun varsayımları altında modelin ürettiği ham bir sonuçtur." />
          <p>
            Bu senaryonun varsayımları altında özkaynak değeri negatif çıkıyor — bu şirketin değersiz
            olduğu anlamına gelmez, kullanılan varsayımların ne kadar karamsar olduğunu gösterir.
          </p>
        </div>
      )}

      {result.missing_fields.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {result.missing_fields.map((f) => (
            <Badge key={f} tone="neutral">
              {missingFieldLabel(f)}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function AssumptionsForm({
  base,
  draft,
  onDraftChange,
  onApply,
  onReset,
}: {
  base: DcfAssumptions;
  draft: DraftState;
  onDraftChange: (d: DraftState) => void;
  onApply: () => void;
  onReset: () => void;
}) {
  function placeholderFor(field: FieldConfig): string {
    const value = base[field.key];
    if (value === null || value === undefined) return "—";
    return field.isPercent ? formatNumber(value * 100, 2) : formatNumber(value, 0);
  }

  const overridden = new Set(base.overridden_fields);
  const hasDraft = Object.values(draft).some((v) => v !== undefined && v.trim() !== "");

  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">Varsayımlar</span>
        <span className="text-[11px] text-muted">Boş alanlar sistem tahminini kullanır</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {FIELD_CONFIG.map((field) => (
          <label key={field.key} className="block">
            <span className="flex items-center gap-1 text-[11px] text-muted">
              {field.label}
              {overridden.has(field.key) && (
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--accent)]"
                  title="Sizin girdiğiniz değer"
                />
              )}
              {field.isPercent && <span className="text-muted">(%)</span>}
              <InfoTooltip text={field.help} />
            </span>
            <input
              type="number"
              inputMode="decimal"
              step="any"
              value={draft[field.key] ?? ""}
              placeholder={placeholderFor(field)}
              onChange={(e) => onDraftChange({ ...draft, [field.key]: e.target.value })}
              className="mt-1 w-full rounded-md border border-border bg-surface px-2 py-1.5 font-tabular text-xs text-foreground placeholder:text-muted focus:border-[var(--accent)] focus:outline-none"
            />
          </label>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={onApply}
          disabled={!hasDraft}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
        >
          Uygula
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-surface-hover"
        >
          Sıfırla
        </button>
      </div>
    </div>
  );
}

function cellKey(wacc: number, tg: number): string {
  return `${wacc.toFixed(6)}|${tg.toFixed(6)}`;
}

function SensitivityMatrix({
  matrix,
  base,
  currency,
}: {
  matrix: SensitivityCell[];
  base: DcfAssumptions;
  currency: string;
}) {
  const { waccRows, tgCols, cellsByKey, minValue, maxValue } = useMemo(() => {
    const waccSet = new Set<number>();
    const tgSet = new Set<number>();
    const byKey = new Map<string, SensitivityCell>();
    let min = Infinity;
    let max = -Infinity;
    for (const cell of matrix) {
      waccSet.add(cell.wacc);
      tgSet.add(cell.terminal_growth);
      byKey.set(cellKey(cell.wacc, cell.terminal_growth), cell);
      if (cell.intrinsic_value_per_share !== null) {
        min = Math.min(min, cell.intrinsic_value_per_share);
        max = Math.max(max, cell.intrinsic_value_per_share);
      }
    }
    return {
      waccRows: [...waccSet].sort((a, b) => a - b),
      tgCols: [...tgSet].sort((a, b) => a - b),
      cellsByKey: byKey,
      minValue: min === Infinity ? 0 : min,
      maxValue: max === -Infinity ? 0 : max,
    };
  }, [matrix]);

  if (matrix.length === 0) return null;

  const maxAbs = Math.max(Math.abs(minValue), Math.abs(maxValue), 1e-9);
  const baseWacc = base.wacc;
  const baseTg = base.terminal_growth_rate;

  function tintFor(value: number | null): React.CSSProperties {
    if (value === null) return {};
    const intensity = Math.min(Math.abs(value) / maxAbs, 1) * 32 + 6;
    const varName = value >= 0 ? "--positive" : "--negative";
    return { backgroundColor: `color-mix(in srgb, var(${varName}) ${intensity.toFixed(0)}%, transparent)` };
  }

  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
        Duyarlılık Matrisi
        <InfoTooltip text="Satırlar WACC, sütunlar terminal büyüme oranı. Hücreler o kombinasyon için hisse başına içsel değeri gösterir. Vurgulu hücre baz senaryodaki değerlere karşılık gelir." />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-xs">
          <thead>
            <tr>
              <th className="pb-2 pr-2 text-left font-medium text-muted">WACC \ Terminal Büyüme</th>
              {tgCols.map((tg) => (
                <th key={tg} className="pb-2 px-2 text-right font-medium text-muted">
                  {formatPercent(tg, 1)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {waccRows.map((wacc) => (
              <tr key={wacc} className="border-t border-border">
                <td className="py-1.5 pr-2 font-medium text-muted">{formatPercent(wacc, 1)}</td>
                {tgCols.map((tg) => {
                  const cell = cellsByKey.get(cellKey(wacc, tg));
                  const value = cell?.intrinsic_value_per_share ?? null;
                  const isBaseCell =
                    baseWacc !== null &&
                    baseTg !== null &&
                    Math.abs(wacc - baseWacc) < 1e-9 &&
                    Math.abs(tg - baseTg) < 1e-9;
                  return (
                    <td
                      key={tg}
                      style={tintFor(value)}
                      className={cn(
                        "px-2 py-1.5 text-right font-tabular text-foreground",
                        isBaseCell && "ring-2 ring-inset ring-[var(--accent)]"
                      )}
                    >
                      {value === null ? "—" : formatCurrency(value, currency)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
