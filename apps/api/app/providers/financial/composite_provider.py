"""Primary + fallback financial statements provider with optional
cross-check (ADR-015).

- Primary fails (ProviderUnavailableError or any error) or returns nothing
  -> the fallback's periods are used, and that is recorded on the result.
- With `cross_check=True` both sources are queried (concurrently). The
  primary's values are always the ones used; wherever both report the same
  canonical field for the same fiscal period and the values differ by more
  than `tolerance` (relative), a `FieldDiscrepancy` is recorded instead of
  silently picking one. `services/financial_sources.py` turns these into
  Turkish data-quality warnings.

The side information travels on the returned list itself
(`FinancialStatements`, a `list` subclass), so the provider stays stateless
and safe to share across concurrent refreshes, and callers that only expect
`list[RawFinancialPeriod]` keep working unchanged.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.core.logging import get_logger
from app.providers.base import FinancialDataProvider, ProviderUnavailableError, RawFinancialPeriod

logger = get_logger(__name__)


@dataclass(frozen=True)
class FieldDiscrepancy:
    period_type: str
    fiscal_year: int
    fiscal_quarter: int | None
    field: str
    primary_source: str
    primary_value: float
    secondary_source: str
    secondary_value: float
    relative_difference: float


class FinancialStatements(list):
    """`list[RawFinancialPeriod]` plus provenance from the composite provider."""

    def __init__(
        self,
        periods: Iterable[RawFinancialPeriod] = (),
        *,
        primary_source: str | None = None,
        secondary_source: str | None = None,
        used_source: str | None = None,
        fallback_used: bool = False,
        cross_check_skipped: bool = False,
        discrepancies: Sequence[FieldDiscrepancy] = (),
    ) -> None:
        super().__init__(periods)
        self.primary_source = primary_source
        self.secondary_source = secondary_source
        self.used_source = used_source
        self.fallback_used = fallback_used
        # Cross-check was requested but the secondary source returned nothing.
        self.cross_check_skipped = cross_check_skipped
        self.discrepancies: list[FieldDiscrepancy] = list(discrepancies)


def relative_difference(a: float, b: float) -> float:
    """|a - b| / max(|a|, |b|); 0 when both are 0. Symmetric, bounded by 2."""
    scale = max(abs(a), abs(b))
    return 0.0 if scale == 0 else abs(a - b) / scale


def compare_periods(
    primary: Sequence[RawFinancialPeriod],
    secondary: Sequence[RawFinancialPeriod],
    fields: Iterable[str],
    period_types: Iterable[str],
    tolerance: float,
) -> list[FieldDiscrepancy]:
    """Discrepancies for every (period, field) both sources report, newest
    period first, fields in the given order."""
    fields = list(fields)
    period_types = set(period_types)
    by_key = {(p.period_type, p.fiscal_year, p.fiscal_quarter): p for p in secondary}
    ordered = sorted(
        (p for p in primary if p.period_type in period_types),
        key=lambda p: (p.fiscal_year, p.period_type == "ANNUAL", p.fiscal_quarter or 0),
        reverse=True,
    )
    out: list[FieldDiscrepancy] = []
    for p in ordered:
        other = by_key.get((p.period_type, p.fiscal_year, p.fiscal_quarter))
        if other is None:
            continue
        for field in fields:
            a, b = p.values.get(field), other.values.get(field)
            if a is None or b is None:
                continue
            diff = relative_difference(a, b)
            if diff > tolerance:
                out.append(
                    FieldDiscrepancy(
                        period_type=p.period_type,
                        fiscal_year=p.fiscal_year,
                        fiscal_quarter=p.fiscal_quarter,
                        field=field,
                        primary_source=p.source_code,
                        primary_value=a,
                        secondary_source=other.source_code,
                        secondary_value=b,
                        relative_difference=diff,
                    )
                )
    return out


class CompositeFinancialDataProvider(FinancialDataProvider):
    def __init__(
        self,
        primary: FinancialDataProvider,
        fallback: FinancialDataProvider,
        *,
        cross_check: bool = False,
        tolerance: float = 0.05,
        cross_check_fields: Iterable[str] = (),
        cross_check_period_types: Iterable[str] = ("ANNUAL",),
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.cross_check = cross_check
        self.tolerance = tolerance
        self.cross_check_fields = list(cross_check_fields)
        self.cross_check_period_types = list(cross_check_period_types)
        self.code = f"{primary.code}+{fallback.code}"

    async def _fetch(
        self, provider: FinancialDataProvider, ticker: str, annual_years: int, quarterly_quarters: int
    ) -> tuple[list[RawFinancialPeriod], str | None]:
        try:
            periods = await provider.get_financial_statements(
                ticker, annual_years=annual_years, quarterly_quarters=quarterly_quarters
            )
        except Exception as exc:  # one source failing must never sink the other
            logger.warning(
                "financial_source_failed",
                extra={"ticker": ticker, "provider": provider.code, "error": str(exc)},
            )
            return [], str(exc)
        if not periods:
            return [], "empty result"
        return list(periods), None

    async def get_financial_statements(
        self, ticker: str, annual_years: int = 5, quarterly_quarters: int = 8
    ) -> list[RawFinancialPeriod]:
        args = (ticker, annual_years, quarterly_quarters)
        if self.cross_check:
            (primary, primary_error), (secondary, secondary_error) = await asyncio.gather(
                self._fetch(self.primary, *args), self._fetch(self.fallback, *args)
            )
        else:
            primary, primary_error = await self._fetch(self.primary, *args)
            secondary, secondary_error = None, None

        provenance = {"primary_source": self.primary.code, "secondary_source": self.fallback.code}

        if primary:
            discrepancies: list[FieldDiscrepancy] = []
            if self.cross_check and secondary:
                discrepancies = compare_periods(
                    primary, secondary, self.cross_check_fields, self.cross_check_period_types, self.tolerance
                )
                for d in discrepancies:
                    logger.warning(
                        "financial_cross_check_discrepancy",
                        extra={
                            "ticker": ticker,
                            "period": f"{d.period_type}:{d.fiscal_year}:{d.fiscal_quarter or ''}",
                            "field": d.field,
                            "primary_source": d.primary_source,
                            "primary_value": d.primary_value,
                            "secondary_source": d.secondary_source,
                            "secondary_value": d.secondary_value,
                            "relative_difference": round(d.relative_difference, 4),
                        },
                    )
            return FinancialStatements(
                primary,
                **provenance,
                used_source=self.primary.code,
                cross_check_skipped=self.cross_check and not secondary,
                discrepancies=discrepancies,
            )

        if secondary is None:
            secondary, secondary_error = await self._fetch(self.fallback, *args)
        if secondary:
            logger.warning(
                "financial_fallback_used",
                extra={"ticker": ticker, "primary": self.primary.code, "error": primary_error},
            )
            return FinancialStatements(
                secondary, **provenance, used_source=self.fallback.code, fallback_used=True
            )

        raise ProviderUnavailableError(
            self.code,
            f"{ticker}: primary {self.primary.code} failed ({primary_error}); "
            f"fallback {self.fallback.code} failed ({secondary_error})",
        )
