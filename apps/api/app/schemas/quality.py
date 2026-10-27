"""Kalite bayrakları ve reel büyüme çıktıları (ADR-016).

İkisi de `financial_engine` içindeki saf fonksiyonların çıktısıdır;
`StructuredAnalysisContext` üzerinde opsiyonel alan olarak taşınır ki
ADR-016'dan önceki snapshot'lar hâlâ okunabilsin (ADR-005).
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel

QualitySeverity = Literal["UYARI", "DIKKAT", "OLUMLU"]
# Değerin nasıl biçimleneceği: "ratio" 0-1 ölçekli oran (büyüme, marj),
# "currency" mutlak TL tutarı. Biçimlendirme arayüzde / LLM context'inde yapılır.
QualityValueUnit = Literal["ratio", "currency"]


class QualityFlagValue(BaseModel):
    """Bayrağın dayandığı tek bir ham sayı (yuvarlanmamış float)."""

    key: str
    label: str
    value: float
    unit: QualityValueUnit


class QualityFlag(BaseModel):
    """Tetiklenmiş bir kalite bayrağı. `title`/`detail` sade Türkçe; içinde
    rakam yoktur — rakamlar `values`'ta ham olarak durur."""

    key: str
    severity: QualitySeverity
    title: str
    detail: str
    values: list[QualityFlagValue] = []


class UnevaluatedQualityCheck(BaseModel):
    """Girdisi eksik olduğu için çalıştırılamayan kontrol — tahmin edilmez."""

    key: str
    name: str
    reason: str
    missing_fields: list[str]


class QualityFlagsResult(BaseModel):
    as_of_period: str | None = None
    engine_version: str = "v1"
    flags: list[QualityFlag] = []
    # Çalıştırılıp bulgu çıkmayan kontrollerin adları (şeffaflık için).
    passed_checks: list[str] = []
    not_evaluated: list[UnevaluatedQualityCheck] = []
    missing_fields: list[str] = []
    # Kurallar bu şirket türüne uymuyorsa (ör. banka) neden; eski snapshot'larda yok.
    not_applicable_reason: str | None = None


class RealGrowth(BaseModel):
    """Nominal büyümenin TÜFE ile arındırılmış hali: (1+nominal)/(1+TÜFE)-1.

    Yaklaşıktır: mali yıl büyümesi, mali yılın kendi enflasyonuyla değil en
    son açıklanan yıllık TÜFE ile arındırılır (bkz. ADR-016). `cpi_yoy`
    0-1 ölçeğindedir (0,335 = %33,5)."""

    as_of_period: str | None = None
    cpi_yoy: float | None = None
    cpi_observation_date: dt.date | None = None
    revenue_growth_nominal: float | None = None
    revenue_growth_real: float | None = None
    net_income_growth_nominal: float | None = None
    net_income_growth_real: float | None = None
    missing_fields: list[str] = []
