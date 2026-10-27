"""KAP company-list parsing and the search index built on it (ADR-015).

The KAP inputs below are synthetic, built in the shapes open-source KAP
clients document (borsapy/borsa-mcp read the Excel export positionally with
a "BIST KODU" header row; bistmas/QuaxisLabs parse `/tr/Sektorler`'s
Next.js Flight payload) — NOT recorded KAP responses."""

from __future__ import annotations

import datetime as dt
import io
import json
import zipfile

import pytest

from app.providers.company import ticker_index
from app.providers.company.kap_company_list import (
    CompanyListParseError,
    build_document,
    parse_company_list,
    parse_company_rows,
    parse_sector_page,
    read_xlsx_rows,
    split_codes,
)
from app.providers.company.ticker_index import load_company_list, search_tickers

_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _xlsx(rows: list[list[str]], inline_cells: dict[tuple[int, int], str] | None = None) -> bytes:
    """Minimal xlsx: shared strings + one worksheet (what Excel/openpyxl write)."""
    strings: list[str] = []
    sheet_rows = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            ref = f"{chr(ord('A') + c)}{r}"
            if value == "":
                continue
            if inline_cells and (r, c) in inline_cells:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{inline_cells[(r, c)]}</t></is></c>')
                continue
            strings.append(value)
            cells.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
        sheet_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    shared = "".join(f"<si><t>{s}</t></si>" for s in strings)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{_NS}">{shared}</sst>')
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{_NS}"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>',
        )
    return buffer.getvalue()


_KAP_ROWS = [
    ["BIST Şirketleri", "", "", ""],
    ["BIST KODU", "ŞİRKET ÜNVANI", "ŞEHİR", "BAĞIMSIZ DENETİM KURULUŞU"],
    ["ACSEL", "ACISELSAN ACIPAYAM SELÜLOZ SANAYİ VE TİCARET A.Ş.", "DENİZLİ", "X DENETİM A.Ş."],
    ["KRDMA, KRDMB, KRDMD", "KARDEMİR KARABÜK DEMİR ÇELİK SANAYİ VE TİCARET A.Ş.", "KARABÜK", "Y A.Ş."],
    ["THYAO", "TÜRK HAVA YOLLARI A.O.", "İSTANBUL", "Z A.Ş."],
    ["", "BOŞ KODLU SATIR", "ANKARA", ""],
]


def test_split_codes_explodes_share_classes_and_drops_junk():
    assert split_codes("KRDMA, KRDMB, KRDMD") == ["KRDMA", "KRDMB", "KRDMD"]
    assert split_codes(" thyao ") == ["THYAO"]
    assert split_codes("-") == []


def test_xlsx_rows_resolve_shared_and_inline_strings():
    rows = read_xlsx_rows(_xlsx([["BIST KODU", "UNVAN"], ["X", "Y"]], inline_cells={(2, 1): "Inline Ünvan"}))
    assert rows == [["BIST KODU", "UNVAN"], ["X", "Inline Ünvan"]]


def test_company_list_from_xlsx_uses_header_and_explodes_codes():
    companies = parse_company_list(_xlsx(_KAP_ROWS))
    assert [c["ticker"] for c in companies] == ["ACSEL", "KRDMA", "KRDMB", "KRDMD", "THYAO"]
    thyao = companies[-1]
    assert thyao == {"ticker": "THYAO", "name": "TÜRK HAVA YOLLARI A.O.", "city": "İSTANBUL"}


def test_company_rows_without_header_fall_back_to_positional_columns():
    companies = parse_company_rows([["THYAO", "TÜRK HAVA YOLLARI A.O.", "İSTANBUL"]])
    assert companies == [{"ticker": "THYAO", "name": "TÜRK HAVA YOLLARI A.O.", "city": "İSTANBUL"}]


def test_company_list_from_html_table_export():
    html = (
        "<html><body><table><tr><th>BIST KODU</th><th>Şirket Ünvanı</th><th>Şehir</th></tr>"
        "<tr><td>ASELS</td><td>ASELSAN ELEKTRONİK SANAYİ VE TİCARET A.Ş.</td><td>ANKARA</td></tr>"
        "</table></body></html>"
    ).encode()
    assert parse_company_list(html)[0]["ticker"] == "ASELS"


def test_unknown_format_fails_loudly():
    with pytest.raises(CompanyListParseError):
        parse_company_list(b"\xd0\xcf\x11\xe0legacy-xls")
    with pytest.raises(CompanyListParseError):
        parse_company_list(_xlsx([["BIST KODU", "UNVAN"]]))  # header only, no companies


