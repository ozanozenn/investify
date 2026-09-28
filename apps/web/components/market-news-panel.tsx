"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Loader2 } from "lucide-react";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { getMarketNews } from "@/lib/api-market";
import { formatRelativeTime } from "@/lib/format";

export function MarketNewsPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["market-news"],
    queryFn: () => getMarketNews(30),
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Genel Piyasa Haberleri" subtitle="Google Haberler" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <Loader2 className="animate-spin" size={14} />
          Haberler yükleniyor...
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader title="Genel Piyasa Haberleri" subtitle="Google Haberler" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <AlertTriangle size={14} className="text-[var(--warning)]" />
          Haberler yüklenemedi
        </CardBody>
      </Card>
    );
  }

  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader title="Genel Piyasa Haberleri" subtitle="Google Haberler — Borsa İstanbul" />
      <CardBody className="space-y-2">
        {items.length === 0 && <p className="text-xs text-muted">Şu anda gösterilecek haber bulunamadı.</p>}
        {items.map((item, i) => (
          <a
            key={i}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-surface-hover"
          >
            <div className="min-w-0">
              <div className="truncate text-foreground">{item.title}</div>
              <div className="mt-0.5 text-muted">
                {item.source} · {formatRelativeTime(item.published_at)}
              </div>
            </div>
            <ExternalLink size={12} className="shrink-0 text-muted" />
          </a>
        ))}
      </CardBody>
    </Card>
  );
}
