"""Converts `StructuredAnalysisContext` into the human-readable dict that
actually gets embedded in the LLM prompt (roadmap section 40, ADR-003).

Every numeric leaf in the raw context is a plain unrounded float — great
for the frontend, which formats numbers itself, but if handed to the LLM
as-is it comes back verbatim in prose (e.g. "0.8259859533087344"), because
the prompt deliberately forbids the LLM from reformatting numbers itself
(that would make them unverifiable). So the formatting has to happen here,
once, before the LLM ever sees the value — not left to the LLM's judgment.

This module only decides *display* formatting; `hallucination_guard.py`
still verifies against the original raw floats (see `number_format.py`'s
parser, which knows how to undo every style produced here).
"""

from __future__ import annotations

import datetime as dt
import json

from app.llm.bank_context_formatter import format_bank_metrics
from app.llm.number_format import (
    format_currency,
    format_multiple,
    format_percent_points,
    format_plain,
    format_price,
    format_ratio_percent,
    format_score,
)
from app.llm.verdict_formatter import format_verdict_for_prompt
from app.schemas.context import (
    CompanyContext,
    DataQuality,
    DisclosureContext,
    MacroSeriesPoint,
    MarketContext,
    SourceRef,
    StructuredAnalysisContext,
)
from app.schemas.dcf import DcfAssumptions, DcfResult, DcfScenarioResult, SensitivityCell
from app.schemas.financial import FinancialHistoryPoint, FinancialMetrics
from app.schemas.quality import QualityFlagsResult, QualityFlagValue, RealGrowth
from app.schemas.scoring import CategoryScore, ScoreComponent, ScoreResult
from app.schemas.valuation import ValuationMetrics

_TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]

_RATIO_PERCENT_FIELDS = {
    "revenue_growth_yoy", "revenue_cagr_3y", "ebitda_growth_yoy", "ebitda_margin",
    "net_income_growth_yoy", "net_margin", "roe", "equity_ratio",
    "ocf_margin", "fcf_margin", "fcf_conversion", "growth_consistency",
}
_MULTIPLE_FIELDS = {"net_debt_to_ebitda", "debt_to_equity"}
_CURRENCY_FIELDS = {
    "net_debt", "operating_cash_flow", "free_cash_flow",
    "latest_revenue", "latest_ebitda", "latest_net_income",
}


def _date_tr(d: dt.date) -> str:
    return f"{d.day} {_TR_MONTHS[d.month - 1]} {d.year}"


def _fmt_financial_metrics(fm: FinancialMetrics) -> dict:
    out: dict = {"as_of_period": fm.as_of_period, "missing_fields": fm.missing_fields}
    for field in _RATIO_PERCENT_FIELDS:
        value = getattr(fm, field)
        out[field] = format_ratio_percent(value) if value is not None else None
    for field in _MULTIPLE_FIELDS:
        value = getattr(fm, field)
        out[field] = format_multiple(value) if value is not None else None
    for field in _CURRENCY_FIELDS:
        value = getattr(fm, field)
        out[field] = format_currency(value) if value is not None else None
    return out


def _fmt_financial_history(points: list[FinancialHistoryPoint]) -> list[dict]:
    return [
        {
            "fiscal_year": p.fiscal_year,
            "revenue": format_currency(p.revenue) if p.revenue is not None else None,
            "ebitda": format_currency(p.ebitda) if p.ebitda is not None else None,
            "net_income": format_currency(p.net_income) if p.net_income is not None else None,
            "free_cash_flow": format_currency(p.free_cash_flow) if p.free_cash_flow is not None else None,
        }
        for p in points
    ]


def _fmt_dcf_assumptions(a: DcfAssumptions) -> dict:
    percent_fields = (
        "revenue_growth_rate", "ebit_margin", "tax_rate", "da_percent_of_revenue",
        "capex_percent_of_revenue", "working_capital_change_percent_of_revenue",
        "wacc", "terminal_growth_rate",
    )
    out: dict = {"overridden_fields": a.overridden_fields}
    for field in percent_fields:
        value = getattr(a, field)
        out[field] = format_ratio_percent(value) if value is not None else None
    out["net_debt"] = format_currency(a.net_debt) if a.net_debt is not None else None
    out["shares_outstanding"] = format_plain(a.shares_outstanding, 0) if a.shares_outstanding is not None else None
    return out


