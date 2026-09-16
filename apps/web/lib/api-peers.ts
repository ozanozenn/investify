// Mirrors apps/api/app/schemas/peer.py:PeerComparisonResult and its nested
// schemas. Kept as a hand-written mirror (see lib/types.ts for the same
// convention) rather than a codegen step — single place to update if the
// API schema drifts.

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

export interface PeerCompanyMetric {
  ticker: string;
  name: string;
  overall_score: number | null;
  pe: number | null;
  pb: number | null;
  ev_ebitda: number | null;
  as_of: string;
}

export type PeerGroupBasis = "industry" | "sector" | "none";

export interface PeerComparisonResult {
  ticker: string;
  sector: string | null;
  industry: string | null;
  peer_group_basis: PeerGroupBasis;
  peer_count: number;
  peers: PeerCompanyMetric[];
  this_company: PeerCompanyMetric;
  median_overall_score: number | null;
  median_pe: number | null;
  median_pb: number | null;
  median_ev_ebitda: number | null;
  overall_score_vs_median: number | null;
  insufficient_peers: boolean;
  insufficient_peers_reason: string | null;
}

export function getPeerComparison(ticker: string): Promise<PeerComparisonResult> {
  return request(`/api/companies/${encodeURIComponent(ticker)}/analysis/peers`);
}
