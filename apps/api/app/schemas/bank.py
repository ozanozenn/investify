from __future__ import annotations

from pydantic import BaseModel


class BankMetrics(BaseModel):
    """`financial_engine/bank_engine.py` çıktısı (ADR-014). Oranlar kesir
    olarak (0.25 == %25). Girdisi eksik her alan None'dır — asla tahmin
    edilmez; eksik girdi `missing_fields`'te listelenir.

    `nim_proxy` gerçek net faiz marjı DEĞİLDİR: payda faiz getirili varlıklar
    yerine ortalama toplam aktiftir (yfinance faiz getirili varlık kalemi
    sunmaz), bu yüzden gerçek NIM'den sistematik olarak düşüktür.
    `cost_income_ratio` da yaklaşıktır: payda sağlayıcının "Total Revenue"
    kalemidir (faiz dışı gelir kalemi yfinance'te yok)."""

    as_of_period: str
    engine_version: str

    # Kârlılık
    roe: float | None = None
    roa: float | None = None
    nim_proxy: float | None = None
    cost_income_ratio: float | None = None

    # Büyüme
    nii_growth_yoy: float | None = None
    net_income_growth_yoy: float | None = None
    equity_growth_yoy: float | None = None

    # Bilanço ve risk
    equity_to_assets: float | None = None
    loan_to_deposit: float | None = None
    provision_to_nii: float | None = None

    # Son dönem tutarları (TL)
    latest_net_interest_income: float | None = None
    latest_net_income: float | None = None
    latest_total_assets: float | None = None
    latest_equity: float | None = None
    latest_loans: float | None = None
    latest_deposits: float | None = None

    missing_fields: list[str] = []
