"""Alacak/stok kanonik alanlarının yfinance eşlemesi (ADR-016)."""

from __future__ import annotations

from yfinance.const import fundamentals_keys
from yfinance.utils import camel2title

from app.models.enums import CanonicalField
from app.providers.financial.yfinance_mapping import BALANCE_SHEET_MAP, extract


def test_yfinance_maps_receivables_and_inventory_with_real_labels():
    # Etiketler yfinance'in kendi bilanço anahtar listesinde olmalı (ağ gerekmez).
    known = set(camel2title(fundamentals_keys["balance-sheet"]))
    for field in (CanonicalField.RECEIVABLES, CanonicalField.INVENTORY):
        assert all(label in known for label in BALANCE_SHEET_MAP[field]), field

    column = {"Receivables": 120.0, "Inventory": 80.0}
    result = extract(BALANCE_SHEET_MAP, ["Receivables", "Inventory"], column)
    assert result["RECEIVABLES"] == 120.0  # "Accounts Receivable" yoksa toplam alacağa düşer
    assert result["INVENTORY"] == 80.0
