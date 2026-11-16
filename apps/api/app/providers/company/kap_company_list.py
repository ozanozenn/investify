"""Parsing for KAP's listed-company list and sector page — used by
`scripts/import_bist_companies.py` to (re)generate `bist_companies.json`,
the data file behind `/companies/search` autocomplete (ADR-015).

Pure functions only; the script does the (two) HTTP requests. Sources, as
used by open-source clients (borsapy `_providers/kap.py`, borsa-mcp
`providers/kap_provider.py`, bistmas `data/clients/kap.py`, QuaxisLabs
`src/fetchers/kap.py`) — unofficial but public, no authentication:

- `GET https://www.kap.org.tr/tr/api/company/generic/excel/IGS/A` — the
  "BIST Şirketleri" list as an Excel (xlsx) file: a header row starting
  with "BIST KODU", then the company title and city (and auditor). A code
  cell may hold several comma-separated codes ("KRDMA, KRDMB, KRDMD").
- `GET https://www.kap.org.tr/tr/Sektorler` — a Next.js page; each company
  is embedded in the React Flight payload (inside
  `self.__next_f.push([1,"..."])` string literals) as
  `{"sectorName": ..., "sectorOid": ..., "stockCode": "...", "title": ..., "kapTypes": [...]}`
  (companies directly under a main sector use `mainSectorName`).

Not live-verified from the build environment (kap.org.tr unreachable); the
parsers accept the shapes those clients document and fail loudly otherwise.
Codes are kept exactly as KAP lists them — never invented or "corrected".
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree

KAP_COMPANY_LIST_URL = "https://www.kap.org.tr/tr/api/company/generic/excel/IGS/A"
KAP_SECTORS_URL = "https://www.kap.org.tr/tr/Sektorler"

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")
_FOLD = str.maketrans(
    {"İ": "I", "ı": "I", "i": "I", "Ş": "S", "ş": "S", "Ğ": "G", "ğ": "G",
     "Ü": "U", "ü": "U", "Ö": "O", "ö": "O", "Ç": "C", "ç": "C"}
)


class CompanyListParseError(ValueError):
    pass


def fold(text: str) -> str:
    """Turkish-aware, accent-insensitive upper case for matching ("Şehir" -> "SEHIR")."""
    return text.translate(_FOLD).upper()


def split_codes(cell: str) -> list[str]:
    codes = [c.strip().upper() for c in re.split(r"[,;\s]+", cell or "") if c.strip()]
    return [c for c in codes if _CODE_RE.match(c)]


# --- Excel (xlsx) without third-party dependencies ---------------------------


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return max(index - 1, 0)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _string_item_text(element) -> str:
    """Text of a shared-string item / inline string: its `t`, or its rich-text
    runs' `t`s (phonetic `rPh` hints are skipped)."""
    if element is None:
        return ""
    parts: list[str] = []
    for child in element:
        if _local(child.tag) == "t":
            parts.append(child.text or "")
        elif _local(child.tag) == "r":
            parts.extend(t.text or "" for t in child if _local(t.tag) == "t")
    return "".join(parts)


