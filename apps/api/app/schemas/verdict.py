"""Hüküm kartı çıktısı (ADR-011). Tamamen deterministik — LLM üretmez."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

PriceLabel = Literal["UCUZ", "MAKUL", "PAHALI"]
QualityLabel = Literal["GUCLU", "ORTA", "ZAYIF"]
ConfidenceLabel = Literal["YUKSEK", "ORTA", "DUSUK"]
SignalLabel = Literal["AL", "TUT", "SAT"]


class VerdictLens(BaseModel):
    """Tek bir değerleme bakış açısının kararı ve gerekçesi."""

    key: Literal["history", "peers", "dcf"]
    label: str
    verdict: PriceLabel | None
    value: float | None
    reason: str


class Verdict(BaseModel):
    price: PriceLabel | None
    quality: QualityLabel | None
    confidence: ConfidenceLabel
    signal: SignalLabel | None = None
    signal_is_demo: bool = True
    headline: str
    lenses: list[VerdictLens]
    agreement: float | None
    overall_score: float | None
    engine_version: str
    missing_fields: list[str] = []
    unsupported_reason: str | None = None
