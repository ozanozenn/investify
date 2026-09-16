"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import {
  ComparisonApiError,
  compareSnapshots,
  getAnalysisHistory,
  type AnalysisHistoryEntry,
  type MetricDelta,
  type SnapshotDiffResult,
} from "@/lib/api-comparisons";
import { formatDateTime, formatMultiple, formatNumber, formatPercent } from "@/lib/format";

type Tone = "neutral" | "positive" | "negative" | "warning" | "accent";

/** Per-metric formatter selection — some tracked metrics are fractions
 * (format as %), some are plain multiples/scores (format as number/"x"). */
const METRIC_FORMATTERS: Record<string, (value: number | null) => string> = {
  revenue_growth_yoy: (v) => formatPercent(v),
  ebitda_margin: (v) => formatPercent(v),
  roe: (v) => formatPercent(v),
  net_debt_to_ebitda: (v) => formatMultiple(v),
  pe: (v) => formatNumber(v, 1),
  overall_score: (v) => formatNumber(v, 1),
};

function formatMetricValue(metric: string, value: number | null): string {
  const formatter = METRIC_FORMATTERS[metric] ?? ((v: number | null) => formatNumber(v, 2));
  return formatter(value);
}

function formatMetricDelta(metric: string, value: number | null): string {
  if (value === null) return "—";
  const magnitude = formatMetricValue(metric, Math.abs(value));
  if (magnitude === "—") return "—";
  if (value > 0) return `+${magnitude}`;
  if (value < 0) return `-${magnitude}`;
  return magnitude;
}

/** The 409 "not enough snapshots yet" body is JSON ({ detail: "..." }) —
 * try to surface the human-readable detail, fall back to the raw message. */
