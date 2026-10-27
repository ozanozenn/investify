"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowDown, ArrowUp, Loader2, RefreshCw, Star, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { Badge, toneForScore } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import {
  WATCHLIST_QUERY_KEY,
  getWatchlist,
  removeFromWatchlist,
  startWatchlistRefresh,
  type WatchlistItemSummary,
  type WatchlistSchedulerStatus,
} from "@/lib/api-watchlist";
import { formatCurrency, formatDateTime, formatNumber, formatRelativeTime } from "@/lib/format";
import { CONFIDENCE_LABELS, PRICE_LABELS, QUALITY_LABELS, SIGNAL_LABELS } from "@/lib/verdict-labels";

const POLL_WHILE_RUNNING_MS = 3000;

const signedFormatter = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

/** Ana sayfadaki "İzleme Listem" (ADR-013). Tüm sayılar ve hükümler
 * backend özetinden gelir; bu bileşen yalnızca biçimlendirir. */
export function WatchlistPanel() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: WATCHLIST_QUERY_KEY,
    queryFn: getWatchlist,
    staleTime: 0, // şirket sayfasında yapılan yenilemeler ana sayfaya dönünce görünsün
    refetchInterval: (query) => (query.state.data?.scheduler.running ? POLL_WHILE_RUNNING_MS : false),
  });

  const refresh = useMutation({
    mutationFn: startWatchlistRefresh,
    onSettled: () => queryClient.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY }),
  });

  const remove = useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY }),
  });

  // Toplu yenileme bitince şirket sayfalarının önbelleği de tazelensin.
  const running = data?.scheduler.running ?? false;
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !running) {
      queryClient.invalidateQueries({ queryKey: ["company-analysis"] });
    }
    wasRunning.current = running;
  }, [running, queryClient]);

  const items = data?.items ?? [];
  const showSignal = items.some((i) => i.verdict?.signal_is_demo);
  const busy = running || refresh.isPending;

  return (
    <Card>
      <CardHeader
        title="İzleme Listem"
        subtitle={data ? schedulerSubtitle(data.scheduler) : undefined}
        action={
          <button
            type="button"
            onClick={() => refresh.mutate()}
            disabled={busy || items.length === 0}
            title="Listedeki tüm hisseleri sırayla yeniden analiz eder (arka planda çalışır)."
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-hover disabled:opacity-50"
          >
            <RefreshCw size={13} className={busy ? "animate-spin" : ""} />
            {busy ? "Yenileniyor..." : "Şimdi yenile"}
          </button>
        }
      />

      {refresh.isError && (
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-xs text-[var(--warning)]">
          <AlertTriangle size={13} />
          {(refresh.error as Error).message}
        </div>
      )}
      {remove.isError && (
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-xs text-[var(--warning)]">
          <AlertTriangle size={13} />
          {(remove.error as Error).message}
        </div>
      )}

      {isLoading && (
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <Loader2 className="animate-spin" size={14} />
          İzleme listesi yükleniyor...
        </CardBody>
      )}

      {isError && (
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <AlertTriangle size={14} className="text-[var(--warning)]" />
          İzleme listesi yüklenemedi: {(error as Error).message}
        </CardBody>
      )}

      {data && items.length === 0 && <EmptyState scheduler={data.scheduler} />}

      {data && items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="border-b border-border text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Hisse</th>
                  <th className="px-3 py-2 text-right font-medium">Fiyat</th>
                  <th className="px-3 py-2 font-medium">Hüküm</th>
                  {showSignal && <th className="px-3 py-2 font-medium">Sinyal (Demo)</th>}
                  <th className="px-3 py-2 text-right font-medium">Genel Skor</th>
                  <th className="px-3 py-2 font-medium">Güncellendi</th>
                  <th className="w-10 px-2 py-2">
                    <span className="sr-only">Çıkar</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <WatchlistRow
                    key={item.ticker}
                    item={item}
                    showSignal={showSignal}
                    removing={remove.isPending && remove.variables === item.ticker}
                    onRemove={() => remove.mutate(item.ticker)}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <LastRunFooter scheduler={data.scheduler} showSignalNote={showSignal} />
        </>
      )}
    </Card>
  );
}

function schedulerSubtitle(scheduler: WatchlistSchedulerStatus): string {
  if (!scheduler.enabled) return "Otomatik yenileme kapalı — listeyi \"Şimdi yenile\" ile güncelleyebilirsin.";
  const next = scheduler.next_run_at ? ` · sonraki: ${formatDateTime(scheduler.next_run_at)}` : "";
  return `Otomatik yenileme: ${scheduler.schedule_label}${next}`;
}

function EmptyState({ scheduler }: { scheduler: WatchlistSchedulerStatus }) {
  return (
    <CardBody className="flex flex-col items-center gap-2 py-10 text-center">
      <Star size={22} className="text-muted" />
      <p className="text-sm font-medium text-foreground">İzleme listen henüz boş.</p>
      <p className="max-w-md text-xs leading-relaxed text-muted">
        Yukarıdaki aramadan bir şirket aç ve başlıktaki <strong>İzleme listesine ekle</strong> düğmesine bas.
        Listedeki hisseler{" "}
        {scheduler.enabled ? `otomatik olarak yenilenir (${scheduler.schedule_label})` : "\"Şimdi yenile\" ile toplu yenilenir"}{" "}
        ve burada fiyat, hüküm ve skor değişimiyle tek bakışta görünür.
      </p>
    </CardBody>
  );
}

