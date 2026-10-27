import { authHeaders, handleUnauthorized } from "./auth";
// Mirrors apps/api/app/schemas/dcf.py:DcfResult and its nested schemas.
// Kept as a hand-written mirror (same practice as lib/types.ts) rather than a
// codegen step. New file (not lib/api.ts / lib/types.ts) so this panel's
// work stays isolated from the shared frontend files while it lands in
// parallel with the historical-comparison and peer-comparison panels.

export interface DcfAssumptions {
  revenue_growth_rate: number | null;
  ebit_margin: number | null;
  tax_rate: number | null;
  da_percent_of_revenue: number | null;
  capex_percent_of_revenue: number | null;
  working_capital_change_percent_of_revenue: number | null;
  wacc: number | null;
  terminal_growth_rate: number | null;
  net_debt: number | null;
  shares_outstanding: number | null;
  overridden_fields: string[];
}

export interface DcfScenarioResult {
  scenario: "bear" | "base" | "bull";
  assumptions: DcfAssumptions;
  projected_fcf: number[];
  terminal_value: number | null;
  enterprise_value: number | null;
  equity_value: number | null;
  intrinsic_value_per_share: number | null;
  upside_vs_current_price: number | null;
  missing_fields: string[];
}

export interface SensitivityCell {
  wacc: number;
  terminal_growth: number;
  intrinsic_value_per_share: number | null;
}

export interface DcfResult {
  bear: DcfScenarioResult;
  base: DcfScenarioResult;
  bull: DcfScenarioResult;
  sensitivity_matrix: SensitivityCell[];
  missing_fields: string[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class DcfApiError extends Error {
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
    throw new DcfApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

/** Fields the /analysis/dcf endpoint accepts as override query params. */
type DcfOverrideKey = Exclude<keyof DcfAssumptions, "overridden_fields">;

export function getCompanyDcf(
  ticker: string,
  overrides?: Partial<DcfAssumptions>
): Promise<DcfResult> {
  const params = new URLSearchParams();
  if (overrides) {
    for (const [key, value] of Object.entries(overrides)) {
      if (key === "overridden_fields") continue;
      if (value === null || value === undefined || typeof value !== "number" || Number.isNaN(value)) continue;
      params.set(key as DcfOverrideKey, String(value));
    }
  }
  const qs = params.toString();
  return request(`/api/companies/${encodeURIComponent(ticker)}/analysis/dcf${qs ? `?${qs}` : ""}`);
}
