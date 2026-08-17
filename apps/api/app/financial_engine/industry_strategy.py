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
    "Specialized financial analysis not yet supported for this industry "
    "(e.g. banks/insurers/REITs use different statement structures). "
    "Generic industrial scoring is intentionally withheld rather than "
    "shown with misleading figures. See docs/PHASE_1_SCOPE.md."
)


def is_generic_engine_supported(is_financial_industry: bool) -> bool:
    return not is_financial_industry
