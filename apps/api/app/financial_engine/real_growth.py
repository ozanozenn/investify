"""Reel (enflasyondan arındırılmış) büyüme (ADR-016, MAIN_ROADMAP.md §66).

Türkiye'de yüksek enflasyon nominal büyümeyi şişirir; %40 gelir artışı
%45 enflasyonda reel küçülmedir. Gelir ve net kâr yıllık büyümesi
`formulas.real_growth` ile arındırılır: (1 + nominal) / (1 + TÜFE) - 1.

Bilinen yaklaşıklık (dürüstçe belirtilir, gizlenmez): nominal büyüme son
mali yılın (ör. 2025 vs 2024) büyümesidir, TÜFE ise en son açıklanan
yıllık TÜFE'dir (ör. 2026 Ocak'ın yıllık değişimi). Doğru arındırıcı mali
yılın ortalama ya da yıl sonu (Aralık/Aralık) enflasyonudur; elimizde
yalnızca son gözlem olduğu için onu kullanıyoruz. TÜFE gözlemi mali yıl
sonundan `max_cpi_gap_months`'tan fazla uzaksa uyumsuzluk çok büyük
sayılır ve reel büyüme hesaplanmaz (`cpi_period_mismatch`).

Saf fonksiyon — I/O yapmaz. Mock TÜFE (EVDS anahtarı yokken kullanılan
etiketli yedek değer) ile asla reel büyüme üretilmez: `cpi_yoy_mock`.
"""

from __future__ import annotations

import datetime as dt

from app.financial_engine import formulas as f
from app.models.enums import CanonicalField as CF
from app.schemas.context import MacroSeriesPoint
from app.schemas.financial import PeriodData
from app.schemas.quality import RealGrowth


def _month_gap(a: dt.date, b: dt.date) -> int:
    return abs((a.year - b.year) * 12 + (a.month - b.month))


def compute_real_growth(
    annual_periods: list[PeriodData],
    cpi: MacroSeriesPoint | None,
    max_cpi_gap_months: int,
) -> RealGrowth:
    """`cpi` = `cpi_yoy` makro gözlemi; değeri yüzde puandır (42,0 = %42)."""
    if not annual_periods:
        return RealGrowth(missing_fields=["no_financial_periods"])

    periods = sorted(annual_periods, key=lambda p: p.fiscal_year)
    latest = periods[-1]
    previous = periods[-2] if len(periods) >= 2 else None
    missing: list[str] = []

    nominal: dict[CF, float | None] = {CF.REVENUE: None, CF.NET_INCOME: None}
    deflatable: set[CF] = set()
    if previous is None:
        missing.append("previous_period")
    else:
        for field in (CF.REVENUE, CF.NET_INCOME):
            cur, prev = latest.values.get(field.value), previous.values.get(field.value)
            # Nominal değer FinancialMetrics.*_growth_yoy ile aynı formül (|önceki| tabanlı).
            nominal[field] = f.growth_rate(cur, prev)
            if cur is None or prev is None:
                missing.append(field.value)
            elif prev <= 0:
                # Sıfır/negatif tabandan (ör. zarardan kâra) "büyüme" enflasyonla
                # bölünürse anlamsız olur — reel değer üretilmez.
                missing.append(f"non_positive_base:{field.value}")
            else:
                deflatable.add(field)

    cpi_ratio = None
    cpi_date = None
    cpi_usable = False
    if cpi is None:
        missing.append("cpi_yoy")
    elif cpi.is_mock:
        missing.append("cpi_yoy_mock")
    else:
        cpi_ratio = cpi.value / 100.0
        cpi_date = cpi.observation_date
        if _month_gap(cpi_date, latest.period_end_date) > max_cpi_gap_months:
            missing.append("cpi_period_mismatch")
        else:
            cpi_usable = True

    def _deflate(field: CF) -> float | None:
        if not cpi_usable or field not in deflatable:
            return None
        return f.real_growth(nominal[field], cpi_ratio)

    return RealGrowth(
        as_of_period=str(latest.fiscal_year),
        cpi_yoy=cpi_ratio,
        cpi_observation_date=cpi_date,
        revenue_growth_nominal=nominal[CF.REVENUE],
        revenue_growth_real=_deflate(CF.REVENUE),
        net_income_growth_nominal=nominal[CF.NET_INCOME],
        net_income_growth_real=_deflate(CF.NET_INCOME),
        missing_fields=missing,
    )
