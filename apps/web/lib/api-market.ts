import { authHeaders, handleUnauthorized } from "./auth";
// Mirrors apps/api/app/schemas/news.py's Market* schemas.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
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
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  handleUnauthorized(res.status);
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface MarketNewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
}

export interface MarketNewsResult {
  items: MarketNewsItem[];
}

export interface MarketDisclosureItem {
  ticker: string | null;
  company_name: string;
  title: string;
  subject: string | null;
  category: string;
  published_at: string;
  source_url: string;
}

export interface MarketDisclosureResult {
  items: MarketDisclosureItem[];
}

export function getMarketNews(limit = 20): Promise<MarketNewsResult> {
  return request(`/api/market/news?limit=${limit}`);
}

export function getMarketDisclosures(limit = 30): Promise<MarketDisclosureResult> {
  return request(`/api/market/disclosures?limit=${limit}`);
}

export interface RateDecisionEvent {
  date: string;
}

export interface CompanyEvent {
  ticker: string | null;
  company_name: string;
  category: string;
  title: string;
  announced_at: string;
  source_url: string;
}

export interface CalendarResult {
  rate_decisions: RateDecisionEvent[];
  company_events: CompanyEvent[];
}

export function getCalendar(): Promise<CalendarResult> {
  return request(`/api/calendar`);
}
