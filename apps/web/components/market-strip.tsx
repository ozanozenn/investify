"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Landmark, Loader2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { getCalendar } from "@/lib/api-market";
import { formatDate } from "@/lib/format";

const EVENT_LIMIT = 4;

const CATEGORY_LABELS: Record<string, string> = {
  DIVIDEND: "Temettü",
  CAPITAL: "Sermaye Artırımı",
  IPO: "Halka Arz",
};

function daysUntilLabel(dateStr: string): string {
  const target = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((target.getTime() - today.getTime()) / 86_400_000);
  if (days === 0) return "bugün";
  if (days === 1) return "yarın";
  return `${days} gün sonra`;
}

/** Ana sayfadaki küçük piyasa şeridi: sıradaki TCMB faiz kararı ve KAP'a en
 * son bildirilen önemli şirket olayları. Takvim sayfasıyla aynı uç noktayı
 * (`GET /api/calendar`) ve aynı önbellek anahtarını kullanır. */
export function MarketStrip() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => getCalendar(),
    retry: false,
  });

  const nextRate = data?.rate_decisions[0] ?? null;
  const events = (data?.company_events ?? []).slice(0, EVENT_LIMIT);

  return (
    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,2.4fr)]">
      <Card>
        <CardBody className="flex h-full flex-col justify-center gap-1 py-3">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
            <Landmark size={12} />
            Sıradaki TCMB faiz kararı
          </div>
          {isLoading ? (
            <Loader2 size={14} className="animate-spin text-muted" />
          ) : nextRate ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-foreground">{formatDate(nextRate.date)}</span>
              <Badge tone="accent">{daysUntilLabel(nextRate.date)}</Badge>
            </div>
          ) : (
            <span className="text-xs text-muted">
              {isError ? "Takvim şu anda alınamadı" : "Yaklaşan toplantı tarihi bilinmiyor"}
            </span>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardBody className="py-3">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">
              Son önemli şirket olayları (KAP)
            </span>
            <Link href="/takvim" className="text-[11px] text-muted hover:text-foreground">
              Tümü →
            </Link>
          </div>
          {isLoading && <Loader2 size={14} className="animate-spin text-muted" />}
          {isError && (
            <p className="flex items-center gap-1.5 text-xs text-muted">
              <AlertTriangle size={12} className="text-[var(--warning)]" />
              KAP olayları şu anda alınamadı
            </p>
          )}
          {data && events.length === 0 && (
            <p className="text-xs text-muted">Son günlerde temettü, sermaye artırımı ya da halka arz duyurusu yok.</p>
          )}
          <ul className="space-y-1">
            {events.map((e, i) => (
              <li key={i} className="flex items-center gap-2 text-xs">
                {e.ticker ? (
                  <Link
                    href={`/company/${e.ticker}`}
                    className="shrink-0 font-tabular font-semibold text-foreground hover:text-[var(--accent)]"
                  >
                    {e.ticker}
                  </Link>
                ) : (
                  <span className="max-w-[140px] shrink-0 truncate font-medium text-foreground">{e.company_name}</span>
                )}
                <Badge tone="neutral" className="shrink-0">
                  {CATEGORY_LABELS[e.category] ?? e.category}
                </Badge>
                <span className="min-w-0 flex-1 truncate text-muted" title={e.title}>
                  {e.title}
                </span>
                <span className="shrink-0 text-muted">{formatDate(e.announced_at)}</span>
                <a
                  href={e.source_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="KAP'ta görüntüle"
                  className="shrink-0 text-muted hover:text-foreground"
                >
                  <ExternalLink size={11} />
                </a>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
