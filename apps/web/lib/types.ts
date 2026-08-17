// Mirrors apps/api/app/schemas/api.py:CompanyAnalysisResponse and its
// nested schemas. Kept as a hand-written mirror rather than a codegen step
// for Phase 1 (YAGNI — see docs/PHASE_1_SCOPE.md); if the API schema drifts
// this is the single place to update on the frontend.

export interface CompanyContext {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
  description: string | null;
  is_financial_industry: boolean;
}

export interface MarketContext {
  price: number | null;
  currency: string;
  market_cap: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  as_of: string | null;
}

export interface FinancialMetrics {
  as_of_period: string;
  revenue_growth_yoy: number | null;
  revenue_cagr_3y: number | null;
  ebitda_growth_yoy: number | null;
  ebitda_margin: number | null;
  net_income_growth_yoy: number | null;
  net_margin: number | null;
  roe: number | null;
  net_debt: number | null;
  net_debt_to_ebitda: number | null;
  debt_to_equity: number | null;
  equity_ratio: number | null;
  operating_cash_flow: number | null;
  ocf_margin: number | null;
  free_cash_flow: number | null;
  fcf_margin: number | null;
  fcf_conversion: number | null;
  growth_consistency: number | null;
  latest_revenue: number | null;
  latest_ebitda: number | null;
  latest_net_income: number | null;
  missing_fields: string[];
}

export interface FinancialHistoryPoint {
  fiscal_year: number;
  revenue: number | null;
  ebitda: number | null;
  net_income: number | null;
  free_cash_flow: number | null;
}

export interface ValuationMetrics {
  pe: number | null;
  pb: number | null;
  ev_ebitda: number | null;
  pe_historical_median: number | null;
  pb_historical_median: number | null;
  ev_ebitda_historical_median: number | null;
  pe_vs_history_ratio: number | null;
  pb_vs_history_ratio: number | null;
  ev_ebitda_vs_history_ratio: number | null;
  history_years_used: number;
  missing_fields: string[];
}

export interface ScoreComponent {
  metric: string;
  label: string;
  value: number | null;
  points: number;
  max_points: number;
  reason: string;
}

export interface CategoryScore {
  label: string;
  score: number;
  components: ScoreComponent[];
}

export interface ScoreResult {
  growth: CategoryScore;
  profitability: CategoryScore;
  balance_sheet: CategoryScore;
  cash_flow: CategoryScore;
  valuation: CategoryScore;
  overall: number;
  overall_weights: Record<string, number>;
  engine_version: string;
  unsupported_reason: string | null;
}

export interface MacroSeriesPoint {
  code: string;
  label: string;
  value: number;
  observation_date: string;
  is_mock: boolean;
}

export interface DisclosureContext {
  title: string;
  category: string;
  published_at: string;
  source_url: string;
}

export interface DataQuality {
  completeness: number;
  freshness: number;
  metric_coverage: number;
  overall: number;
  warnings: string[];
}

export interface SourceRef {
  field: string;
  source: string;
  source_url: string | null;
  fetched_at: string;
  published_at: string | null;
  is_mock: boolean;
}

export type Outlook = "POSITIVE" | "NEUTRAL_POSITIVE" | "NEUTRAL" | "NEUTRAL_NEGATIVE" | "NEGATIVE";

export interface HorizonOutlook {
  outlook: Outlook;
  confidence: number;
  drivers: string[];
  risks: string[];
  catalysts: string[];
}

export interface LLMAnalysis {
  executive_summary: string;
  short_term: HorizonOutlook;
  medium_term: HorizonOutlook;
  long_term: HorizonOutlook;
  bull_case: string[];
  bear_case: string[];
  key_risks: string[];
  key_catalysts: string[];
  thesis_breakers: string[];
  what_to_watch: string[];
  _meta: {
    llm_model: string;
    llm_is_mocked: boolean;
    prompt_version: string;
    hallucination_flags: string[];
  };
}

export interface CompanyAnalysisResponse {
  ticker: string;
  as_of: string;
  company: CompanyContext;
  market: MarketContext;
  metrics: FinancialMetrics;
  financial_history: FinancialHistoryPoint[];
  valuation: ValuationMetrics;
  scores: ScoreResult;
  macro: MacroSeriesPoint[];
  disclosures: DisclosureContext[];
  data_quality: DataQuality;
  sources: SourceRef[];
  analysis: LLMAnalysis;
  unsupported_reason: string | null;
  versions: Record<string, string>;
  stage_results: Record<string, string> | null;
}

export interface CompanySearchResult {
  ticker: string;
  name: string;
  sector: string | null;
  industry: string | null;
}
