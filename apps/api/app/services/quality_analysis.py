"""Kalite bayrakları + reel büyüme orkestrasyonu (ADR-016).

Refresh pipeline'ı bu tek fonksiyonu çağırır; eşikleri
`config/quality_flags.yaml`'dan okuyup saf motorlara (`financial_engine/
quality_flags.py`, `financial_engine/real_growth.py`) verir.
"""

from __future__ import annotations

from functools import lru_cache

import yaml

from app.core.config import CONFIG_DIR
from app.financial_engine.quality_flags import compute_quality_flags
from app.financial_engine.real_growth import compute_real_growth
from app.schemas.context import MacroSeriesPoint
from app.schemas.financial import PeriodData
from app.schemas.quality import QualityFlagsResult, RealGrowth

CPI_SERIES_CODE = "cpi_yoy"  # config/analysis.yaml macro.series


@lru_cache
def get_quality_flags_config() -> dict:
    with open(CONFIG_DIR / "quality_flags.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def compute_quality_analysis(
    annual_periods: list[PeriodData],
    macro: list[MacroSeriesPoint],
    unsupported_reason: str | None = None,
    not_applicable_reason: str | None = None,
) -> tuple[QualityFlagsResult, RealGrowth]:
    config = get_quality_flags_config()
    cpi = next((m for m in macro if m.code == CPI_SERIES_CODE), None)
    if not_applicable_reason and not unsupported_reason:
        # Analiz edilen ama genel kuralların uymadığı şirket türü (banka,
        # ADR-014): bayrak üretilmez, nedeni yazılır. Reel büyüme (net kârın
        # enflasyondan arındırılmış büyümesi) bankada da anlamlı, hesaplanır.
        return (
            QualityFlagsResult(
                engine_version=str(config.get("version", "v1")),
                missing_fields=["not_applicable_bank"],
                not_applicable_reason=not_applicable_reason,
            ),
            compute_real_growth(annual_periods, cpi, int(config["real_growth"]["max_cpi_gap_months"])),
        )
    if unsupported_reason:
        # Banka/GYO gibi sektörlerde FAVÖK/marj/hasılat bu anlamda yok;
        # genel kurallar yanıltıcı bayrak üretir (bkz. industry_strategy).
        return (
            QualityFlagsResult(engine_version=str(config.get("version", "v1")), missing_fields=["unsupported_industry"]),
            RealGrowth(missing_fields=["unsupported_industry"]),
        )
    return (
        compute_quality_flags(annual_periods, config),
        compute_real_growth(annual_periods, cpi, int(config["real_growth"]["max_cpi_gap_months"])),
    )
