"""Çarpan bazında "kendi geçmişine göre" etiketleri (F/K, PD/DD, FD/FAVÖK).

Hüküm kartının tarihsel bakış açısı (`engine._history_lens`) üç çarpanın
ortalamasına bakar; sayfadaki değerleme kutucukları ise her çarpanı ayrı
gösterir. İkisi de AYNI sınıflandırıcıyı (`engine._ratio_verdict`) ve AYNI
eşikleri (`config/verdict.yaml` -> `lenses.history`) kullanır; böylece
sayfa kendi içinde çelişmez.

Saf fonksiyon — I/O yok, eşikler argüman olarak gelir.
"""

from __future__ import annotations

from app.schemas.valuation import ValuationMetrics
from app.verdict_engine.engine import _ratio_verdict

_MULTIPLES = ("pe", "pb", "ev_ebitda")


def label_history_multiples(
    valuation: ValuationMetrics, *, cheap_below: float, expensive_above: float
) -> ValuationMetrics:
    """Her çarpan için etiket (UCUZ/MAKUL/PAHALI) ve fark (oran − 1) ekler.

    Oran yoksa (veya pozitif değilse) o çarpanın alanları None kalır —
    tahmin edilmez. Girdi değiştirilmez; güncellenmiş kopya döner.
    """
    updates: dict[str, object] = {}
    for multiple in _MULTIPLES:
        ratio = getattr(valuation, f"{multiple}_vs_history_ratio")
        if ratio is None or ratio <= 0:
            continue
        updates[f"{multiple}_vs_history_label"] = _ratio_verdict(ratio, cheap_below, expensive_above)
        updates[f"{multiple}_vs_history_diff"] = ratio - 1
    return valuation.model_copy(update=updates)
