"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { getCompanyQuote } from "@/lib/api-quote";
import { cn } from "@/lib/cn";
import { formatCompact, formatDateTime, formatPercent, formatRelativeTime } from "@/lib/format";
import type { MarketContext } from "@/lib/types";

const QUOTE_REFETCH_MS = 60_000;

const DIRECTION_CLASS = {
  up: "text-[var(--positive)]",
  down: "text-[var(--negative)]",
  flat: "text-muted",
} as const;

/** Başlıktaki fiyat bloğu: sayfa açılınca güncel fiyatı (önbellekli, 60 sn'de
 * bir) çeker; yüklenirken veya hata olursa analizdeki fiyatı gösterir.
 * Değişim ve yön backend'den gelir — burada hiçbir şey hesaplanmaz. */
export function LivePrice({ ticker, market }: { ticker: string; market: MarketContext }) {
  const { data: quote } = useQuery({
    queryKey: ["company-quote", ticker],
    queryFn: () => getCompanyQuote(ticker),
    refetchInterval: QUOTE_REFETCH_MS,
  });

  if (!quote) {
    return (
      <div className="text-right">
        <div className="font-tabular text-2xl font-semibold text-foreground">
          {market.price ? `${market.price.toFixed(2)} ${market.currency}` : "—"}
        </div>
        <div className="mt-0.5 text-xs text-muted">
          Piyasa Değeri {formatCompact(market.market_cap, market.currency)}
        </div>
        <div className="mt-0.5 text-[11px] text-muted">
          Son analizdeki fiyat · {formatRelativeTime(market.as_of)}
        </div>
      </div>
    );
  }

  const changeText =
    quote.change !== null && quote.direction !== null
      ? `${quote.direction === "up" ? "+" : ""}${quote.change.toFixed(2)} (${quote.direction === "up" ? "+" : ""}${formatPercent(quote.change_fraction, 2)})`
      : null;

  return (
    <div className="text-right">
      <div className="flex items-baseline justify-end gap-2">
        {quote.stale && <Badge tone="warning">Son analiz fiyatı</Badge>}
        <span className="font-tabular text-2xl font-semibold text-foreground">
          {quote.price.toFixed(2)} {quote.currency}
        </span>
        {changeText && quote.direction && (
          <span
            className={cn("font-tabular text-xs font-medium", DIRECTION_CLASS[quote.direction])}
            title="Önceki kapanışa göre değişim"
          >
            {changeText}
          </span>
        )}
      </div>
      <div className="mt-0.5 text-xs text-muted">
        Piyasa Değeri {formatCompact(quote.market_cap, quote.currency)}
      </div>
      <div className={cn("ml-auto mt-0.5 max-w-xs text-[11px]", quote.stale ? "text-[var(--warning)]" : "text-muted")}>
        {formatDateTime(quote.as_of)} itibarıyla · {quote.stale ? quote.stale_note : quote.delay_note}
      </div>
    </div>
  );
}
