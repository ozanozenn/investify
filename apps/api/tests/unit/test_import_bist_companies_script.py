"""Offline end-to-end run of scripts/import_bist_companies.py with
browser-downloaded inputs (--from-file / --sectors-from-file) — the path the
owner uses if KAP blocks scripted requests. Inputs are synthetic."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from app.providers.company import ticker_index
from tests.unit.test_bist_company_list import _KAP_ROWS, _xlsx

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "import_bist_companies.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("import_bist_companies", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    xlsx = tmp_path / "sirketler.xlsx"
    xlsx.write_bytes(_xlsx(_KAP_ROWS))
    obj = {"sectorName": "ULAŞTIRMA VE DEPOLAMA", "sectorOid": "s", "stockCode": "THYAO", "title": "T", "kapTypes": []}
    sectors = tmp_path / "Sektorler.html"
    flight = json.dumps("1:" + json.dumps({"data": [{"content": [obj]}]}, ensure_ascii=False), ensure_ascii=False)
    sectors.write_text(f"<script>self.__next_f.push([1,{flight}])</script>", encoding="utf-8")
    return xlsx, sectors


def test_script_writes_document_that_search_can_load(tmp_path):
    xlsx, sectors = _inputs(tmp_path)
    output = tmp_path / "bist_companies.json"

    code = _load_script().main(
        ["--from-file", str(xlsx), "--sectors-from-file", str(sectors), "--output", str(output), "--min-count", "1"]
    )

    assert code == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["metadata"]["company_count"] == 5
    assert document["metadata"]["with_sector"] == 1
    assert any("elle indirildi" in url for url in document["metadata"]["source_urls"])
    assert ticker_index.load_company_list(output)["KRDMD"].startswith("KARDEMİR")


def test_script_refuses_to_write_a_suspiciously_short_list(tmp_path):
    xlsx, _ = _inputs(tmp_path)
    output = tmp_path / "bist_companies.json"

    code = _load_script().main(["--from-file", str(xlsx), "--no-sectors", "--output", str(output)])

    assert code == 1  # 5 < default --min-count 300
    assert not output.exists()