def _fmt_dcf_scenario(s: DcfScenarioResult) -> dict:
    return {
        "scenario": s.scenario,
        "assumptions": _fmt_dcf_assumptions(s.assumptions),
        "projected_fcf": [format_currency(v) for v in s.projected_fcf],
        "terminal_value": format_currency(s.terminal_value) if s.terminal_value is not None else None,
        "enterprise_value": format_currency(s.enterprise_value) if s.enterprise_value is not None else None,
        "equity_value": format_currency(s.equity_value) if s.equity_value is not None else None,
        "intrinsic_value_per_share": (
            format_price(s.intrinsic_value_per_share) if s.intrinsic_value_per_share is not None else None
        ),
        "upside_vs_current_price": (
            format_ratio_percent(s.upside_vs_current_price) if s.upside_vs_current_price is not None else None
        ),
        "missing_fields": s.missing_fields,
    }


def _fmt_dcf(d: DcfResult | None) -> dict | None:
    if d is None:
        return None
    return {
        "bear": _fmt_dcf_scenario(d.bear),
        "base": _fmt_dcf_scenario(d.base),
        "bull": _fmt_dcf_scenario(d.bull),
        "sensitivity_matrix": [_fmt_sensitivity_cell(c) for c in d.sensitivity_matrix],
        "missing_fields": d.missing_fields,
    }


def _fmt_sensitivity_cell(c: SensitivityCell) -> dict:
    return {
        "wacc": format_ratio_percent(c.wacc),
        "terminal_growth": format_ratio_percent(c.terminal_growth),
        "intrinsic_value_per_share": (
            format_price(c.intrinsic_value_per_share) if c.intrinsic_value_per_share is not None else None
        ),
    }


def _fmt_valuation(v: ValuationMetrics) -> dict:
    multiple_fields = (
        "pe", "pb", "ev_ebitda",
        "pe_historical_median", "pb_historical_median", "ev_ebitda_historical_median",
        "pe_vs_history_ratio", "pb_vs_history_ratio", "ev_ebitda_vs_history_ratio",
    )
    out: dict = {"history_years_used": v.history_years_used, "missing_fields": v.missing_fields}
    for field in multiple_fields:
        value = getattr(v, field)
        out[field] = format_multiple(value) if value is not None else None
    out["dcf"] = _fmt_dcf(v.dcf)
    return out


def _fmt_score_component(c: ScoreComponent) -> dict:
    return {
        "metric": c.metric,
        "label": c.label,
        "value": format_plain(c.value, 2) if c.value is not None else None,
        "points": format_plain(c.points, 1),
        "max_points": format_plain(c.max_points, 1),
        "reason": c.reason,
    }


def _fmt_category_score(c: CategoryScore) -> dict:
    return {
        "label": c.label,
        "score": format_score(c.score),
        "components": [_fmt_score_component(x) for x in c.components],
    }


def _fmt_scores(s: ScoreResult) -> dict:
    return {
        "growth": _fmt_category_score(s.growth),
        "profitability": _fmt_category_score(s.profitability),
        "balance_sheet": _fmt_category_score(s.balance_sheet),
        "cash_flow": _fmt_category_score(s.cash_flow),
        "valuation": _fmt_category_score(s.valuation),
        "overall": format_score(s.overall),
        "overall_weights": {k: format_ratio_percent(w) for k, w in s.overall_weights.items()},
        "engine_version": s.engine_version,
        "unsupported_reason": s.unsupported_reason,
    }


_MACRO_PERCENT_POINT_CODES = {"policy_rate", "cpi_yoy"}


def _fmt_macro(points: list[MacroSeriesPoint]) -> list[dict]:
    out = []
    for p in points:
        if p.code in _MACRO_PERCENT_POINT_CODES:
            value_str = format_percent_points(p.value)
        else:
            value_str = format_price(p.value)  # FX rate, e.g. "41,23 TL"
        out.append(
            {
                "code": p.code,
                "label": p.label,
                "value": value_str,
                "observation_date": p.observation_date.isoformat(),
                "is_mock": p.is_mock,
            }
        )
    return out


def _fmt_market(m: MarketContext) -> dict:
    return {
        "price": format_price(m.price) if m.price is not None else None,
        "currency": m.currency,
        "market_cap": format_currency(m.market_cap, m.currency) if m.market_cap is not None else None,
        "fifty_two_week_high": format_price(m.fifty_two_week_high) if m.fifty_two_week_high is not None else None,
        "fifty_two_week_low": format_price(m.fifty_two_week_low) if m.fifty_two_week_low is not None else None,
        "as_of": m.as_of.isoformat() if m.as_of else None,
    }


def _fmt_company(c: CompanyContext) -> dict:
    return c.model_dump(mode="json")


