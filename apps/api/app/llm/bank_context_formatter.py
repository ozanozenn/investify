"""Banka göstergelerinin LLM prompt'una giden insan-okunur biçimi (ADR-014,
ADR-003). `context_formatter.py` yalnızca bankalarda bu çıktıyı
`bank_metrics` anahtarıyla ekler. Biçimleme kuralları ve geri-okuma
(`hallucination_guard.py`) `number_format.py` ile aynıdır."""

from __future__ import annotations

from app.llm.number_format import format_currency, format_ratio_percent
from app.schemas.bank import BankMetrics

BANK_CONTEXT_NOTE = (
    "Bu şirket bir bankadır. Genel 'metrics' alanındaki FAVÖK, net borç ve "
    "serbest nakit akışı göstergeleri bankalarda anlamsız olduğu için boştur; "
    "bankayı bu alandaki göstergelerle ve PD/DD, F/K çarpanlarıyla değerlendir. "
    "DCF bankalara uygulanmaz ve nakit akışı skoru hesaba katılmaz. "
    "'nim_proxy' gerçek net faiz marjı değildir: net faiz gelirinin ortalama "
    "toplam aktife oranıdır (yaklaşık, gerçek marjdan düşüktür). "
    "'cost_income_ratio' da yaklaşıktır (payda sağlayıcının toplam gelir kalemi)."
)

_PERCENT_FIELDS = (
    "roe", "roa", "nim_proxy", "cost_income_ratio",
    "nii_growth_yoy", "net_income_growth_yoy", "equity_growth_yoy",
    "equity_to_assets", "loan_to_deposit", "provision_to_nii",
)
_CURRENCY_FIELDS = (
    "latest_net_interest_income", "latest_net_income", "latest_total_assets",
    "latest_equity", "latest_loans", "latest_deposits",
)


def format_bank_metrics(bm: BankMetrics) -> dict:
    out: dict = {
        "note": BANK_CONTEXT_NOTE,
        "as_of_period": bm.as_of_period,
        "engine_version": bm.engine_version,
        "missing_fields": bm.missing_fields,
    }
    for field in _PERCENT_FIELDS:
        value = getattr(bm, field)
        out[field] = format_ratio_percent(value) if value is not None else None
    for field in _CURRENCY_FIELDS:
        value = getattr(bm, field)
        out[field] = format_currency(value) if value is not None else None
    return out
