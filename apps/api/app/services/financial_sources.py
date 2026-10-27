"""Financial statement source selection and its data-quality warnings
(ADR-015).

`build_financial_provider` turns the `FINANCIAL_PROVIDER_*` /
`FINANCIAL_CROSS_CHECK` settings into a provider. With the defaults it
returns the plain yfinance provider — exactly the pre-ADR-015 behaviour.

`financial_source_warnings` reads the provenance a
`CompositeFinancialDataProvider` attaches to its result and produces
Turkish data-quality warnings (fallback used, cross-check skipped, values
that disagree between sources). Warnings are deliberately qualitative — the
exact numbers are logged by the composite provider and shown by
`scripts/verify_isyatirim.py` — so the LLM never sees a figure in a warning
that the hallucination guard cannot trace back to a numeric context field.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.config import Settings, get_financial_sources_config
from app.core.logging import get_logger
from app.providers.base import FinancialDataProvider, RawFinancialPeriod
from app.providers.financial.composite_provider import CompositeFinancialDataProvider, FieldDiscrepancy
from app.providers.financial.isyatirim_provider import IsYatirimFinancialDataProvider
from app.providers.financial.yfinance_provider import YFinanceFinancialDataProvider

logger = get_logger(__name__)

_PROVIDER_FACTORIES = {
    "yfinance": YFinanceFinancialDataProvider,
    "isyatirim": IsYatirimFinancialDataProvider,
}

SOURCE_LABELS: dict[str, str] = {
    "yfinance": "Yahoo Finance",
    "isyatirim": "İş Yatırım",
}

FIELD_LABELS: dict[str, str] = {
    "REVENUE": "Hasılat",
    "GROSS_PROFIT": "Brüt kâr",
    "EBITDA": "FAVÖK",
    "EBIT": "Esas faaliyet kârı",
    "NET_INCOME": "Net kâr",
    "CASH": "Nakit",
    "TOTAL_ASSETS": "Toplam varlıklar",
    "TOTAL_DEBT": "Finansal borç",
    "EQUITY": "Özkaynaklar",
    "OPERATING_CASH_FLOW": "İşletme nakit akışı",
    "CAPEX": "Yatırım harcaması",
    "FREE_CASH_FLOW": "Serbest nakit akışı",
}


def _source_label(code: str | None) -> str:
    return SOURCE_LABELS.get(code or "", code or "bilinmeyen kaynak")


def build_financial_provider(settings: Settings, cross_check_config: dict | None = None) -> FinancialDataProvider:
    primary = _PROVIDER_FACTORIES[settings.financial_provider_primary]()
    fallback_code = settings.financial_provider_fallback
    if fallback_code == "none" or fallback_code == settings.financial_provider_primary:
        if settings.financial_cross_check:
            logger.warning(
                "financial_cross_check_ignored",
                extra={"reason": "FINANCIAL_PROVIDER_FALLBACK must name a second source"},
            )
        return primary
    cfg = (cross_check_config or get_financial_sources_config())["cross_check"]
    return CompositeFinancialDataProvider(
        primary,
        _PROVIDER_FACTORIES[fallback_code](),
        cross_check=settings.financial_cross_check,
        tolerance=float(cfg["relative_tolerance"]),
        cross_check_fields=cfg["fields"],
        cross_check_period_types=cfg["period_types"],
    )


def _period_label(d: FieldDiscrepancy) -> str:
    if d.period_type == "ANNUAL":
        return f"{d.fiscal_year} yıllık"
    return f"{d.fiscal_year} {d.fiscal_quarter}. çeyrek"


def financial_source_warnings(
    raw_periods: Sequence[RawFinancialPeriod], max_warnings: int | None = None
) -> list[str]:
    """Turkish data-quality warnings for a financial-statements result.
    Plain lists (single-provider mode, failed stage) produce none."""
    if max_warnings is None:
        max_warnings = int(get_financial_sources_config()["cross_check"]["max_warnings"])
    warnings: list[str] = []
    primary = _source_label(getattr(raw_periods, "primary_source", None))
    secondary = _source_label(getattr(raw_periods, "secondary_source", None))

    if getattr(raw_periods, "fallback_used", False):
        warnings.append(
            f"Birincil finansal tablo kaynağı ({primary}) veri vermedi; "
            f"yedek kaynak ({secondary}) kullanıldı."
        )
    if getattr(raw_periods, "cross_check_skipped", False):
        warnings.append(f"Finansal tablo çapraz kontrolü yapılamadı: {secondary} veri vermedi.")

    by_period: dict[str, list[str]] = {}
    for d in getattr(raw_periods, "discrepancies", ()):
        by_period.setdefault(_period_label(d), []).append(FIELD_LABELS.get(d.field, d.field))
    for label, fields in list(by_period.items())[:max_warnings]:
        warnings.append(
            f"Finansal tablo çapraz kontrolü ({label}): {', '.join(fields)} için {primary} ile "
            f"{secondary} değerleri tolerans dışında farklı; {primary} değerleri kullanıldı."
        )
    remaining = len(by_period) - max_warnings
    if remaining > 0:
        warnings.append(f"Finansal tablo çapraz kontrolü: {remaining} dönemde daha kaynaklar arası fark var.")
    return warnings