def _fmt_disclosures(items: list[DisclosureContext]) -> list[dict]:
    return [d.model_dump(mode="json") for d in items]


def _fmt_data_quality(dq: DataQuality) -> dict:
    return {
        "completeness": format_ratio_percent(dq.completeness),
        "freshness": format_ratio_percent(dq.freshness),
        "metric_coverage": format_ratio_percent(dq.metric_coverage),
        "overall": format_ratio_percent(dq.overall),
        "warnings": dq.warnings,
    }


def _fmt_sources(items: list[SourceRef]) -> list[dict]:
    return [s.model_dump(mode="json") for s in items]


def _fmt_quality_value(v: QualityFlagValue) -> str:
    return format_currency(v.value) if v.unit == "currency" else format_ratio_percent(v.value)


def _fmt_quality_flags(q: QualityFlagsResult | None) -> dict | None:
    """Kalite bayrakları (ADR-016). Eski snapshot'larda None."""
    if q is None:
        return None
    return {
        "as_of_period": q.as_of_period,
        "flags": [
            {
                "key": fl.key,
                "severity": fl.severity,
                "title": fl.title,
                "detail": fl.detail,
                "values": {v.label: _fmt_quality_value(v) for v in fl.values},
            }
            for fl in q.flags
        ],
        "passed_checks": q.passed_checks,
        "not_evaluated": [{"name": c.name, "reason": c.reason} for c in q.not_evaluated],
        "missing_fields": q.missing_fields,
    }


_REAL_GROWTH_NOTE = (
    "Reel büyüme = (1 + nominal büyüme) / (1 + yıllık TÜFE) - 1. Yaklaşık bir değerdir: son mali yılın "
    "büyümesi, o yılın kendi enflasyonuyla değil en son açıklanan yıllık TÜFE ile arındırılmıştır."
)


def _fmt_real_growth(r: RealGrowth | None) -> dict | None:
    """Enflasyondan arındırılmış büyüme (ADR-016). Eski snapshot'larda None."""
    if r is None:
        return None

    def pct(value: float | None) -> str | None:
        return format_ratio_percent(value) if value is not None else None

    obs = r.cpi_observation_date
    return {
        "as_of_period": r.as_of_period,
        "cpi_yoy": pct(r.cpi_yoy),
        # Aylık seri: gün bilgisi anlamsız, "Ocak 2026" yeterli.
        "cpi_observation_month": f"{_TR_MONTHS[obs.month - 1]} {obs.year}" if obs else None,
        "revenue_growth_nominal": pct(r.revenue_growth_nominal),
        "revenue_growth_real": pct(r.revenue_growth_real),
        "net_income_growth_nominal": pct(r.net_income_growth_nominal),
        "net_income_growth_real": pct(r.net_income_growth_real),
        "note": _REAL_GROWTH_NOTE,
        "missing_fields": r.missing_fields,
    }


def format_context_for_prompt(context: StructuredAnalysisContext) -> dict:
    return {
        "ticker": context.ticker,
        "as_of": context.as_of.isoformat(),
        "company": _fmt_company(context.company),
        "market": _fmt_market(context.market),
        "metrics": _fmt_financial_metrics(context.metrics),
        "financial_history": _fmt_financial_history(context.financial_history),
        "valuation": _fmt_valuation(context.valuation),
        "scores": _fmt_scores(context.scores),
        "macro": _fmt_macro(context.macro),
        "disclosures": _fmt_disclosures(context.disclosures),
        "data_quality": _fmt_data_quality(context.data_quality),
        "sources": _fmt_sources(context.sources),
        "unsupported_reason": context.unsupported_reason,
        "next_rate_decision_date": (
            _date_tr(context.next_rate_decision_date) if context.next_rate_decision_date else None
        ),
        "quality_flags": _fmt_quality_flags(context.quality_flags),
        "real_growth": _fmt_real_growth(context.real_growth),
        # company-analysis-v4: LLM deterministik hükmü açıklar (ADR-011).
        "verdict": format_verdict_for_prompt(context.verdict),
        # Yalnızca bankalarda (ADR-014); diğer şirketlerin prompt'u değişmez.
        **({"bank_metrics": format_bank_metrics(context.bank_metrics)} if context.bank_metrics else {}),
    }


def render_context_json(context: StructuredAnalysisContext) -> str:
    """What actually gets embedded in the prompt in place of `{context_json}`."""
    return json.dumps(format_context_for_prompt(context), ensure_ascii=False, indent=2)
