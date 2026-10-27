"""Banka finansal motoru (ADR-014).

Bankada "hasılat", FAVÖK, net borç ve serbest nakit akışı kavramları anlamsız
olduğu için genel motor (`engine.py`) yerine bu motor çalışır. Saf fonksiyon:
I/O yapmaz, sağlayıcı/LLM import etmez. Girdi, yıllık `PeriodData` listesi.

Her oran girdileri yoksa None döner — asla tahmin edilmez; eksik girdiler
`missing_fields`'e yazılır. İki oran bilinçli olarak YAKLAŞIKTIR (etiketleri
ve `schemas/bank.py` açıklaması bunu söyler):
- `nim_proxy` = net faiz geliri / ortalama TOPLAM aktif (gerçek NIM'in
  paydası faiz getirili aktiflerdir; yfinance bu kalemi sunmaz).
- `cost_income_ratio` = faaliyet giderleri / sağlayıcının "Total Revenue"
  kalemi (faiz dışı gelir kalemi yfinance'te yok). Skora girmez.

Formül değişirse `BANK_ENGINE_VERSION` atlanır (ADR-005/012).
"""

from __future__ import annotations

from app.financial_engine import formulas as f
from app.models.enums import CanonicalField as CF
from app.schemas.bank import BankMetrics
from app.schemas.financial import PeriodData

BANK_ENGINE_VERSION = "bank-v1"

# Bunlar olmadan ROE/ROA/NIM ve özkaynak/aktif kurulamaz (veri kalitesi bunları sayar).
BANK_CORE_FIELDS: list[str] = [
    CF.NET_INCOME.value,
    CF.EQUITY.value,
    CF.TOTAL_ASSETS.value,
    CF.NET_INTEREST_INCOME.value,
]
# Varsa ek oranlar için kullanılır; yoksa ilgili oran None kalır.
BANK_OPTIONAL_FIELDS: list[str] = [
    CF.OPERATING_EXPENSE.value,
    CF.REVENUE.value,
    CF.CREDIT_LOSS_PROVISION.value,
    CF.LOANS.value,
    CF.DEPOSITS.value,
]

NO_PREVIOUS_PERIOD = "no_previous_period"
NII_DERIVED = "net_interest_income_derived_from_interest_income_minus_expense"
COST_INCOME_APPROXIMATION = "cost_income_ratio_uses_provider_total_revenue"


def _get(period: PeriodData | None, field: CF) -> float | None:
    if period is None:
        return None
    return period.values.get(field.value)


def net_interest_income(period: PeriodData | None) -> tuple[float | None, bool]:
    """(net faiz geliri, türetildi_mi). Açık kalem öncelikli; yoksa faiz
    gelirleri − |faiz giderleri| muhasebe özdeşliği. Sağlayıcıların gider
    işaret kuralı farklı olabildiği için gider mutlak değerle düşülür
    (`formulas.free_cash_flow`'daki CAPEX normalizasyonuyla aynı)."""
    explicit = _get(period, CF.NET_INTEREST_INCOME)
    if explicit is not None:
        return explicit, False
    income = _get(period, CF.INTEREST_INCOME)
    expense = _get(period, CF.INTEREST_EXPENSE)
    if income is None or expense is None:
        return None, False
    return income - abs(expense), True


def cost_income_ratio(operating_expense: float | None, total_revenue: float | None) -> float | None:
    """Faaliyet giderleri / toplam gelir. Gelir pozitif olmalı; gider
    işareti sağlayıcıya göre değiştiği için mutlak değer alınır."""
    if operating_expense is None or total_revenue is None or total_revenue <= 0:
        return None
    return abs(operating_expense) / total_revenue


def provision_to_nii(provision: float | None, nii: float | None) -> float | None:
    """Kredi karşılık gideri / net faiz geliri: faiz gelirinin ne kadarını
    karşılıklar yiyor. Negatif karşılık (iptal) olduğu gibi bırakılır.
    NFG ≤ 0 ise oran anlamsızdır → None."""
    if provision is None or nii is None or nii <= 0:
        return None
    return provision / nii


def compute_bank_metrics(annual_periods: list[PeriodData]) -> BankMetrics:
    """`annual_periods` herhangi bir sırada olabilir; en yeni yıl "güncel",
    bir önceki yıl büyüme ve ortalama bakiye için kullanılır."""
    if not annual_periods:
        return BankMetrics(
            as_of_period="N/A",
            engine_version=BANK_ENGINE_VERSION,
            missing_fields=["no_financial_periods"],
        )

    periods = sorted(annual_periods, key=lambda p: p.fiscal_year)
    latest = periods[-1]
    previous = periods[-2] if len(periods) >= 2 else None

    net_income = _get(latest, CF.NET_INCOME)
    equity = _get(latest, CF.EQUITY)
    total_assets = _get(latest, CF.TOTAL_ASSETS)
    nii, nii_derived = net_interest_income(latest)
    operating_expense = _get(latest, CF.OPERATING_EXPENSE)
    revenue = _get(latest, CF.REVENUE)
    provision = _get(latest, CF.CREDIT_LOSS_PROVISION)
    loans = _get(latest, CF.LOANS)
    deposits = _get(latest, CF.DEPOSITS)

    prev_net_income = _get(previous, CF.NET_INCOME)
    prev_equity = _get(previous, CF.EQUITY)
    prev_total_assets = _get(previous, CF.TOTAL_ASSETS)
    prev_nii, _ = net_interest_income(previous)

    avg_equity = f.average(equity, prev_equity)
    avg_assets = f.average(total_assets, prev_total_assets)
    cost_income = cost_income_ratio(operating_expense, revenue)

    missing: list[str] = []
    for field in BANK_CORE_FIELDS + BANK_OPTIONAL_FIELDS:
        if field == CF.NET_INTEREST_INCOME.value:
            if nii is None:
                missing.append(field)
        elif latest.values.get(field) is None:
            missing.append(field)
    if previous is None:
        missing.append(NO_PREVIOUS_PERIOD)
    if nii_derived:
        missing.append(NII_DERIVED)
    if cost_income is not None:
        missing.append(COST_INCOME_APPROXIMATION)

    return BankMetrics(
        as_of_period=str(latest.fiscal_year),
        engine_version=BANK_ENGINE_VERSION,
        roe=f.safe_div(net_income, avg_equity),
        roa=f.safe_div(net_income, avg_assets),
        nim_proxy=f.safe_div(nii, avg_assets),
        cost_income_ratio=cost_income,
        nii_growth_yoy=f.growth_rate(nii, prev_nii),
        net_income_growth_yoy=f.growth_rate(net_income, prev_net_income),
        equity_growth_yoy=f.growth_rate(equity, prev_equity),
        equity_to_assets=f.safe_div(equity, total_assets),
        loan_to_deposit=f.safe_div(loans, deposits) if deposits and deposits > 0 else None,
        provision_to_nii=provision_to_nii(provision, nii),
        latest_net_interest_income=nii,
        latest_net_income=net_income,
        latest_total_assets=total_assets,
        latest_equity=equity,
        latest_loans=loans,
        latest_deposits=deposits,
        missing_fields=missing,
    )
