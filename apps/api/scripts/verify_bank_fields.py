"""Banka alanları canlı doğrulama betiği (ADR-014).

Geliştirme ortamında Yahoo'ya erişim yok; banka kalemlerinin yfinance satır
adları yalnızca kurulu yfinance kaynağına (`const.py:fundamentals_keys`) göre
eşlendi. Bu betik, internet erişimi olan bir makinede, hangi banka kanonik
alanlarının hangi dönemde GERÇEKTEN dolu geldiğini ve banka motorunun bu
veriyle ne hesapladığını gösterir.

Kullanım (apps/api içinden):
    .venv/bin/python scripts/verify_bank_fields.py                # GARAN AKBNK YKBNK
    .venv/bin/python scripts/verify_bank_fields.py ISCTR HALKB TSKB
    .venv/bin/python scripts/verify_bank_fields.py GARAN --raw    # ham satır adlarını da yaz

Çıktıda "—" olan alan, sağlayıcının o dönem için o kalemi vermediği
anlamına gelir; motor bu durumda oranı hesaplamaz (`missing_fields`).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # apps/api

import yfinance as yf  # noqa: E402

from app.financial_engine.bank_engine import compute_bank_metrics  # noqa: E402
from app.financial_engine.industry_strategy import is_bank_industry  # noqa: E402
from app.providers.company.seed import SEED_COMPANIES  # noqa: E402
from app.providers.company.taxonomy import normalize_sector_industry  # noqa: E402
from app.providers.financial.yfinance_mapping import (  # noqa: E402
    BANK_BALANCE_SHEET_MAP,
    BANK_INCOME_STATEMENT_MAP,
)
from app.providers.financial.yfinance_provider import YFinanceFinancialDataProvider  # noqa: E402
from app.schemas.financial import PeriodData  # noqa: E402

DEFAULT_TICKERS = ["GARAN", "AKBNK", "YKBNK"]

# Banka motorunun okuduğu tüm kanonik alanlar (genel + banka kalemleri).
BANK_FIELDS = ["NET_INCOME", "EQUITY", "TOTAL_ASSETS", "REVENUE"] + [
    f.value for f in (*BANK_INCOME_STATEMENT_MAP, *BANK_BALANCE_SHEET_MAP)
] + ["DEPOSITS"]

RAW_KEYWORDS = ("interest", "loan", "deposit", "provision", "revenue", "expense", "credit", "fee")

PERCENT_METRICS = (
    "roe", "roa", "nim_proxy", "cost_income_ratio", "nii_growth_yoy", "net_income_growth_yoy",
    "equity_growth_yoy", "equity_to_assets", "loan_to_deposit", "provision_to_nii",
)


def _fmt_amount(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value / 1e9:,.2f} mlr"


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"%{value * 100:.2f}"


def _print_detection(ticker: str) -> None:
    info = yf.Ticker(f"{ticker}.IS").info or {}
    sector, industry = info.get("sector"), info.get("industry")
    is_financial = (sector or "").lower() in ("financial services", "financials")
    norm_sector, norm_industry = normalize_sector_industry(sector, industry)
    print(f"  yfinance profili: sector={sector!r} industry={industry!r}")
    print(f"  normalize: ({norm_sector}, {norm_industry}) → banka mı: {is_bank_industry(is_financial, norm_industry)}")
    if ticker in SEED_COMPANIES:
        seed = SEED_COMPANIES[ticker]
        print(f"  seed kaydı var (önce o kullanılır): industry={seed['industry']!r} → banka mı: "
              f"{is_bank_industry(seed['is_financial_industry'], seed['industry'])}")


def _print_raw_labels(ticker: str) -> None:
    yt = yf.Ticker(f"{ticker}.IS")
    for name, frame in (("gelir tablosu", yt.financials), ("bilanço", yt.balance_sheet)):
        labels = [] if frame is None or frame.empty else list(frame.index)
        related = [label for label in labels if any(k in label.lower() for k in RAW_KEYWORDS)]
        print(f"  ham {name} satırları ({len(labels)} satır, ilgili olanlar): {related}")


def verify(ticker: str, show_raw: bool) -> None:
    print(f"\n=== {ticker} ===")
    try:
        _print_detection(ticker)
    except Exception as exc:  # canlı profil alınamazsa diğer kontroller sürer
        print(f"  profil alınamadı: {exc}")

    provider = YFinanceFinancialDataProvider()
    try:
        periods = asyncio.run(provider.get_financial_statements(ticker))
    except Exception as exc:
        print(f"  finansal tablolar alınamadı: {exc}")
        return

    for period in sorted(periods, key=lambda p: (p.period_type, p.period_end_date)):
        label = f"{period.period_type[:3]} {period.period_end_date.isoformat()}"
        present = [f for f in BANK_FIELDS if f in period.values]
        missing = [f for f in BANK_FIELDS if f not in period.values]
        print(f"  {label}: dolu={len(present)}/{len(BANK_FIELDS)} eksik={missing}")
        print("    " + " | ".join(f"{f}={_fmt_amount(period.values.get(f))}" for f in present))

    annual = [
        PeriodData(
            period_type=p.period_type, fiscal_year=p.fiscal_year, fiscal_quarter=p.fiscal_quarter,
            period_end_date=p.period_end_date, values=p.values,
        )
        for p in periods
        if p.period_type == "ANNUAL"
    ]
    metrics = compute_bank_metrics(annual)
    print(f"  banka motoru ({metrics.engine_version}, dönem {metrics.as_of_period}):")
    print("    " + " | ".join(f"{m}={_fmt_pct(getattr(metrics, m))}" for m in PERCENT_METRICS))
    print(f"    missing_fields={metrics.missing_fields}")

    if show_raw:
        _print_raw_labels(ticker)


def main() -> None:
    parser = argparse.ArgumentParser(description="yfinance banka alanlarını canlı doğrular (ADR-014).")
    parser.add_argument("tickers", nargs="*", default=DEFAULT_TICKERS, help="BIST kodları (varsayılan: GARAN AKBNK YKBNK)")
    parser.add_argument("--raw", action="store_true", help="ham yfinance satır adlarından ilgili olanları da yaz")
    args = parser.parse_args()
    print(f"yfinance {yf.__version__} — Yahoo'dan canlı veri çekiliyor...")
    for ticker in args.tickers:
        verify(ticker.upper(), args.raw)


if __name__ == "__main__":
    main()