def read_xlsx_rows(data: bytes) -> list[list[str]]:
    """First worksheet of an xlsx file as a list of string rows."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise CompanyListParseError("not an xlsx (zip) file") from exc
    with archive:
        names = archive.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [_string_item_text(si) for si in root.findall("{*}si")]
        sheets = sorted(
            (n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)),
        )
        if not sheets:
            raise CompanyListParseError("xlsx has no worksheet")
        root = ElementTree.fromstring(archive.read(sheets[0]))
    rows: list[list[str]] = []
    for row in root.iterfind(".//{*}row"):
        cells: dict[int, str] = {}
        for position, cell in enumerate(row.findall("{*}c")):
            ref = cell.get("r")
            col = _column_index(ref) if ref else position
            kind = cell.get("t")
            if kind == "inlineStr":
                value = _string_item_text(cell.find("{*}is"))
            else:
                v = cell.find("{*}v")
                value = v.text if v is not None and v.text is not None else ""
                if kind == "s" and value.strip().isdigit() and int(value) < len(shared):
                    value = shared[int(value)]
            cells[col] = value.strip()
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def read_html_table_rows(text: str) -> list[list[str]]:
    parser = _TableParser()
    parser.feed(text)
    return parser.rows


def parse_company_rows(rows: list[list[str]]) -> list[dict]:
    """Rows -> [{"ticker", "name", "city"}], one record per listed code.
    Uses the "BIST KODU" header row when present; otherwise the column
    order the clients rely on (code, title, city)."""
    code_col, name_col, city_col, start = 0, 1, 2, 0
    for i, row in enumerate(rows):
        folded = [fold(c) for c in row]
        if any(c.replace(" ", "") == "BISTKODU" for c in folded):
            code_col = next(j for j, c in enumerate(folded) if c.replace(" ", "") == "BISTKODU")
            name_col = next((j for j, c in enumerate(folded) if "UNVAN" in c), code_col + 1)
            city_col = next((j for j, c in enumerate(folded) if "SEHIR" in c), None)
            start = i + 1
            break
    out: list[dict] = []
    seen: set[str] = set()
    for row in rows[start:]:
        if len(row) <= max(code_col, name_col):
            continue
        name = " ".join(row[name_col].split())
        if not name:
            continue
        city = row[city_col].strip() if city_col is not None and city_col < len(row) else ""
        for code in split_codes(row[code_col]):
            if code in seen:
                continue
            seen.add(code)
            out.append({"ticker": code, "name": name, "city": city or None})
    return out


def parse_company_list(data: bytes) -> list[dict]:
    """KAP company-list download (xlsx, or an HTML table export) -> records."""
    if data[:2] == b"PK":
        rows = read_xlsx_rows(data)
    elif b"<table" in data[:200_000].lower():
        rows = read_html_table_rows(data.decode("utf-8", errors="replace"))
    else:
        raise CompanyListParseError(
            f"unrecognised company-list format (first bytes: {data[:8]!r}); "
            "download it in a browser and pass it with --from-file"
        )
    companies = parse_company_rows(rows)
    if not companies:
        raise CompanyListParseError("no company rows found (layout changed?)")
    return companies


# --- KAP "Sektörler" page (Next.js React Flight payload) ----------------------

_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[\s*1\s*,\s*"((?:[^"\\]|\\.)*)"\s*\]\)', re.S)
_SECTOR_OBJ_RE = re.compile(r'\{"(sectorName|mainSectorName)"\s*:')


def decode_next_flight(html: str) -> str:
    parts: list[str] = []
    for match in _PUSH_RE.finditer(html):
        try:
            parts.append(json.loads(f'"{match.group(1)}"'))
        except json.JSONDecodeError:
            continue
    return "".join(parts)


def parse_sector_page(html: str) -> dict[str, str]:
    """{ticker: KAP sector name}. Sub-sector names win over main-sector names."""
    decoder = json.JSONDecoder()
    main: dict[str, str] = {}
    sub: dict[str, str] = {}
    for text in (decode_next_flight(html), html):
        for match in _SECTOR_OBJ_RE.finditer(text):
            try:
                obj, _ = decoder.raw_decode(text, match.start())
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            key = match.group(1)
            sector = obj.get(key)
            if not isinstance(sector, str) or not sector.strip():
                continue
            target = sub if key == "sectorName" else main
            for code in split_codes(str(obj.get("stockCode") or "")):
                target.setdefault(code, " ".join(sector.split()))
    return {**main, **sub}


def build_document(
    companies: list[dict],
    sectors: dict[str, str] | None,
    *,
    fetched_at: dt.datetime,
    source_urls: list[str],
) -> dict:
    records = [
        {
            "ticker": c["ticker"],
            "name": c["name"],
            "sector": (sectors or {}).get(c["ticker"]),
            "city": c.get("city"),
        }
        for c in sorted(companies, key=lambda c: c["ticker"])
    ]
    return {
        "metadata": {
            "source": "KAP (Kamuyu Aydınlatma Platformu) — BIST şirketleri listesi"
            + (" ve Sektörler sayfası" if sectors else ""),
            "source_urls": source_urls,
            "fetched_at": fetched_at.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "apps/api/scripts/import_bist_companies.py",
            "company_count": len(records),
            "with_sector": sum(1 for r in records if r["sector"]),
            "note": "Kodlar ve unvanlar KAP'ın listelediği gibidir; elle eklenmiş kayıt yoktur.",
        },
        "companies": records,
    }
