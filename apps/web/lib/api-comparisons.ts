import { authHeaders, handleUnauthorized } from "./auth";
// Mirrors apps/api/app/schemas/diff.py (SnapshotDiffResult / MetricDelta) and
// the AnalysisHistoryEntry shape returned by the existing
// /api/companies/{ticker}/analysis/history endpoint. Kept as a standalone
// hand-written mirror (see lib/types.ts for the rationale) rather than
// extending the shared lib/types.ts / lib/api.ts files, to avoid merge
// conflicts with other in-flight panels touching those shared files.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ComparisonApiError extends Error {
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
    throw new ComparisonApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface AnalysisHistoryEntry {
  id: number;
  created_at: string; // ISO datetime
  as_of: string; // ISO datetime
  overall_score: number | null;
}

export interface MetricDelta {
  metric: string; // machine key e.g. "revenue_growth_yoy"
  label: string; // human label — already in readable form, use directly
  previous: number | null;
  current: number | null;
  delta: number | null; // current - previous
  is_notable: boolean;
}

export interface SnapshotDiffResult {
  ticker: string;
  from_snapshot_id: number;
  to_snapshot_id: number;
  from_as_of: string; // ISO datetime
  to_as_of: string; // ISO datetime
  deltas: MetricDelta[];
  notable_changes: MetricDelta[];
  valuation_direction: "cheaper" | "more_expensive" | "unchanged" | "unknown";
  overall_score_delta: number | null;
  thesis_strength: "STRENGTHENED" | "WEAKENED" | "UNCHANGED";
  thesis_strength_reason: string;
}

export function getAnalysisHistory(ticker: string): Promise<AnalysisHistoryEntry[]> {
  return request(`/api/companies/${encodeURIComponent(ticker)}/analysis/history`);
}

export function compareSnapshots(
  ticker: string,
  fromId?: number,
  toId?: number
): Promise<SnapshotDiffResult> {
  const params = new URLSearchParams();
  if (fromId !== undefined) params.set("from_id", String(fromId));
  if (toId !== undefined) params.set("to_id", String(toId));
  const qs = params.toString();
  return request(
    `/api/companies/${encodeURIComponent(ticker)}/analysis/compare${qs ? `?${qs}` : ""}`
  );
}
