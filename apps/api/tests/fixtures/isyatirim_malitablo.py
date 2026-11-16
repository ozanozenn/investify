"""Recorded-SHAPE fixtures for İş Yatırım's `MaliTablo` endpoint — NOT real
recorded data.

The envelope and row shape follow what open-source clients document or keep
as recorded fixtures (borsa-mcp `providers/isyatirim_provider.py`,
isyatirimhisse `FetchFinancials.py`, OracleX
`backend/tests/fixtures/isyatirim_thyao_2026Q2.json`, bistmas
`tests/fixtures/isyatirim_fin/TRKCM_2019.json`, QuaxisLabs notes):

    {"ok": true, "errorCode": null, "errorDescription": null,
     "transactionId": "...", "value": [
        {"itemCode": "1BL", "itemDescTr": "TOPLAM VARLIKLAR",
         "itemDescEng": "TOTAL ASSETS", "value1": "...", ..., "value4": null}, ...]}

- `valueN` belongs to the N-th (year, period) pair of the request.
- Values are numeric strings (or null for unpublished periods).
- Sub-items carry leading spaces in `itemDescTr` (e.g. "  Nakit ve Nakit Benzerleri").
- Income-statement (3*) and cash-flow (4*) values are cumulative YTD.

The numbers below are synthetic and round so YTD differencing can be
checked by hand. Requests in these fixtures always use periods (3, 6, 9, 12)
in that order, matching `isyatirim_provider._PERIODS`.
"""

from __future__ import annotations

ROW_LABELS: dict[str, tuple[str, str]] = {
    "1A": ("Dönen Varlıklar", "CURRENT ASSETS"),
    "1AA": ("  Nakit ve Nakit Benzerleri", "Cash and Cash Equivalents"),
    "1BL": ("TOPLAM VARLIKLAR", "TOTAL ASSETS"),
    "2A": ("Kısa Vadeli Yükümlülükler", "SHORT TERM LIABILITIES"),
    "2AA": ("  Finansal Borçlar", "Short-Term Financial Loans"),
    "2BA": ("  Finansal Borçlar", "Long-Term Financial Loans"),
    "2N": ("Özkaynaklar", "SHAREHOLDERS EQUITY"),
    "2O": ("  Ana Ortaklığa Ait Özkaynaklar", "Parent Shareholders Capital"),
    "3C": ("Satış Gelirleri", "Net Sales"),
    "3D": ("BRÜT KAR (ZARAR)", "GROSS PROFIT (LOSS)"),
    "3DF": ("FAALİYET KARI (ZARARI)", "OPERATING PROFITS"),
    "3H": ("Net Faaliyet Kar/Zararı", "Net Operating Profits"),
    "3L": ("DÖNEM KARI (ZARARI)", "NET PROFIT AFTER TAXES"),
    "3Z": ("Ana Ortaklık Payları", "Parent Shares"),
    "4B": ("Amortisman Giderleri", "Depreciation & Amortization"),
    "4C": (" İşletme Faaliyetlerinden Kaynaklanan Net Nakit", " Net Cash from Operations"),
    "4CAI": ("  Sabit Sermaye Yatırımları", "  Capital Expenditures (CapEx)"),
    "4CB": ("Serbest Nakit Akım", "Free Cash Flow"),
}

M = 1_000_000  # values are full TRY units; fixtures use round millions


def _s(value: float | None) -> str | None:
    return None if value is None else str(round(value))


def cumulative_year(scale: float = 1.0) -> dict[str, list[float | None]]:
    """One fiscal year, all four quarter-ends reported. Periods: 3, 6, 9, 12.
    Flow items are cumulative: revenue Q1=100, Q2=120, Q3=130, Q4=150 (x scale, x M)."""

    def cum(*quarters: float) -> list[float | None]:
        running, out = 0.0, []
        for q in quarters:
            running += q
            out.append(running * scale * M)
        return out

    def snap(*values: float) -> list[float | None]:
        return [v * scale * M for v in values]

    return {
        "1A": snap(400, 420, 440, 460),
        "1AA": snap(80, 85, 90, 95),
        "1BL": snap(1000, 1100, 1200, 1300),
        "2A": snap(300, 310, 320, 330),
        "2AA": snap(50, 55, 60, 65),
        "2BA": snap(150, 160, 170, 180),
        "2N": snap(500, 520, 540, 560),
        "2O": snap(450, 470, 490, 510),
        "3C": cum(100, 120, 130, 150),
        "3D": cum(30, 36, 39, 45),
        "3DF": cum(18, 22, 24, 30),
        "3H": cum(20, 22, 24, 24),
        "3L": cum(11, 16, 21, 26),
        "3Z": cum(10, 15, 20, 25),
        "4B": cum(5, 5, 5, 5),
        "4C": cum(25, 30, 35, 40),
        "4CAI": cum(-10, -12, -14, -16),
        "4CB": cum(5, 6, 7, 8),
    }


def year_payload(values_by_code: dict[str, list[float | None]]) -> dict:
    rows = []
    for code, values in values_by_code.items():
        desc_tr, desc_eng = ROW_LABELS.get(code, (code, code))
        row = {"itemCode": code, "itemDescTr": desc_tr, "itemDescEng": desc_eng}
        for index, value in enumerate(values, start=1):
            row[f"value{index}"] = _s(value)
        rows.append(row)
    return {
        "ok": True,
        "errorCode": None,
        "errorDescription": None,
        "transactionId": "00000000-0000-0000-0000-000000000000",
        "value": rows,
    }


def partial_year(values_by_code: dict[str, list[float | None]], reported_periods: int) -> dict[str, list[float | None]]:
    """Same year with only the first `reported_periods` quarter-ends
    published; the rest come back null (as the live endpoint does)."""
    return {
        code: [v if i < reported_periods else None for i, v in enumerate(values)]
        for code, values in values_by_code.items()
    }


def empty_payload() -> dict:
    """What the endpoint returns for a wrong financialGroup / unknown code."""
    return {"ok": True, "errorCode": None, "errorDescription": None, "transactionId": "x", "value": []}
