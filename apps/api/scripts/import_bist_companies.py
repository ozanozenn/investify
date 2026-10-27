"""KAP'tan tam BIST şirket listesini çekip `bist_companies.json` yazar (ADR-015).

`/companies/search` otomatik tamamlaması bu dosya varsa ~500+ şirketin
tamamını önerir (`app/providers/company/ticker_index.py`); yoksa elle
tutulan ~60 kodluk statik dizine düşer. Dosya depoya commit edilir; kaynak
URL'leri ve çekim tarihi dosyanın `metadata` alanına yazılır.

İnternet erişimi olan bir makinede:

    cd apps/api
    .venv/bin/python scripts/import_bist_companies.py            # liste + sektörler
    .venv/bin/python scripts/import_bist_companies.py --no-sectors
    .venv/bin/python scripts/import_bist_companies.py --dry-run  # yazmadan özet

KAP betik isteğini engellerse dosyaları tarayıcıdan indirip verin:

    .venv/bin/python scripts/import_bist_companies.py \\
        --from-file ~/Downloads/sirketler.xlsx --sectors-from-file ~/Downloads/Sektorler.html

Kaynaklar (resmî olmayan ama herkese açık, kimlik doğrulamasız; borsapy ve
borsa-mcp de aynı uç noktaları kullanıyor):
  - https://www.kap.org.tr/tr/api/company/generic/excel/IGS/A  (kod, unvan, şehir)
  - https://www.kap.org.tr/tr/Sektorler                       (sektör; isteğe bağlı)

Liste `--min-count` (varsayılan 300) kayıttan kısaysa dosya yazılmaz:
yarım bir liste, statik dizinden daha kötüdür.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import httpx

from app.providers.company.kap_company_list import (
    KAP_COMPANY_LIST_URL,
    KAP_SECTORS_URL,
    CompanyListParseError,
    build_document,
    parse_company_list,
    parse_sector_page,
)
from app.providers.company.ticker_index import BIST_COMPANIES_PATH

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; InvestifyBot/0.1; +personal-research-use)",
    "Accept": "*/*",
    "Accept-Language": "tr",
    "Referer": "https://www.kap.org.tr/tr/bist-sirketler",
}


def _get(url: str) -> httpx.Response:
    response = httpx.get(url, headers=_HEADERS, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=BIST_COMPANIES_PATH)
    parser.add_argument("--from-file", type=Path, help="tarayıcıdan indirilmiş KAP şirket listesi (xlsx)")
    parser.add_argument("--sectors-from-file", type=Path, help="tarayıcıdan kaydedilmiş Sektorler sayfası (html)")
    parser.add_argument("--no-sectors", action="store_true", help="sektör sayfasını hiç çekme")
    parser.add_argument("--min-count", type=int, default=300)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    fetched_at = dt.datetime.now(dt.timezone.utc)
    source_urls: list[str] = []
    try:
        if args.from_file:
            data = args.from_file.read_bytes()
            source_urls.append(f"{KAP_COMPANY_LIST_URL} (elle indirildi: {args.from_file.name})")
        else:
            data = _get(KAP_COMPANY_LIST_URL).content
            source_urls.append(KAP_COMPANY_LIST_URL)
        companies = parse_company_list(data)
    except (httpx.HTTPError, OSError, CompanyListParseError) as exc:
        print(f"HATA: şirket listesi alınamadı: {exc}", file=sys.stderr)
        return 1

    sectors: dict[str, str] | None = None
    if not args.no_sectors:
        try:
            if args.sectors_from_file:
                html = args.sectors_from_file.read_text(encoding="utf-8", errors="replace")
                source_urls.append(f"{KAP_SECTORS_URL} (elle kaydedildi: {args.sectors_from_file.name})")
            else:
                time.sleep(0.5)  # KAP'a nazik ol (ADR-002)
                html = _get(KAP_SECTORS_URL).text
                source_urls.append(KAP_SECTORS_URL)
            sectors = parse_sector_page(html) or None
            if not sectors:
                print("UYARI: sektör sayfasından şirket ayrıştırılamadı; sektörsüz devam.", file=sys.stderr)
        except (httpx.HTTPError, OSError) as exc:
            print(f"UYARI: sektörler alınamadı ({exc}); sektörsüz devam.", file=sys.stderr)

    document = build_document(companies, sectors, fetched_at=fetched_at, source_urls=source_urls)
    meta = document["metadata"]
    print(f"{meta['company_count']} kod, {meta['with_sector']} tanesi sektörlü ({meta['fetched_at']}).")
    if meta["company_count"] < args.min_count:
        print(
            f"HATA: liste beklenenden kısa (< {args.min_count}); dosya yazılmadı. "
            "Biçim değişmiş olabilir — --dry-run ile inceleyin.",
            file=sys.stderr,
        )
        return 1
    if args.dry_run:
        for record in document["companies"][:10]:
            print(f"  {record['ticker']:<8} {record['name']}  [{record['sector'] or '-'}]")
        return 0
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Yazıldı: {args.output}")
    print("Commit etmeyi unutmayın; kaynak ve tarih metadata'da kayıtlı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