def test_sector_page_parses_escaped_flight_payload_and_prefers_sub_sector():
    objects = [
        {"mainSectorName": "İMALAT", "mainSectorOid": "m1", "stockCode": "ACSEL", "title": "A", "kapTypes": []},
        {"sectorName": "KAĞIT VE KAĞIT ÜRÜNLERİ", "sectorOid": "s1", "stockCode": "ACSEL", "title": "A",
         "kapTypes": ["IGS"]},
        {"sectorName": "ANA METAL SANAYİ", "sectorOid": "s2", "stockCode": "KRDMA, KRDMB, KRDMD",
         "title": "K", "kapTypes": ["IGS"]},
    ]
    flight = '1:["$","div",null,{"data":[{"title":"İMALAT","content":' + json.dumps(objects, ensure_ascii=False) + "}]}]"
    literal = json.dumps(flight, ensure_ascii=False)  # a JS string literal, as Next.js pushes it
    html = f"<html><script>self.__next_f.push([1,{literal}])</script></html>"

    sectors = parse_sector_page(html)

    assert sectors["ACSEL"] == "KAĞIT VE KAĞIT ÜRÜNLERİ"
    assert sectors["KRDMD"] == "ANA METAL SANAYİ"


def test_build_document_records_source_and_date():
    fetched = dt.datetime(2026, 10, 27, 12, 0, tzinfo=dt.timezone.utc)
    doc = build_document(
        parse_company_rows(_KAP_ROWS),
        {"THYAO": "ULAŞTIRMA VE DEPOLAMA"},
        fetched_at=fetched,
        source_urls=["https://www.kap.org.tr/tr/api/company/generic/excel/IGS/A"],
    )
    meta = doc["metadata"]
    assert meta["fetched_at"] == "2026-10-27T12:00:00+00:00"
    assert meta["company_count"] == 5
    assert meta["with_sector"] == 1
    assert "KAP" in meta["source"]
    assert doc["companies"][-1]["sector"] == "ULAŞTIRMA VE DEPOLAMA"


# --- loader + search --------------------------------------------------------


def _write_doc(path, companies):
    path.write_text(json.dumps({"metadata": {}, "companies": companies}, ensure_ascii=False), encoding="utf-8")


def test_load_company_list_handles_missing_and_invalid_files(tmp_path):
    assert load_company_list(tmp_path / "missing.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_company_list(bad) == {}
    wrong = tmp_path / "wrong.json"
    wrong.write_text('{"companies": "nope"}', encoding="utf-8")
    assert load_company_list(wrong) == {}


def test_search_uses_static_index_when_json_absent():
    # tests/conftest.py points BIST_COMPANIES_PATH at a missing file.
    assert ticker_index.get_ticker_index() == ticker_index.TICKER_INDEX
    assert search_tickers("THY")[0]["ticker"] == "THYAO"
    assert search_tickers("ACSEL") == []


def test_search_merges_json_list_with_static_names_winning(tmp_path, monkeypatch):
    path = tmp_path / "bist_companies.json"
    _write_doc(
        path,
        [
            {"ticker": "ACSEL", "name": "ACISELSAN ACIPAYAM SELÜLOZ SANAYİ VE TİCARET A.Ş.", "sector": None},
            {"ticker": "THYAO", "name": "TÜRK HAVA YOLLARI A.O.", "sector": "ULAŞTIRMA VE DEPOLAMA"},
            {"ticker": "", "name": "kodsuz"},
            "junk",
        ],
    )
    monkeypatch.setattr(ticker_index, "BIST_COMPANIES_PATH", path)
    ticker_index.get_ticker_index.cache_clear()

    index = ticker_index.get_ticker_index()

    assert index["ACSEL"].startswith("ACISELSAN")
    assert index["THYAO"] == "Türk Hava Yolları A.O."  # curated static name kept
    assert set(ticker_index.TICKER_INDEX) <= set(index)
    assert search_tickers("acsel")[0]["ticker"] == "ACSEL"
    # Turkish-aware name matching: "selüloz"/"seluloz" both find KAP's upper-case "SELÜLOZ".
    assert any(r["ticker"] == "ACSEL" for r in search_tickers("seluloz"))
    assert any(r["ticker"] == "ACSEL" for r in search_tickers("selüloz"))


def test_search_ranks_ticker_prefix_before_name_matches_and_respects_limit():
    index = {"ISCTR": "Türkiye İş Bankası A.Ş.", "ABCDE": "İskenderun Örnek A.Ş.", "ISMEN": "İş Yatırım"}
    results = search_tickers("is", limit=2, index=index)
    assert [r["ticker"] for r in results] == ["ISCTR", "ISMEN"]
    assert [r["ticker"] for r in search_tickers("iskenderun", index=index)] == ["ABCDE"]
    assert search_tickers("   ", index=index) == []
