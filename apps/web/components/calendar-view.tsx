"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Landmark, Loader2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { getCalendar } from "@/lib/api-market";
import { formatDate } from "@/lib/format";

const CATEGORY_LABELS: Record<string, string> = {
  DIVIDEND: "Temettü",
  CAPITAL: "Sermaye Artırımı",
  IPO: "Halka Arz",
};

function daysFromToday(dateStr: string): number {
  const target = new Date(dateStr + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

function daysUntilLabel(days: number): string {
  if (days === 0) return "bugün";
  if (days === 1) return "yarın";
  return `${days} gün sonra`;
}

export function CalendarView() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => getCalendar(),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-muted">
        <Loader2 className="animate-spin" size={16} />
        Takvim yükleniyor...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 py-16 text-sm text-muted">
        <AlertTriangle size={16} className="text-[var(--warning)]" />
        Takvim yüklenemedi
      </div>
    );
  }

  const rateDecisions = data?.rate_decisions ?? [];
  const companyEvents = data?.company_events ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader title="Yaklaşan Faiz Kararları" subtitle="TCMB — Para Politikası Kurulu (PPK)" />
        <CardBody className="space-y-2">
          {rateDecisions.length === 0 && (
            <p className="text-xs text-muted">Yaklaşan bir toplantı tarihi bulunamadı.</p>
          )}
          {rateDecisions.map((d, i) => (
            <div key={i} className="flex items-center justify-between gap-2 rounded-md px-2 py-2 hover:bg-surface-hover">
              <div className="flex items-center gap-2">
                <Landmark size={14} className="shrink-0 text-muted" />
                <span className="text-sm text-foreground">{formatDate(d.date)}</span>
              </div>
              <Badge tone="accent">{daysUntilLabel(daysFromToday(d.date))}</Badge>
            </div>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Şirket Duyuruları"
          subtitle="Temettü, sermaye artırımı, halka arz — KAP'a en son bildirilenler"
        />
        <CardBody className="space-y-2">
          {companyEvents.length === 0 && (
            <p className="text-xs text-muted">Şu anda gösterilecek bir duyuru bulunamadı.</p>
          )}
          {companyEvents.map((e, i) => (
            <div key={i} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-surface-hover">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {e.ticker ? (
                    <Link href={`/company/${e.ticker}`} className="font-tabular font-semibold text-foreground hover:text-[var(--accent)]">
                      {e.ticker}
                    </Link>
                  ) : (
                    <span className="font-medium text-foreground">{e.company_name}</span>
                  )}
                  <Badge tone="neutral">{CATEGORY_LABELS[e.category] ?? e.category}</Badge>
                </div>
                <div className="mt-0.5 truncate text-muted">{e.title}</div>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-muted">
                <span>{formatDate(e.announced_at)}</span>
                <a href={e.source_url} target="_blank" rel="noreferrer" aria-label="KAP'ta görüntüle">
                  <ExternalLink size={12} />
                </a>
              </div>
            </div>
          ))}
          {companyEvents.length > 0 && (
            <p className="pt-1 text-[11px] text-muted">
              Tarihler duyuru tarihidir — kesin ödeme/kayıt tarihi için KAP bağlantısına bakın.
            </p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