function WatchlistRow({
  item,
  showSignal,
  removing,
  onRemove,
}: {
  item: WatchlistItemSummary;
  showSignal: boolean;
  removing: boolean;
  onRemove: () => void;
}) {
  const verdict = item.verdict;

  return (
    <tr className="border-b border-border last:border-b-0 hover:bg-surface-hover">
      <td className="px-4 py-2.5">
        <Link href={`/company/${item.ticker}`} className="font-tabular text-sm font-semibold text-foreground hover:text-[var(--accent)]">
          {item.ticker}
        </Link>
        <div className="max-w-[220px] truncate text-muted" title={item.name}>
          {item.name}
        </div>
      </td>

      <td className="px-3 py-2.5 text-right font-tabular text-foreground">
        {item.price !== null ? formatCurrency(item.price, item.currency ?? "TRY") : "—"}
      </td>

      <td className="px-3 py-2.5">
        {!item.has_analysis ? (
          <span className="text-muted">Henüz analiz yok</span>
        ) : !verdict ? (
          <span className="text-muted">—</span>
        ) : verdict.unsupported_reason ? (
          <Badge tone="neutral">Desteklenmeyen sektör</Badge>
        ) : (
          <div className="flex flex-wrap items-center gap-1" title={verdict.headline ?? undefined}>
            {verdict.price ? (
              <Badge tone={PRICE_LABELS[verdict.price].tone}>{PRICE_LABELS[verdict.price].label}</Badge>
            ) : (
              <Badge tone="neutral">Fiyat net değil</Badge>
            )}
            {verdict.quality && (
              <Badge tone={QUALITY_LABELS[verdict.quality].tone}>{QUALITY_LABELS[verdict.quality].label}</Badge>
            )}
            {verdict.confidence && (
              <span className="text-[11px] text-muted">Güven: {CONFIDENCE_LABELS[verdict.confidence].label}</span>
            )}
          </div>
        )}
      </td>

      {showSignal && (
        <td className="px-3 py-2.5">
          {verdict?.signal_is_demo && verdict.signal ? (
            <Badge tone={SIGNAL_LABELS[verdict.signal].tone}>{SIGNAL_LABELS[verdict.signal].label}</Badge>
          ) : (
            <span className="text-muted">{item.has_analysis ? "Verilmedi" : "—"}</span>
          )}
        </td>
      )}

      <td className="px-3 py-2.5 text-right">
        <ScoreCell score={item.overall_score} change={item.score_change} previous={item.previous_overall_score} />
      </td>

      <td className="px-3 py-2.5">
        <div className="text-foreground" title={item.last_refreshed_at ? formatDateTime(item.last_refreshed_at) : undefined}>
          {formatRelativeTime(item.last_refreshed_at)}
        </div>
        {item.last_job_failed && (
          <div className="mt-0.5" title={item.last_job_error ?? undefined}>
            <Badge tone="warning">
              <AlertTriangle size={11} />
              {item.last_job_trigger === "manual" ? "Son toplu yenileme başarısız" : "Son otomatik yenileme başarısız"}
            </Badge>
          </div>
        )}
      </td>

      <td className="px-2 py-2.5 text-right">
        <button
          type="button"
          onClick={onRemove}
          disabled={removing}
          aria-label={`${item.ticker} hissesini izleme listesinden çıkar`}
          title="İzleme listesinden çıkar"
          className="rounded-md p-1.5 text-muted hover:bg-surface hover:text-[var(--negative)] disabled:opacity-50"
        >
          {removing ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />}
        </button>
      </td>
    </tr>
  );
}

function ScoreCell({ score, change, previous }: { score: number | null; change: number | null; previous: number | null }) {
  if (score === null) return <span className="text-muted">—</span>;
  return (
    <div className="flex items-center justify-end gap-2">
      <Badge tone={toneForScore(score)} className="font-tabular">
        {formatNumber(score, 0)}
      </Badge>
      {change !== null && (
        <span
          className={`flex items-center gap-0.5 font-tabular text-[11px] ${
            change > 0 ? "text-[var(--positive)]" : change < 0 ? "text-[var(--negative)]" : "text-muted"
          }`}
          title={previous !== null ? `Önceki analizde ${formatNumber(previous, 1)}` : undefined}
        >
          {change > 0 && <ArrowUp size={11} />}
          {change < 0 && <ArrowDown size={11} />}
          {signedFormatter.format(change)}
        </span>
      )}
    </div>
  );
}

function LastRunFooter({
  scheduler,
  showSignalNote,
}: {
  scheduler: WatchlistSchedulerStatus;
  showSignalNote: boolean;
}) {
  const hasLastRun = scheduler.last_run_finished_at !== null;
  if (!hasLastRun && !showSignalNote) return null;
  return (
    <div className="space-y-0.5 border-t border-border px-4 py-2 text-[11px] text-muted">
      {hasLastRun && (
        <p>
          Son toplu yenileme ({scheduler.last_run_trigger === "manual" ? "elle" : "otomatik"}):{" "}
          {formatRelativeTime(scheduler.last_run_finished_at)} — {scheduler.last_run_succeeded ?? 0} başarılı,{" "}
          {scheduler.last_run_failed ?? 0} başarısız.
        </p>
      )}
      {showSignalNote && <p>Sinyal deneme amaçlıdır ve yatırım tavsiyesi değildir; kararlar sana aittir.</p>}
    </div>
  );
}