function extractDetail(message: string): string | null {
  try {
    const parsed = JSON.parse(message);
    if (parsed && typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // not JSON — ignore
  }
  return null;
}

function NotEnoughHistory({ count }: { count: number }) {
  return (
    <Card>
      <CardHeader title="Since Previous Analysis" subtitle="Önceki analize göre değişim" />
      <CardBody>
        <p className="text-sm text-muted">
          Karşılaştırma için en az iki analiz gerekiyor. Şu an {count} analiz var — tekrar refresh
          yapınca karşılaştırma burada görünecek.
        </p>
      </CardBody>
    </Card>
  );
}

function InlineError() {
  return (
    <Card>
      <CardHeader title="Since Previous Analysis" subtitle="Önceki analize göre değişim" />
      <CardBody>
        <p className="text-sm text-muted">Karşılaştırma yüklenemedi.</p>
      </CardBody>
    </Card>
  );
}

const VALUATION_DIRECTION: Record<SnapshotDiffResult["valuation_direction"], { label: string; tone: Tone }> = {
  cheaper: { label: "Daha ucuz", tone: "positive" },
  more_expensive: { label: "Daha pahalı", tone: "negative" },
  unchanged: { label: "Değişmedi", tone: "neutral" },
  unknown: { label: "Bilinmiyor", tone: "neutral" },
};

const THESIS_STRENGTH: Record<SnapshotDiffResult["thesis_strength"], { label: string; tone: Tone }> = {
  STRENGTHENED: { label: "Güçlendi", tone: "positive" },
  WEAKENED: { label: "Zayıfladı", tone: "negative" },
  UNCHANGED: { label: "Değişmedi", tone: "neutral" },
};

function HistorySelect({
  label,
  history,
  value,
  onChange,
}: {
  label: string;
  history: AnalysisHistoryEntry[];
  value: number | undefined;
  onChange: (id: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      <select
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-foreground"
      >
        {value === undefined && <option value="">Otomatik (en son)</option>}
        {history.map((entry) => (
          <option key={entry.id} value={entry.id}>
            {formatDateTime(entry.created_at)}
            {entry.overall_score !== null ? ` — skor ${entry.overall_score.toFixed(0)}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

function DeltaTable({ deltas }: { deltas: MetricDelta[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[480px] text-xs">
        <thead>
          <tr className="text-left text-muted">
            <th className="pb-2 font-medium">Metrik</th>
            <th className="pb-2 font-medium">Önceki</th>
            <th className="pb-2 font-medium">Şimdi</th>
            <th className="pb-2 font-medium">Değişim</th>
          </tr>
        </thead>
        <tbody>
          {deltas.map((d) => (
            <tr
              key={d.metric}
              className={d.is_notable ? "border-t border-border bg-surface-hover" : "border-t border-border"}
            >
              <td className="py-1.5 pr-3 text-foreground">
                <span className="flex items-center gap-1.5">
                  {d.is_notable && (
                    <span
                      aria-hidden
                      className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]"
                    />
                  )}
                  {d.label}
                </span>
              </td>
              <td className="py-1.5 pr-3 font-tabular text-muted">{formatMetricValue(d.metric, d.previous)}</td>
              <td className="py-1.5 pr-3 font-tabular text-foreground">{formatMetricValue(d.metric, d.current)}</td>
              <td className="py-1.5 font-tabular text-foreground">{formatMetricDelta(d.metric, d.delta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ComparisonResult({ data }: { data: SnapshotDiffResult }) {
  const strength = THESIS_STRENGTH[data.thesis_strength];
  const direction = VALUATION_DIRECTION[data.valuation_direction];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Thesis Strength</div>
          <div className="flex items-center gap-2">
            <Badge tone={strength.tone}>{strength.label}</Badge>
          </div>
          <p className="mt-1 max-w-md text-xs text-muted">{data.thesis_strength_reason}</p>
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Değerleme</div>
          <Badge tone={direction.tone}>{direction.label}</Badge>
        </div>
      </div>
      <DeltaTable deltas={data.deltas} />
    </div>
  );
}

export function HistoricalComparisonPanel({ ticker }: { ticker: string }) {
  const [fromId, setFromId] = useState<number | undefined>(undefined);
  const [toId, setToId] = useState<number | undefined>(undefined);

  const historyQuery = useQuery({
    queryKey: ["analysis-history-compare", ticker],
    queryFn: () => getAnalysisHistory(ticker),
    retry: false,
  });

  const history = historyQuery.data ?? [];
  const hasEnoughHistory = history.length >= 2;

  const compareQuery = useQuery({
    queryKey: ["analysis-compare", ticker, fromId, toId],
    queryFn: () => compareSnapshots(ticker, fromId, toId),
    enabled: hasEnoughHistory,
    retry: false,
  });

  if (historyQuery.isLoading) {
    return (
      <Card>
        <CardHeader title="Since Previous Analysis" subtitle="Önceki analize göre değişim" />
        <CardBody>
          <p className="text-sm text-muted">Yükleniyor...</p>
        </CardBody>
      </Card>
    );
  }

  if (historyQuery.isError) {
    const error = historyQuery.error;
    if (error instanceof ComparisonApiError && error.status === 404) {
      return <NotEnoughHistory count={0} />;
    }
    return <InlineError />;
  }

  if (!hasEnoughHistory) {
    return <NotEnoughHistory count={history.length} />;
  }

  const compareError = compareQuery.error;
  const isNotEnoughSnapshots = compareError instanceof ComparisonApiError && compareError.status === 409;

  return (
    <Card>
      <CardHeader
        title="Since Previous Analysis"
        subtitle="Önceki analize göre değişim ve tez gücü"
        action={
          <div className="flex flex-wrap items-end gap-3">
            <HistorySelect label="Karşılaştırılan" history={history} value={fromId} onChange={setFromId} />
            <HistorySelect label="Yeni" history={history} value={toId} onChange={setToId} />
          </div>
        }
      />
      <CardBody>
        {compareQuery.isLoading && <p className="text-sm text-muted">Karşılaştırma hesaplanıyor...</p>}
        {compareQuery.isError && isNotEnoughSnapshots && (
          <p className="text-sm text-muted">
            {extractDetail(compareError.message) ??
              "Karşılaştırma için en az iki analiz gerekiyor. Tekrar refresh yapınca karşılaştırma burada görünecek."}
          </p>
        )}
        {compareQuery.isError && !isNotEnoughSnapshots && <p className="text-sm text-muted">Karşılaştırma yüklenemedi.</p>}
        {compareQuery.data && <ComparisonResult data={compareQuery.data} />}
      </CardBody>
    </Card>
  );
}
