import type { CompanyAnalysisResponse, CompanySearchResult } from "./types";

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

export function searchCompanies(query: string): Promise<CompanySearchResult[]> {
  if (!query.trim()) return Promise.resolve([]);
  return request(`/api/companies/search?q=${encodeURIComponent(query)}`);
}

export function getCompanyAnalysis(ticker: string): Promise<CompanyAnalysisResponse> {
  return request(`/api/companies/${encodeURIComponent(ticker)}/analysis`);
}

export function refreshCompanyAnalysis(ticker: string): Promise<CompanyAnalysisResponse> {
  return request(`/api/companies/${encodeURIComponent(ticker)}/refresh`, { method: "POST" });
}
