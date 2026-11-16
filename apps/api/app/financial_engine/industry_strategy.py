"""IndustryAnalysisStrategy (roadmap section 10 / Phase 1 section 9).

Banks, insurers, REITs and holdings use fundamentally different statement
shapes and ratios (roadmap sections 61-63) that the generic industrial
financial_engine cannot honestly compute (e.g. a bank has no "Revenue" or
"EBITDA" line item in the sense used here). Rather than emit a
plausible-looking but wrong generic score, Phase 1 detects this up front
and returns a clear "not yet supported" state end-to-end (engine -> API ->
UI), per the explicit instruction: "Yanlış generic skor üretmektense
unsupported state göster."

`Company.is_financial_industry` is the current (Phase 1) detection
mechanism — set from the seed data or from the yfinance sector field
("Financial Services"). A real bank-specific engine is Phase 2+ scope
(docs/PHASE_1_SCOPE.md item 5).
"""

from __future__ import annotations

UNSUPPORTED_INDUSTRY_MESSAGE = (
    "Bu şirketin sektörü için özel finansal analiz henüz desteklenmiyor "
    "(sigorta şirketleri ve GYO'lar farklı bir finansal tablo yapısı "
    "kullanır; bankalar kendi motoruyla analiz edilir). Yanıltıcı bir skor "
    "göstermek yerine, genel sanayi skorlaması bilinçli olarak gösterilmiyor."
)


def is_generic_engine_supported(is_financial_industry: bool) -> bool:
    return not is_financial_industry


# --- Bankalar (ADR-014) ------------------------------------------------------
# Bankalar artık genel motor yerine `bank_engine.py` ile analiz edilir;
# sigorta ve GYO hâlâ yukarıdaki "desteklenmiyor" yolundadır.

BANK_DCF_NOT_APPLICABLE_MESSAGE = (
    "Bankalar için DCF uygulanmaz; değerleme PD/DD ve özkaynak kârlılığı "
    "üzerinden yapılır."
)

# Normalize endüstri adı (providers/company/taxonomy.py ve seed.py:
# "Bankacılık") ile taksonomi öncesi kaydedilmiş olabilecek ham yfinance adları.
_BANK_INDUSTRY_NAMES = frozenset(
    {
        "bankacılık",
        "bankacilik",  # "BANKACILIK".lower() noktalı i üretir
        "banks - regional",
        "banks—regional",
        "banks - diversified",
        "banks—diversified",
    }
)


def is_bank_industry(is_financial_industry: bool, industry_name: str | None) -> bool:
    """Banka mı? Hem finansal sektör bayrağı hem de banka endüstri adı
    gerekir — sigorta ("Sigorta") ve GYO ("GYO") burada False döner ve
    desteklenmeyen yolda kalır. Bilinmeyen endüstri adı asla banka sayılmaz."""
    if not is_financial_industry or not industry_name:
        return False
    return industry_name.strip().lower() in _BANK_INDUSTRY_NAMES
