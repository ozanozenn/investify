"""Deterministik hükmün (ADR-011) LLM prompt'una giden Türkçe biçimi
(company-analysis-v4, ADR-003).

LLM hükmü yalnızca AÇIKLAR: etiketler insan-okunur Türkçeye çevrilir,
bakış açısı gerekçeleri motorun yazdığı cümlelerle aynen gider. Ham oran
değerleri (`lens.value`, `agreement`) gönderilmez — gerekçe cümlesi
zaten biçimlendirilmiş yüzdeyi içerir ve LLM'in kendi başına oran
yorumlaması/yeniden hesaplaması istenmez. `hallucination_guard.py` bu
yüzden hükmün sayılarını ham alanlardan değil, buradaki metinlerden okur.

Demo sinyal (AL/TUT/SAT) yalnızca demo etiketi olarak, uyarı notuyla
gider; prompt LLM'e onu tekrar etmemesini söyler.
"""

from __future__ import annotations

from app.schemas.verdict import Verdict

PRICE_LABEL_TR = {"UCUZ": "Ucuz", "MAKUL": "Makul", "PAHALI": "Pahalı"}
QUALITY_LABEL_TR = {"GUCLU": "Güçlü", "ORTA": "Orta", "ZAYIF": "Zayıf"}
CONFIDENCE_LABEL_TR = {"YUKSEK": "Yüksek", "ORTA": "Orta", "DUSUK": "Düşük"}

DEMO_SIGNAL_NOTE = (
    "yalnızca demo amaçlı deterministik etiket; yatırım tavsiyesi değildir — "
    "metinde tekrar etme, yorumlama"
)


def format_verdict_for_prompt(verdict: Verdict | None) -> dict | None:
    if verdict is None:
        return None
    return {
        "headline": verdict.headline,
        "price": PRICE_LABEL_TR[verdict.price] if verdict.price else None,
        "quality": QUALITY_LABEL_TR[verdict.quality] if verdict.quality else None,
        "confidence": CONFIDENCE_LABEL_TR[verdict.confidence],
        "lenses": [
            {
                "label": lens.label,
                "verdict": PRICE_LABEL_TR[lens.verdict] if lens.verdict else None,
                "reason": lens.reason,
            }
            for lens in verdict.lenses
        ],
        "demo_signal": f"{verdict.signal} ({DEMO_SIGNAL_NOTE})" if verdict.signal else None,
        "missing_fields": verdict.missing_fields,
        "unsupported_reason": verdict.unsupported_reason,
    }
