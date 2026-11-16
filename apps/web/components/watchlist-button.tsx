"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Star } from "lucide-react";
import {
  WATCHLIST_QUERY_KEY,
  addToWatchlist,
  getWatchlist,
  removeFromWatchlist,
} from "@/lib/api-watchlist";

/** Şirket sayfası başlığındaki "İzleme listesine ekle / çıkar" düğmesi
 * (ADR-013). Ana sayfadaki listeyle aynı React Query önbelleğini paylaşır. */
export function WatchlistButton({ ticker }: { ticker: string }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: WATCHLIST_QUERY_KEY, queryFn: getWatchlist });
  const inList = data?.items.some((i) => i.ticker === ticker) ?? false;

  const toggle = useMutation({
    mutationFn: async (): Promise<void> => {
      if (inList) await removeFromWatchlist(ticker);
      else await addToWatchlist(ticker);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: WATCHLIST_QUERY_KEY }),
  });

  const pending = isLoading || toggle.isPending;

  return (
    <button
      type="button"
      onClick={() => toggle.mutate()}
      disabled={pending}
      aria-pressed={inList}
      title={
        toggle.isError
          ? (toggle.error as Error).message
          : inList
            ? "Bu hisse izleme listende — ana sayfada özetini görürsün."
            : "Ana sayfadaki izleme listene ekler; listedeki hisseler toplu olarak yenilenir."
      }
      className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-foreground hover:bg-surface-hover disabled:opacity-50"
    >
      {pending ? (
        <Loader2 size={13} className="animate-spin" />
      ) : toggle.isError ? (
        <AlertTriangle size={13} className="text-[var(--warning)]" />
      ) : (
        <Star size={13} className={inList ? "fill-[var(--warning)] text-[var(--warning)]" : ""} />
      )}
      {inList ? "İzleme listesinden çıkar" : "İzleme listesine ekle"}
    </button>
  );
}
