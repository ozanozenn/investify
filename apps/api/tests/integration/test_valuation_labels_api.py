"""Refresh, değerleme kutucuk etiketlerini hüküm kartıyla aynı eşiklerle kaydeder."""

from __future__ import annotations

import pytest

from app.core.config import get_verdict_config


async def test_refresh_stores_history_labels_from_verdict_config(client):
    body = (await client.post("/api/companies/TEST/refresh")).json()
    valuation = body["valuation"]
    history = get_verdict_config()["lenses"]["history"]

    for multiple in ("pe", "pb", "ev_ebitda"):
        ratio = valuation[f"{multiple}_vs_history_ratio"]
        assert ratio is not None  # sahte veride üç çarpanın da geçmişi var
        if ratio < history["cheap_below"]:
            expected = "UCUZ"
        elif ratio > history["expensive_above"]:
            expected = "PAHALI"
        else:
            expected = "MAKUL"
        assert valuation[f"{multiple}_vs_history_label"] == expected
        assert valuation[f"{multiple}_vs_history_diff"] == pytest.approx(ratio - 1)

    # Aynı snapshot'ın GET'i de etiketleri taşır.
    stored = (await client.get("/api/companies/TEST/analysis")).json()["valuation"]
    assert stored["pe_vs_history_label"] == valuation["pe_vs_history_label"]
