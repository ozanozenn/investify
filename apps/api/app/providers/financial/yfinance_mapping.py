"""Maps yfinance's (Yahoo Finance) raw statement row labels to Investify's
canonical fields (ADR-004). Yahoo's row naming is not perfectly stable
across companies/versions, so each canonical field has an ordered list of
candidate labels — the first one present in the statement wins.
"""

from __future__ import annotations

from app.models.enums import CanonicalField

INCOME_STATEMENT_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.REVENUE: ["Total Revenue", "Operating Revenue"],
    CanonicalField.GROSS_PROFIT: ["Gross Profit"],
    CanonicalField.EBITDA: ["EBITDA", "Normalized EBITDA"],
    CanonicalField.EBIT: ["EBIT", "Operating Income"],
    CanonicalField.NET_INCOME: [
        "Net Income",
        "Net Income Common Stockholders",
        "Net Income From Continuing Operation Net Minority Interest",
    ],
}

BALANCE_SHEET_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.CASH: [
        "Cash And Cash Equivalents",
        "Cash Cash Equivalents And Short Term Investments",
    ],
    CanonicalField.TOTAL_ASSETS: ["Total Assets"],
    CanonicalField.TOTAL_DEBT: ["Total Debt"],
    CanonicalField.EQUITY: [
        "Stockholders Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ],
    # Kalite bayrakları (ADR-016). Etiketler yfinance 0.2.66 `const.py`
    # fundamentals_keys["balance-sheet"] ("AccountsReceivable", "Receivables",
    # "Inventory") + `camel2title` ile doğrulandı. Önce ticari alacak, yoksa
    # toplam alacak — aynı şirkette yıllar arasında etiket karışabilir, bu
    # bilinen bir yaklaşıklıktır.
    CanonicalField.RECEIVABLES: ["Accounts Receivable", "Receivables"],
    CanonicalField.INVENTORY: ["Inventory"],
}

CASH_FLOW_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.OPERATING_CASH_FLOW: ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    CanonicalField.CAPEX: ["Capital Expenditure", "Purchase Of PPE"],
    CanonicalField.FREE_CASH_FLOW: ["Free Cash Flow"],
}


def extract(row_map: dict[CanonicalField, list[str]], statement_index: list[str], column) -> dict[str, float]:
    """`column` is a pandas Series for one period (statement[period_column])."""
    result: dict[str, float] = {}
    for canonical, candidates in row_map.items():
        for label in candidates:
            if label in statement_index:
                value = column.get(label)
                if value is not None and value == value:  # not NaN
                    result[canonical.value] = float(value)
                    break
    return result


# --- Banka kalemleri (ADR-014) ---------------------------------------------
# Satır adları canlı veriyle DEĞİL, kurulu yfinance 0.2.66 kaynağıyla
# doğrulandı: yfinance yalnızca `yfinance/const.py:fundamentals_keys`
# listesindeki anahtarları Yahoo'dan ister (`scrapers/fundamentals.py`:
# `df.reindex([k for k in keys if k in df.index])`) ve `pretty=True` ile
# `utils.camel2title` üzerinden "Net Interest Income" biçimine çevirir.
# Doğrulanan anahtarlar:
#   'financials':    NetInterestIncome, InterestIncome, InterestExpense,
#                    OperatingExpense, SellingGeneralAndAdministration,
#                    ProvisionForDoubtfulAccounts
#   'balance-sheet': LoansReceivable
# Mevduat (Deposits / TotalDeposits) bu listede YOK — yfinance bankalar için
# mevduat kalemi döndüremez; DEPOSITS bilerek eşlenmedi, kredi/mevduat oranı
# bu sağlayıcıyla hep `missing_fields`'e düşer. Türk bankaları için hangi
# kalemlerin gerçekten dolu geldiği canlı doğrulanmadı:
# `scripts/verify_bank_fields.py` internet erişimi olan makinede çalıştırılmalı.
BANK_INCOME_STATEMENT_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.NET_INTEREST_INCOME: ["Net Interest Income"],
    CanonicalField.INTEREST_INCOME: ["Interest Income"],
    CanonicalField.INTEREST_EXPENSE: ["Interest Expense"],
    CanonicalField.OPERATING_EXPENSE: ["Operating Expense", "Selling General And Administration"],
    CanonicalField.CREDIT_LOSS_PROVISION: ["Provision For Doubtful Accounts"],
}

BANK_BALANCE_SHEET_MAP: dict[CanonicalField, list[str]] = {
    CanonicalField.LOANS: ["Loans Receivable"],
}

# Banka kalemleri her şirket için çekilir (sanayi şirketinde de "Interest
# Expense" vardır; genel motor bu alanları okumaz). Sağlayıcı dosyasına
# dokunmadan mevcut `extract` çağrılarına girmeleri için ana sözlüklere eklenir.
INCOME_STATEMENT_MAP.update(BANK_INCOME_STATEMENT_MAP)
BALANCE_SHEET_MAP.update(BANK_BALANCE_SHEET_MAP)
