"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ExternalLink, Loader2 } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { getMarketDisclosures } from "@/lib/api-market";
import { formatRelativeTime } from "@/lib/format";

const CATEGORY_LABELS: Record<string, string> = {
  FINANCIAL_RESULT: "Finansal Sonuç",
  DIVIDEND: "Temettü",
  INVESTMENT: "Yatırım",
  CONTRACT: "Sözleşme",
  MANAGEMENT: "Yönetim",
  CAPITAL: "Sermaye",
  OTHER: "Diğer",
};

export function MarketDisclosuresPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["market-disclosures"],
    queryFn: () => getMarketDisclosures(40),
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Son KAP Açıklamaları" subtitle="Tüm BIST şirketleri" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <Loader2 className="animate-spin" size={14} />
          Açıklamalar yükleniyor...
        </CardBody>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader title="Son KAP Açıklamaları" subtitle="Tüm BIST şirketleri" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <AlertTriangle size={14} className="text-[var(--warning)]" />
          Açıklamalar yüklenemedi
        </CardBody>
      </Card>
    );
  }

  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader title="Son KAP Açıklamaları" subtitle="Tüm BIST şirketleri — Kamuyu Aydınlatma Platformu" />
      <CardBody className="space-y-2">
        {items.length === 0 && <p className="text-xs text-muted">Şu anda gösterilecek açıklama bulunamadı.</p>}
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-surface-hover">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                {item.ticker ? (
                  <Link href={`/company/${item.ticker}`} className="font-tabular font-semibold text-foreground hover:text-[var(--accent)]">
                    {item.ticker}
                  </Link>
                ) : (
                  <span className="font-medium text-foreground">{item.company_name}</span>
                )}
                <Badge tone="neutral">{CATEGORY_LABELS[item.category] ?? item.category}</Badge>
              </div>
              <div className="mt-0.5 truncate text-muted">{item.title}</div>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-muted">
              <span>{formatRelativeTime(item.published_at)}</span>
              <a href={item.source_url} target="_blank" rel="noreferrer" aria-label="KAP'ta görüntüle">
                <ExternalLink size={12} />
              </a>
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}
