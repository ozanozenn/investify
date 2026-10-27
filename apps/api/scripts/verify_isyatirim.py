"""İş Yatırım finansal tablo sağlayıcısını canlı doğrulama betiği (ADR-015).

AGENTS.md: yeni bir sağlayıcı mock'a değil gerçek API'ye karşı en az bir
kez canlı doğrulanmadan kullanılmaz. Bu betik internet erişimi olan bir
makinede çalıştırılır; İş Yatırım ve Yahoo Finance'ten aynı şirketlerin
tablolarını çeker, dönemleri yan yana basar ve çapraz kontrol farklarını
gösterir. Çıktıya göre varsayılan kaynak değiştirilebilir:

    cd apps/api
    .venv/bin/python scripts/verify_isyatirim.py                 # THYAO ASELS FROTO
    .venv/bin/python scripts/verify_isyatirim.py SISE BIMAS --dump-codes --quarterly

`--dump-codes`, eşlemede kullanılan kalem kodlarının canlı Türkçe
etiketlerini basar (ör. 3C -> "Satış Gelirleri"); eşleme dosyası
(`app/providers/financial/isyatirim_mapping.py`) bununla teyit edilir.

Çıkış kodu: İş Yatırım her şirket için veri döndürdüyse 0, aksi halde 1.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
from collections.abc import Sequence

from app.core.config import get_analysis_config, get_financial_sources_config
from app.llm.number_format import format_currency, format_ratio_percent
from app.models.enums import CanonicalField
from app.providers.base import FinancialDataProvider, RawFinancialPeriod
from app.providers.financial.composite_provider import compare_periods, relative_difference
from app.providers.financial.isyatirim_mapping import ITEM_CODE_MAP, SUM_MAP
from app.providers.financial.isyatirim_provider import IsYatirimFinancialDataProvider
from app.providers.financial.yfinance_provider import YFinanceFinancialDataProvider
from app.services.financial_sources import FIELD_LABELS

DEFAULT_TICKERS = ("THYAO", "ASELS", "FROTO")


def _fmt(value: float | None) -> str:
    return "—" if value is None else format_currency(value, "TL", decimals=2)


def _period_name(p: RawFinancialPeriod) -> str:
    return f"{p.fiscal_year} yıllık" if p.period_type == "ANNUAL" else f"{p.fiscal_year} Ç{p.fiscal_quarter}"


async def _fetch(provider: FinancialDataProvider, ticker: str, annual_years: int, quarters: int):
    try:
        return await provider.get_financial_statements(
            ticker, annual_years=annual_years, quarterly_quarters=quarters
        ), None
    except Exception as exc:  # the point of the script is to show what fails
        return [], f"{type(exc).__name__}: {exc}"


def side_by_side(
    isy: Sequence[RawFinancialPeriod], yf: Sequence[RawFinancialPeriod], period_types: set[str]
) -> list[str]:
    lines: list[str] = []
    yf_by_key = {(p.period_type, p.fiscal_year, p.fiscal_quarter): p for p in yf}
    keys = sorted(
        {(p.period_type, p.fiscal_year, p.fiscal_quarter) for p in [*isy, *yf] if p.period_type in period_types},
        key=lambda k: (k[0] != "ANNUAL", -k[1], -(k[2] or 0)),
    )
    isy_by_key = {(p.period_type, p.fiscal_year, p.fiscal_quarter): p for p in isy}
    for key in keys:
        a, b = isy_by_key.get(key), yf_by_key.get(key)
        name = _period_name(a or b)
        lines.append(f"  {name}  (İş Yatırım: {'var' if a else 'yok'}, Yahoo: {'var' if b else 'yok'})")
        for field in CanonicalField:
            va = a.values.get(field.value) if a else None
            vb = b.values.get(field.value) if b else None
            if va is None and vb is None:
                continue
            diff = "" if va is None or vb is None else format_ratio_percent(relative_difference(va, vb))
            label = FIELD_LABELS.get(field.value, field.value)
            lines.append(f"    {label:<22} {_fmt(va):>22} {_fmt(vb):>22}  {diff}")
    return lines


async def dump_codes(provider: IsYatirimFinancialDataProvider, ticker: str, year: int) -> list[str]:
    rows = await provider.fetch_raw_rows(ticker, year)
    labels = {str(r.get("itemCode") or "").strip(): r for r in rows}
    lines = [f"  Kalem kodları ({year}, {len(rows)} satır; value4 = {year}/12):"]
    used: list[tuple[str, str]] = []
    for field, codes in ITEM_CODE_MAP.items():
        used += [(field.value, c) for c in codes]
    for field, codes in SUM_MAP.items():
        used += [(field.value, c) for c in codes]
    for field, code in used:
        row = labels.get(code)
        if row is None:
            lines.append(f"    {field:<20} {code:<6} YOK")
        else:
            desc = str(row.get("itemDescTr") or "").strip()
            lines.append(f"    {field:<20} {code:<6} {desc!r:<55} value4={row.get('value4')}")
    return lines


async def run(
    tickers: Sequence[str],
    isy: FinancialDataProvider,
    yf: FinancialDataProvider,
    *,
    annual_years: int,
    quarters: int,
    include_quarterly: bool,
    show_codes: bool,
    tolerance: float,
    fields: Sequence[str],
    out=print,
) -> int:
    failures = 0
    period_types = {"ANNUAL", "QUARTERLY"} if include_quarterly else {"ANNUAL"}
    for ticker in tickers:
        ticker = ticker.upper()
        out(f"\n=== {ticker} ===")
        (isy_periods, isy_err), (yf_periods, yf_err) = await asyncio.gather(
            _fetch(isy, ticker, annual_years, quarters), _fetch(yf, ticker, annual_years, quarters)
        )
        out(f"  İş Yatırım: {len(isy_periods)} dönem" + (f"  HATA: {isy_err}" if isy_err else ""))
        out(f"  Yahoo     : {len(yf_periods)} dönem" + (f"  HATA: {yf_err}" if yf_err else ""))
        if not isy_periods:
            failures += 1
        out(f"  {'Alan':<22} {'İş Yatırım':>22} {'Yahoo Finance':>22}  Fark")
        for line in side_by_side(isy_periods, yf_periods, period_types):
            out(line)
        if isy_periods and yf_periods:
            found = compare_periods(isy_periods, yf_periods, fields, period_types, tolerance)
            out(f"  Çapraz kontrol (tolerans {format_ratio_percent(tolerance)}): {len(found)} fark")
            for d in found:
                out(
                    f"    {d.fiscal_year} {d.period_type} {FIELD_LABELS.get(d.field, d.field)}: "
                    f"{_fmt(d.primary_value)} / {_fmt(d.secondary_value)} "
                    f"({format_ratio_percent(d.relative_difference)})"
                )
        if show_codes and isinstance(isy, IsYatirimFinancialDataProvider):
            try:
                for line in await dump_codes(isy, ticker, dt.date.today().year - 1):
                    out(line)
            except Exception as exc:
                out(f"  Kalem kodları alınamadı: {exc}")

    out("\n=== Özet ===")
    if failures:
        out(f"İş Yatırım {failures}/{len(tickers)} şirket için veri döndürmedi. Varsayılanı DEĞİŞTİRMEYİN.")
        return 1
    out("İş Yatırım tüm şirketler için veri döndürdü. Farkları inceledikten sonra .env'de:")
    out("  FINANCIAL_PROVIDER_PRIMARY=isyatirim")
    out("  FINANCIAL_PROVIDER_FALLBACK=yfinance")
    out("  FINANCIAL_CROSS_CHECK=true")
    out("(Önce yalnızca çapraz kontrol için: PRIMARY=yfinance, FALLBACK=isyatirim, CROSS_CHECK=true.)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    cfg = get_financial_sources_config()["cross_check"]
    history = get_analysis_config()["history"]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tickers", nargs="*", default=list(DEFAULT_TICKERS))
    parser.add_argument("--quarterly", action="store_true", help="çeyreklik dönemleri de göster/karşılaştır")
    parser.add_argument("--dump-codes", action="store_true", help="canlı kalem kodu etiketlerini bas")
    parser.add_argument("--tolerance", type=float, default=float(cfg["relative_tolerance"]))
    parser.add_argument("--annual-years", type=int, default=int(history["annual_years"]))
    parser.add_argument("--quarters", type=int, default=int(history["quarterly_quarters"]))
    args = parser.parse_args(argv)
    return asyncio.run(
        run(
            args.tickers,
            IsYatirimFinancialDataProvider(),
            YFinanceFinancialDataProvider(),
            annual_years=args.annual_years,
            quarters=args.quarters,
            include_quarterly=args.quarterly,
            show_codes=args.dump_codes,
            tolerance=args.tolerance,
            fields=cfg["fields"],
        )
    )


if __name__ == "__main__":
    sys.exit(main())
