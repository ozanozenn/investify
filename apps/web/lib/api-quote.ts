import { authHeaders, handleUnauthorized } from "./auth";
// Mirrors apps/api/app/schemas/quote.py:LiveQuote. Ayrı dosya (lib/api.ts /
// lib/types.ts değil) — diğer panellerin api-*.ts dosyalarıyla aynı düzen.

export interface LiveQuote {
  ticker: string;
  price: number;
  currency: string;
  market_cap: number | null;
  as_of: string | null;
  source: string;
  is_cached: boolean;
  stale: boolean;
  delay_note: string;
  stale_note: string | null;
  previous_close: number | null;
  change: number | null;
  change_fraction: number | null;
  direction: "up" | "down" | "flat" | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getCompanyQuote(ticker: string): Promise<LiveQuote> {
  const res = await fetch(`${API_BASE_URL}/api/companies/${encodeURIComponent(ticker)}/quote`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
    cache: "no-store",
  });
  handleUnauthorized(res.status);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  return res.json() as Promise<LiveQuote>;
}
