// Mirrors apps/api/app/schemas/watchlist.py (ADR-013). Her sayı backend'den
// gelir (skor değişimi dahil); burada yalnızca istek atılır.

import type { VerdictConfidence, VerdictPrice, VerdictQuality, VerdictSignal } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class WatchlistApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body || res.statusText;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // düz metin gövde — olduğu gibi göster
    }
    throw new WatchlistApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type WatchlistRefreshStatus = "SUCCESS" | "FAILED";
export type WatchlistRefreshTrigger = "scheduled" | "manual";

export interface WatchlistVerdictSummary {
  price: VerdictPrice | null;
  quality: VerdictQuality | null;
  confidence: VerdictConfidence | null;
  signal: VerdictSignal | null;
  signal_is_demo: boolean;
  headline: string | null;
  unsupported_reason: string | null;
}

export interface WatchlistItemSummary {
  ticker: string;
  name: string;
  added_at: string;
  has_analysis: boolean;
  price: number | null;
  currency: string | null;
  as_of: string | null;
  overall_score: number | null;
  verdict: WatchlistVerdictSummary | null;
  last_refreshed_at: string | null;
  previous_overall_score: number | null;
  score_change: number | null;
  last_job_at: string | null;
  last_job_status: WatchlistRefreshStatus | null;
  last_job_trigger: WatchlistRefreshTrigger | null;
  last_job_error: string | null;
  last_job_failed: boolean;
}

export interface WatchlistSchedulerStatus {
  enabled: boolean;
  schedule_label: string;
  next_run_at: string | null;
  running: boolean;
  last_run_trigger: WatchlistRefreshTrigger | null;
  last_run_started_at: string | null;
  last_run_finished_at: string | null;
  last_run_succeeded: number | null;
  last_run_failed: number | null;
}

export interface WatchlistResponse {
  items: WatchlistItemSummary[];
  scheduler: WatchlistSchedulerStatus;
}

export interface WatchlistRefreshStartResponse {
  started: boolean;
  tickers: number;
  message: string;
}

export const WATCHLIST_QUERY_KEY = ["watchlist"] as const;

export function getWatchlist(): Promise<WatchlistResponse> {
  return request("/api/watchlist");
}

export function addToWatchlist(ticker: string): Promise<WatchlistItemSummary> {
  return request("/api/watchlist", { method: "POST", body: JSON.stringify({ ticker }) });
}

export function removeFromWatchlist(ticker: string): Promise<void> {
  return request(`/api/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" });
}

export function startWatchlistRefresh(): Promise<WatchlistRefreshStartResponse> {
  return request("/api/watchlist/refresh", { method: "POST" });
}
