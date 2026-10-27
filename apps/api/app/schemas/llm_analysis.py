from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

Outlook = Literal["POSITIVE", "NEUTRAL_POSITIVE", "NEUTRAL", "NEUTRAL_NEGATIVE", "NEGATIVE"]

# Madde sınırları çıktı sözleşmesinin parçası: company-analysis-v4.md aynı
# sayıları metin olarak söyler. JSON Schema'ya `maxItems` olarak konmaz —
# OpenAI Structured Outputs ile Gemini `response_schema` desteği sürümden
# sürüme değişiyor; şema sade kalır, sınır alan açıklamasıyla modele
# söylenir ve fazlası burada kesilir (en önemli madde önce istendiği için
# baştakiler korunur). Fazla madde yüzünden tüm LLM aşamasını FAILED
# yapmak, kullanıcıya hiç özet göstermemek demek olurdu.
MAX_ITEMS: dict[str, int] = {
    "what_matters_now": 5,
    "bull_case": 3,
    "bear_case": 3,
    "key_risks": 4,
    "key_catalysts": 4,
    "thesis_breakers": 3,
    "what_to_watch": 4,
}


def _capped(field: str, description: str):
    limit = MAX_ITEMS[field]
    return Annotated[
        list[str],
        AfterValidator(lambda items: items[:limit]),
        Field(description=f"En fazla {limit} madde. {description}"),
    ]


WhatMattersNow = _capped("what_matters_now", "En önemlisi önce; her madde tek cümle.")
BullCase = _capped("bull_case", "Olumlu senaryo; her iddia context'e izlenebilir.")
BearCase = _capped("bear_case", "Olumsuz senaryo; her iddia context'e izlenebilir.")
KeyRisks = _capped("key_risks", "Başlıca riskler.")
KeyCatalysts = _capped("key_catalysts", "Başlıca katalizörler.")
ThesisBreakers = _capped("thesis_breakers", "Somut, kontrol edilebilir koşullar.")
WhatToWatch = _capped("what_to_watch", "Takip edilecek somut gelişmeler.")


# Not: bu sınıflarda docstring yerine yorum kullanılıyor — Pydantic sınıf
# docstring'ini JSON Schema `description`'ına koyar ve şema her çağrıda
# modele gider; geliştirici notları boşuna token harcatır.


# v4: ufuk başına tek etiket + kısa gerekçe. LLM'in kendi "güven" sayısı
# (v1-v3 `confidence`) kaldırıldı — sayı üretmek LLM'in işi değil
# (ADR-003); güvenilirlik deterministik hüküm kartından gelir (ADR-011).
class HorizonOutlook(BaseModel):
    outlook: Outlook
    rationale: str = Field(description="1-2 cümlelik koşullu senaryo; bu ufukta öne çıkan dinamik.")


# Structured LLM output, company-analysis-v4 shape (ADR-003). Validated
# with Pydantic against the JSON Schema sent to OpenAI Structured Outputs /
# Gemini `response_schema` — if this fails to parse, the pipeline stage is
# marked FAILED, never silently patched (only over-long lists are trimmed,
# see MAX_ITEMS).
#
# v1-v3 snapshots (`drivers`/`risks`/`catalysts`/`confidence` per horizon,
# no `what_matters_now`) are never re-parsed through this model:
# `analysis_json` is served as a plain dict and the frontend renders
# whichever shape it finds.
class LLMAnalysisResult(BaseModel):
    executive_summary: str = Field(description="2-4 cümle: deterministik hükmün sade Türkçe açıklaması.")
    what_matters_now: WhatMattersNow
    short_term: HorizonOutlook
    medium_term: HorizonOutlook
    long_term: HorizonOutlook
    bull_case: BullCase
    bear_case: BearCase
    key_risks: KeyRisks
    key_catalysts: KeyCatalysts
    thesis_breakers: ThesisBreakers
    what_to_watch: WhatToWatch
