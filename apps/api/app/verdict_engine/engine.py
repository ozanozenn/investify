"""Hüküm motoru (ADR-011): "Bu hisse ucuz mu pahalı mı, şirket iyi mi?"

Saf fonksiyon — I/O yapmaz, LLM'e dokunmaz. Girdi olarak zaten hesaplanmış
değerleme, skor ve veri kalitesi çıktısını alır; eşikler `config/verdict.yaml`.

Üç değerleme bakış açısı ayrı ayrı oy verir (tarihsel çarpanlar, sektör
medyanı, DCF baz senaryo). Veri yoksa o bakış açısı oy vermez — asla
tahmin edilmez, `missing_fields`'e yazılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.scoring import ScoreResult
from app.schemas.valuation import ValuationMetrics
from app.schemas.verdict import Verdict, VerdictLens

_PRICE_TR = {"UCUZ": "ucuz", "MAKUL": "makul", "PAHALI": "pahalı"}
_QUALITY_TR = {"GUCLU": "Güçlü", "ORTA": "Orta kalitede", "ZAYIF": "Zayıf"}

# DEMO sinyal matrisi: (fiyat, kalite) -> sinyal. Ucuz ama zayıf şirket
# "değer tuzağı" olabileceği için AL değil TUT.
_SIGNAL_MATRIX = {
    ("UCUZ", "GUCLU"): "AL",
    ("UCUZ", "ORTA"): "AL",
    ("UCUZ", "ZAYIF"): "TUT",
    ("MAKUL", "GUCLU"): "TUT",
    ("MAKUL", "ORTA"): "TUT",
    ("MAKUL", "ZAYIF"): "SAT",
    ("PAHALI", "GUCLU"): "TUT",
    ("PAHALI", "ORTA"): "SAT",
    ("PAHALI", "ZAYIF"): "SAT",
}


@dataclass(frozen=True)
class PeerMedians:
    """Sektör/endüstri medyanları; `services/peer_comparison.py` üretir."""

    peer_count: int
    median_pe: float | None = None
    median_ev_ebitda: float | None = None
    median_pb: float | None = None
    # Her çarpanın medyanına kaç şirket katkı verdi (zarar edenin F/K'sı yok).
    pe_count: int = 0
    ev_ebitda_count: int = 0
    pb_count: int = 0


def _pct(value: float) -> str:
    return f"%{abs(value) * 100:.0f}".replace(".", ",")


def _vs(diff: float, of: str, with_: str) -> str:
    """"medyanının %12 üstünde" / "medyanıyla aynı seviyede" — %0 yazmaz.
    `of`: tamlayan hali (medyanının), `with_`: birliktelik hali (medyanıyla)."""
    if round(abs(diff) * 100) == 0:
        return f"{with_} aynı seviyede"
    return f"{of} {_pct(diff)} {'üstünde' if diff > 0 else 'altında'}"


def _ratio_verdict(ratio: float, cheap_below: float, expensive_above: float) -> str:
    if ratio < cheap_below:
        return "UCUZ"
    if ratio > expensive_above:
        return "PAHALI"
    return "MAKUL"


def _mean_positive(values: list[float | None]) -> float | None:
    # Negatif/sıfır çarpan (zarar eden şirketin F/K'sı) anlamsız — dışarıda bırak.
    present = [v for v in values if v is not None and v > 0]
    return sum(present) / len(present) if present else None


def _history_lens(valuation: ValuationMetrics, cfg: dict) -> VerdictLens:
    ratio = _mean_positive(
        [valuation.pe_vs_history_ratio, valuation.ev_ebitda_vs_history_ratio, valuation.pb_vs_history_ratio]
    )
    label = "Kendi geçmişine göre"
    if ratio is None:
        return VerdictLens(key="history", label=label, verdict=None, value=None,
                           reason="Tarihsel çarpan verisi yok.")
    verdict = _ratio_verdict(ratio, cfg["cheap_below"], cfg["expensive_above"])
    years = valuation.history_years_used
    reason = f"Çarpanları {_vs(ratio - 1, f'son {years} yıllık medyanının', f'son {years} yıllık medyanıyla')}."
    return VerdictLens(key="history", label=label, verdict=verdict, value=ratio, reason=reason)


def _peers_lens(valuation: ValuationMetrics, peers: PeerMedians | None, cfg: dict) -> VerdictLens:
    label = "Sektörüne göre"
    if peers is None or peers.peer_count < cfg["min_peer_count"]:
        count = 0 if peers is None else peers.peer_count
        return VerdictLens(key="peers", label=label, verdict=None, value=None,
                           reason=f"Karşılaştırılacak yeterli benzer şirket yok ({count}).")
    ratios: list[float | None] = []
    used_counts: list[int] = []
    for own, median, count in (
        (valuation.pe, peers.median_pe, peers.pe_count),
        (valuation.ev_ebitda, peers.median_ev_ebitda, peers.ev_ebitda_count),
        (valuation.pb, peers.median_pb, peers.pb_count),
    ):
        # Her çarpan kendi başına yeterli sayıda şirketle karşılaştırılmalı.
        if own is not None and median is not None and own > 0 and median > 0 and count >= cfg["min_peer_count"]:
            ratios.append(own / median)
            used_counts.append(count)
    ratio = _mean_positive(ratios)
    if ratio is None:
        return VerdictLens(key="peers", label=label, verdict=None, value=None,
                           reason="Benzer şirketlerle karşılaştırılabilir çarpan yok.")
    verdict = _ratio_verdict(ratio, cfg["cheap_below"], cfg["expensive_above"])
    return VerdictLens(
        key="peers", label=label, verdict=verdict, value=ratio,
        reason=f"Çarpanları {min(used_counts)}+ benzer şirketin {_vs(ratio - 1, 'medyanının', 'medyanıyla')}.",
    )


def _dcf_lens(valuation: ValuationMetrics, cfg: dict, not_applicable_reason: str | None = None) -> VerdictLens:
    label = "İndirgenmiş nakit akışına (DCF) göre"
    if not_applicable_reason:
        # Bankalar (ADR-014): yöntem uygulanmaz, oy vermez, eksik veri sayılmaz.
        return VerdictLens(key="dcf", label=label, verdict=None, value=None,
                           reason=not_applicable_reason, not_applicable=True)
    upside = valuation.dcf.base.upside_vs_current_price if valuation.dcf else None
    if upside is None:
        return VerdictLens(key="dcf", label=label, verdict=None, value=None,
                           reason="DCF hesaplanamadı.")
    if upside > cfg["cheap_above_upside"]:
        verdict = "UCUZ"
    elif upside < cfg["expensive_below_upside"]:
        verdict = "PAHALI"
    else:
        verdict = "MAKUL"
    return VerdictLens(
        key="dcf", label=label, verdict=verdict, value=upside,
        reason=f"Baz senaryo içsel değeri {_vs(upside, 'güncel fiyatın', 'güncel fiyatla')}.",
    )


def _quality(overall: float | None, cfg: dict) -> str | None:
    if overall is None:
        return None
    if overall >= cfg["strong_at_or_above"]:
        return "GUCLU"
    if overall >= cfg["medium_at_or_above"]:
        return "ORTA"
    return "ZAYIF"


def _headline(price: str | None, quality: str | None, voted: int, agreeing: int) -> str:
    quality_part = f"{_QUALITY_TR[quality]} şirket" if quality else "Kalitesi ölçülemeyen şirket"
    if voted == 0:
        return "Fiyat hakkında hüküm vermek için yeterli değerleme verisi yok."
    if price is None:
        return f"{quality_part}; değerleme yöntemleri farklı yönleri gösteriyor, fiyat için net bir hüküm yok."
    return (
        f"{quality_part}, fiyatı {_PRICE_TR[price]} — "
        f"{voted} değerleme yönteminden {agreeing} tanesi bu yönde."
    )


def compute_verdict(
    valuation: ValuationMetrics,
    scores: ScoreResult,
    data_quality_overall: float,
    peers: PeerMedians | None,
    config: dict,
    unsupported_reason: str | None = None,
    dcf_not_applicable_reason: str | None = None,
) -> Verdict:
    version = config["version"]
    signal_enabled = bool(config["signal"]["enabled"])

    if unsupported_reason:
        return Verdict(
            price=None, quality=None, confidence="DUSUK", headline="Bu sektör için hüküm üretilmiyor.",
            lenses=[], agreement=None, overall_score=None, engine_version=version,
            missing_fields=["unsupported_industry"], unsupported_reason=unsupported_reason,
            signal_is_demo=signal_enabled,
        )

    lens_cfg = config["lenses"]
    lenses = [
        _history_lens(valuation, lens_cfg["history"]),
        _peers_lens(valuation, peers, lens_cfg["peers"]),
        _dcf_lens(valuation, lens_cfg["dcf"], dcf_not_applicable_reason),
    ]
    missing = [f"verdict_lens_{lens.key}" for lens in lenses if lens.verdict is None and not lens.not_applicable]
    votes = [lens.verdict for lens in lenses if lens.verdict]

    # Gerçek çoğunluk: yarıdan fazlası aynı şeyi demeli. Ortalama alınmaz —
    # aksi halde azınlıktaki tek bir yöntem hükmü (ve sinyali) belirleyebilir.
    price: str | None = None
    agreeing = 0
    for label in ("UCUZ", "MAKUL", "PAHALI"):
        count = votes.count(label)
        if count * 2 > len(votes):
            price, agreeing = label, count
    agreement = agreeing / len(votes) if votes else None

    overall = scores.overall if scores.unsupported_reason is None else None
    quality = _quality(overall, config["quality"])
    if quality is None:
        missing.append("verdict_quality")

    conf_cfg = config["confidence"]
    if (
        len(votes) >= conf_cfg["high_min_lenses"]
        and agreement is not None
        and agreement >= conf_cfg["high_min_agreement"]
        and data_quality_overall >= conf_cfg["high_min_data_quality"]
    ):
        confidence = "YUKSEK"
    elif price is None or len(votes) < 2 or data_quality_overall < conf_cfg["low_below_data_quality"]:
        confidence = "DUSUK"
    else:
        confidence = "ORTA"

    signal = (
        _SIGNAL_MATRIX.get((price, quality))
        if signal_enabled and price and quality and confidence != "DUSUK"
        else None
    )

    return Verdict(
        price=price,
        quality=quality,
        confidence=confidence,
        signal=signal,
        signal_is_demo=signal_enabled,
        headline=_headline(price, quality, len(votes), agreeing),
        lenses=lenses,
        agreement=agreement,
        overall_score=overall,
        engine_version=version,
        missing_fields=missing,
    )
