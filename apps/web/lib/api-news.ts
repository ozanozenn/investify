// Mirrors apps/api/app/schemas/news.py:NewsResult and its nested schema.
// Kept as a hand-written mirror (see lib/types.ts for the same
// convention) rather than a codegen step.

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
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  published_at: string;
}

export interface NewsResult {
  ticker: string;
  items: NewsItem[];
}

export function getCompanyNews(ticker: string): Promise<NewsResult> {
  return request(`/api/companies/${encodeURIComponent(ticker)}/news`);
}
