"""Kalite bayrakları motoru (ADR-016, MAIN_ROADMAP.md §72).

"Gelir artıyor ama nakit akışı bozuluyor" gibi kural tabanlı uyarıları
yıllık finansal dönemlerden üretir. Saf fonksiyon — I/O yapmaz, LLM'e
dokunmaz; eşikler `config/quality_flags.yaml`'dan çağıran tarafından verilir.

Her kontrolün üç olası sonucu vardır:
- tetiklendi -> `QualityFlag` (önem, Türkçe başlık/açıklama, ham sayılar)
- temiz -> adı `passed_checks`'e yazılır
- değerlendirilemedi -> `not_evaluated` + `missing_fields`; eksik girdi
  asla tahmin edilmez, sıfır/negatif tabandan anlamsız büyüme üretilmez.

Yüksek enflasyonda nominal büyümeler şiştiği için iki kalemin büyümesi
yüzde puan farkıyla değil göreli farkla karşılaştırılır:
(1 + a_büyüme) / (1 + b_büyüme) - 1 = (a_t / a_t-1) / (b_t / b_t-1) - 1.
Enflasyon iki tarafta da olduğu için birbirini götürür.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.financial_engine import formulas as f
from app.models.enums import CanonicalField as CF
from app.schemas.financial import PeriodData
from app.schemas.quality import (
    QualityFlag,
    QualityFlagsResult,
    QualityFlagValue,
    QualitySeverity,
    UnevaluatedQualityCheck,
)

_FIELD_LABELS: dict[CF, str] = {
    CF.REVENUE: "Hasılat",
    CF.EBITDA: "FAVÖK",
    CF.NET_INCOME: "Net kâr",
    CF.TOTAL_DEBT: "Toplam borç",
    CF.EQUITY: "Özkaynak",
    CF.OPERATING_CASH_FLOW: "Faaliyet nakit akışı",
    CF.FREE_CASH_FLOW: "Serbest nakit akışı",
    CF.RECEIVABLES: "Ticari alacaklar",
    CF.INVENTORY: "Stoklar",
}

_NUMBER_WORDS = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş"}

_SEVERITY_ORDER: dict[str, int] = {"UYARI": 0, "DIKKAT": 1, "OLUMLU": 2}


@dataclass(frozen=True)
class _Missing:
    missing_fields: list[str]
    reason: str


_Outcome = QualityFlag | _Missing | None


def _get(period: PeriodData, field: CF) -> float | None:
    return period.values.get(field.value)


def _fcf(period: PeriodData) -> float | None:
    # financial_engine.engine ile aynı kural: sağlayıcının FCF'si, yoksa OCF - |CAPEX|.
    explicit = _get(period, CF.FREE_CASH_FLOW)
    if explicit is not None:
        return explicit
    return f.free_cash_flow(_get(period, CF.OPERATING_CASH_FLOW), _get(period, CF.CAPEX))


def _ratio(key: str, label: str, value: float) -> QualityFlagValue:
    return QualityFlagValue(key=key, label=label, value=value, unit="ratio")


def _currency(key: str, label: str, value: float) -> QualityFlagValue:
    return QualityFlagValue(key=key, label=label, value=value, unit="currency")


def _no_previous() -> _Missing:
    return _Missing(["previous_period"], "Önceki yıl verisi yok; yıllık karşılaştırma yapılamıyor.")


def _non_positive_base(field: CF) -> _Missing:
    return _Missing(
        [f"non_positive_base:{field.value}"],
        f"{_FIELD_LABELS[field]} önceki yılda sıfır veya negatif; büyüme karşılaştırması anlamlı değil.",
    )


def _pairs(
    latest: PeriodData, previous: PeriodData | None, fields: list[CF]
) -> dict[CF, tuple[float, float]] | _Missing:
    """(son yıl, önceki yıl) değer çiftleri ya da eksik alanlar."""
    if previous is None:
        return _no_previous()
    missing = [fld for fld in fields if _get(latest, fld) is None or _get(previous, fld) is None]
    if missing:
        return _Missing(
            [fld.value for fld in missing],
            "Gerekli veri eksik: " + ", ".join(_FIELD_LABELS[fld] for fld in missing) + ".",
        )
    return {fld: (_get(latest, fld), _get(previous, fld)) for fld in fields}


def _flag(key: str, severity: QualitySeverity, title: str, detail: str, values: list[QualityFlagValue]) -> QualityFlag:
    return QualityFlag(key=key, severity=severity, title=title, detail=detail, values=values)


# --- Kontroller --------------------------------------------------------------


def _check_revenue_vs_cash(periods: list[PeriodData], cfg: dict) -> _Outcome:
    latest, previous = periods[-1], (periods[-2] if len(periods) >= 2 else None)
    data = _pairs(latest, previous, [CF.REVENUE, CF.OPERATING_CASH_FLOW])
    if isinstance(data, _Missing):
        return data
    revenue_growth = f.growth_rate(*data[CF.REVENUE])
    # growth_rate |önceki| ile böler: negatif tabanda da "kötüleşme" negatif çıkar.
    ocf_growth = f.growth_rate(*data[CF.OPERATING_CASH_FLOW])
    if revenue_growth is None:
        return _non_positive_base(CF.REVENUE)
    if ocf_growth is None:
        return _non_positive_base(CF.OPERATING_CASH_FLOW)
    c = cfg["revenue_vs_cash"]
    if revenue_growth > c["min_revenue_growth"] and ocf_growth <= c["max_ocf_growth"]:
        return _flag(
            "revenue_vs_cash",
            "UYARI",
            "Gelir artıyor ama nakit akışı bozuluyor",
            "Satışlar bir önceki yıla göre artarken şirketin faaliyetlerinden elde ettiği nakit belirgin "
            "şekilde azaldı. Satışlar tahsilata dönüşmüyor ya da işletme sermayesi ihtiyacı büyüyor "
            "olabilir; nakit akış tablosuna bakmakta fayda var.",
            [
                _ratio("revenue_growth_yoy", "Gelir büyümesi (yıllık)", revenue_growth),
                _ratio("ocf_growth_yoy", "Faaliyet nakit akışı değişimi (yıllık)", ocf_growth),
            ],
        )
    return None


def _check_earnings_vs_cash(periods: list[PeriodData], cfg: dict) -> _Outcome:
    latest, previous = periods[-1], (periods[-2] if len(periods) >= 2 else None)
    data = _pairs(latest, previous, [CF.NET_INCOME, CF.OPERATING_CASH_FLOW])
    if isinstance(data, _Missing):
        return data
    ni_cur, ni_prev = data[CF.NET_INCOME]
    ocf_cur, ocf_prev = data[CF.OPERATING_CASH_FLOW]
    if ni_cur <= ni_prev:
        return None  # kâr büyümüyor; bu kontrolün konusu değil
    if ni_prev <= 0:
        return _non_positive_base(CF.NET_INCOME)
    if ocf_prev <= 0:
        return _non_positive_base(CF.OPERATING_CASH_FLOW)
    ni_growth = ni_cur / ni_prev - 1
    ocf_growth = ocf_cur / ocf_prev - 1
    values = [
        _ratio("net_income_growth_yoy", "Net kâr büyümesi (yıllık)", ni_growth),
        _ratio("ocf_growth_yoy", "Faaliyet nakit akışı değişimi (yıllık)", ocf_growth),
    ]
    title = "Kâr, nakit akışından çok daha hızlı büyüyor"
    if ocf_cur <= 0:
        return _flag(
            "earnings_vs_cash",
            "DIKKAT",
            title,
            "Net kâr artarken faaliyetlerden elde edilen nakit sıfırın altına indi. Kâğıt üzerindeki "
            "kâr nakde dönmüyor; kârın kalitesi sorgulanmalı.",
            values,
        )
    gap = (ni_cur / ni_prev) / (ocf_cur / ocf_prev) - 1
    if gap >= cfg["earnings_vs_cash"]["min_relative_gap"]:
        return _flag(
            "earnings_vs_cash",
            "DIKKAT",
            title,
            "Net kâr, faaliyetlerden elde edilen nakitten belirgin şekilde daha hızlı arttı. Kârın bir "
            "kısmı henüz nakde dönmemiş (tahakkuk) olabilir; kârın kalitesi açısından dikkat edilmeli.",
            values,
        )
    return None


def _margin_check(
    key: str, numerator: CF, name: str, plain_name: str, threshold_key: str
) -> Callable[[list[PeriodData], dict], _Outcome]:
    def check(periods: list[PeriodData], cfg: dict) -> _Outcome:
        if len(periods) < 2:
            return _no_previous()
        latest, previous = periods[-1], periods[-2]
        data = _pairs(latest, previous, [CF.REVENUE, numerator])
        if isinstance(data, _Missing):
            return data
        rev_cur, rev_prev = data[CF.REVENUE]
        num_cur, num_prev = data[numerator]
        if rev_cur <= 0 or rev_prev <= 0:
            return _Missing([f"non_positive:{CF.REVENUE.value}"], "Hasılat sıfır veya negatif; marj hesaplanamıyor.")
        margin_cur, margin_prev = num_cur / rev_cur, num_prev / rev_prev
        delta = margin_cur - margin_prev
        points = cfg["margin_trend"][threshold_key]
        values = [
            _ratio(f"{key}_previous", f"{name} ({previous.fiscal_year})", margin_prev),
            _ratio(f"{key}_latest", f"{name} ({latest.fiscal_year})", margin_cur),
        ]
        if delta <= -points:
            return _flag(
                key,
                "DIKKAT",
                f"{name} daralıyor",
                f"Şirketin {plain_name} bir önceki yıla göre belirgin şekilde geriledi. Maliyetler satış "
                "fiyatlarından hızlı artıyor ya da fiyatlama gücü zayıflıyor olabilir.",
                values,
            )
        if delta >= points:
            return _flag(
                key,
                "OLUMLU",
                f"{name} genişliyor",
                f"Şirketin {plain_name} bir önceki yıla göre belirgin şekilde iyileşti; satışlarından "
                "kâra kalan pay arttı.",
                values,
            )
        return None

    return check


def _check_debt_vs_ebitda(periods: list[PeriodData], cfg: dict) -> _Outcome:
    latest, previous = periods[-1], (periods[-2] if len(periods) >= 2 else None)
    data = _pairs(latest, previous, [CF.TOTAL_DEBT, CF.EBITDA])
    if isinstance(data, _Missing):
        return data
    debt_cur, debt_prev = data[CF.TOTAL_DEBT]
    ebitda_cur, ebitda_prev = data[CF.EBITDA]
    if debt_cur <= debt_prev:
        return None  # borç artmıyor
    if debt_prev <= 0:
        return _non_positive_base(CF.TOTAL_DEBT)
    if ebitda_prev <= 0:
        return _non_positive_base(CF.EBITDA)
    debt_growth = debt_cur / debt_prev - 1
    ebitda_growth = ebitda_cur / ebitda_prev - 1
    values = [
        _ratio("total_debt_growth_yoy", "Toplam borç büyümesi (yıllık)", debt_growth),
        _ratio("ebitda_growth_yoy", "FAVÖK büyümesi (yıllık)", ebitda_growth),
    ]
    title = "Borç, FAVÖK'ten hızlı artıyor"
    if ebitda_cur <= 0:
        return _flag(
            "debt_vs_ebitda",
            "UYARI",
            title,
            "Toplam borç artarken faaliyet kârı (FAVÖK) sıfırın altına indi; borcu faaliyet kârıyla "
            "taşıma kapasitesi ciddi şekilde zayıfladı.",
            values,
        )
    gap = (debt_cur / debt_prev) / (ebitda_cur / ebitda_prev) - 1
    if gap >= cfg["debt_vs_ebitda"]["min_relative_gap"]:
        return _flag(
            "debt_vs_ebitda",
            "UYARI",
            title,
            "Toplam borç, faaliyet kârından (FAVÖK) belirgin şekilde daha hızlı büyüdü. Borcu faaliyet "
            "kârıyla taşıma kapasitesi zayıflıyor olabilir.",
            values,
        )
    return None


def _check_negative_fcf_streak(periods: list[PeriodData], cfg: dict) -> _Outcome:
    years = int(cfg["negative_fcf_streak"]["years"])
    years_word = _NUMBER_WORDS.get(years, str(years))
    if len(periods) < years:
        return _Missing(["previous_period"], f"En az {years_word} yıllık veri gerekiyor.")
    window = periods[-years:]
    fcf_values = [_fcf(p) for p in window]
    if any(v is None for v in fcf_values):
        return _Missing(
            [CF.FREE_CASH_FLOW.value],
            f"Son {years_word} yılın serbest nakit akışı (veya faaliyet nakit akışı ve yatırım harcaması) eksik.",
        )
    fcfs = [v for v in fcf_values if v is not None]
    if all(v < 0 for v in fcfs):
        return _flag(
            "negative_fcf_streak",
            "UYARI",
            "Serbest nakit akışı art arda negatif",
            f"Şirket son {years_word} yılın hepsinde yatırım harcamalarından sonra nakit tüketti. "
            "Faaliyetlerini ve büyümesini borçla veya sermaye artırımıyla finanse ediyor olabilir.",
            [
                _currency(f"free_cash_flow_{p.fiscal_year}", f"Serbest nakit akışı ({p.fiscal_year})", v)
                for p, v in zip(window, fcfs, strict=True)
            ],
        )
    return None


def _check_equity_trend(periods: list[PeriodData], cfg: dict) -> _Outcome:
    latest, previous = periods[-1], (periods[-2] if len(periods) >= 2 else None)
    eq_cur = _get(latest, CF.EQUITY)
    if eq_cur is None:
        return _Missing([CF.EQUITY.value], "Gerekli veri eksik: Özkaynak.")
    if eq_cur <= 0:
        return _flag(
            "equity_trend",
            "UYARI",
            "Özkaynak negatif",
            "Şirketin borçları varlıklarını aşmış durumda; özkaynak sıfırın altında. Bu, finansal "
            "dayanıklılık açısından ciddi bir uyarıdır.",
            [_currency("equity_latest", f"Özkaynak ({latest.fiscal_year})", eq_cur)],
        )
    if previous is None:
        return _no_previous()
    data = _pairs(latest, previous, [CF.EQUITY])
    if isinstance(data, _Missing):
        return data
    eq_prev = data[CF.EQUITY][1]
    if eq_prev <= 0:
        return None  # negatiften pozitife dönmüş: erime yok
    eq_growth = eq_cur / eq_prev - 1
    if eq_growth <= cfg["equity_trend"]["max_equity_growth"]:
        return _flag(
            "equity_trend",
            "DIKKAT",
            "Özkaynak eriyor",
            "Şirketin özkaynağı bir önceki yıla göre belirgin şekilde azaldı. Zarar, yüksek temettü "
            "dağıtımı veya kur farkı kayıpları sermayeyi aşındırıyor olabilir.",
            [
                _currency("equity_previous", f"Özkaynak ({previous.fiscal_year})", eq_prev),
                _currency("equity_latest", f"Özkaynak ({latest.fiscal_year})", eq_cur),
                _ratio("equity_growth_yoy", "Özkaynak değişimi (yıllık)", eq_growth),
            ],
        )
    return None


def _working_capital_check(
    key: str, field: CF, threshold_key: str, title: str, growth_label: str, consequence: str
) -> Callable[[list[PeriodData], dict], _Outcome]:
    label = _FIELD_LABELS[field]

    def check(periods: list[PeriodData], cfg: dict) -> _Outcome:
        latest, previous = periods[-1], (periods[-2] if len(periods) >= 2 else None)
        data = _pairs(latest, previous, [field, CF.REVENUE])
        if isinstance(data, _Missing):
            return data
        wc_cur, wc_prev = data[field]
        rev_cur, rev_prev = data[CF.REVENUE]
        if wc_prev <= 0:
            return _non_positive_base(field)
        if rev_prev <= 0:
            return _non_positive_base(CF.REVENUE)
        wc_growth = wc_cur / wc_prev - 1
        rev_growth = rev_cur / rev_prev - 1
        if rev_cur <= 0:
            # Gelir sıfırlandı: göreli fark tanımsız, ama kalem bilançoda duruyorsa bayrak.
            triggered = wc_cur > 0
            movement = f"Gelir sıfıra indiği hâlde {label.lower()} bilançoda duruyor."
        else:
            gap = (wc_cur / wc_prev) / (rev_cur / rev_prev) - 1
            triggered = gap >= cfg["working_capital_vs_revenue"][threshold_key]
            movement = (
                f"{label} gelirden belirgin şekilde daha hızlı arttı."
                if wc_growth > 0
                else f"Gelir, {label.lower()} kaleminden belirgin şekilde daha hızlı geriledi; "
                f"{label.lower()} satışlara oranla şişti."
            )
        if not triggered:
            return None
        return _flag(
            key,
            "DIKKAT",
            title,
            f"{movement} {consequence}",
            [
                _ratio(f"{field.value.lower()}_growth_yoy", growth_label, wc_growth),
                _ratio("revenue_growth_yoy", "Gelir büyümesi (yıllık)", rev_growth),
            ],
        )

    return check


_CHECKS: list[tuple[str, str, Callable[[list[PeriodData], dict], _Outcome]]] = [
    ("revenue_vs_cash", "Gelir ile faaliyet nakit akışı uyumu", _check_revenue_vs_cash),
    ("earnings_vs_cash", "Kârın nakitle desteklenmesi (tahakkuk kalitesi)", _check_earnings_vs_cash),
    (
        "ebitda_margin_trend",
        "FAVÖK marjı eğilimi",
        _margin_check(
            "ebitda_margin_trend",
            CF.EBITDA,
            "FAVÖK marjı",
            "faaliyet kârlılığı (FAVÖK marjı)",
            "ebitda_margin_points",
        ),
    ),
    (
        "net_margin_trend",
        "Net kâr marjı eğilimi",
        _margin_check(
            "net_margin_trend",
            CF.NET_INCOME,
            "Net kâr marjı",
            "net kârlılığı (net kâr marjı)",
            "net_margin_points",
        ),
    ),
    ("debt_vs_ebitda", "Borç ile FAVÖK büyümesi", _check_debt_vs_ebitda),
    ("negative_fcf_streak", "Serbest nakit akışı sürekliliği", _check_negative_fcf_streak),
    ("equity_trend", "Özkaynak eğilimi", _check_equity_trend),
    (
        "receivables_vs_revenue",
        "Ticari alacaklar ile gelir büyümesi",
        _working_capital_check(
            "receivables_vs_revenue",
            CF.RECEIVABLES,
            "receivables_min_relative_gap",
            "Alacaklar gelirden hızlı büyüyor",
            "Ticari alacak büyümesi (yıllık)",
            "Satışlar daha uzun vadeyle yapılıyor ya da tahsilat zorlaşıyor olabilir.",
        ),
    ),
    (
        "inventory_vs_revenue",
        "Stoklar ile gelir büyümesi",
        _working_capital_check(
            "inventory_vs_revenue",
            CF.INVENTORY,
            "inventory_min_relative_gap",
            "Stoklar gelirden hızlı büyüyor",
            "Stok büyümesi (yıllık)",
            "Talep yavaşlıyor ya da ürünler depoda bekliyor olabilir.",
        ),
    ),
]


def compute_quality_flags(annual_periods: list[PeriodData], config: dict) -> QualityFlagsResult:
    """`annual_periods` yıllık dönemler (sıra önemsiz, burada sıralanır);
    `config` = `config/quality_flags.yaml` içeriği."""
    engine_version = str(config.get("version", "v1"))
    if not annual_periods:
        return QualityFlagsResult(engine_version=engine_version, missing_fields=["no_financial_periods"])

    periods = sorted(annual_periods, key=lambda p: p.fiscal_year)
    flags: list[QualityFlag] = []
    passed: list[str] = []
    not_evaluated: list[UnevaluatedQualityCheck] = []
    for key, name, check in _CHECKS:
        outcome = check(periods, config)
        if isinstance(outcome, QualityFlag):
            flags.append(outcome)
        elif isinstance(outcome, _Missing):
            not_evaluated.append(
                UnevaluatedQualityCheck(key=key, name=name, reason=outcome.reason, missing_fields=outcome.missing_fields)
            )
        else:
            passed.append(name)

    flags.sort(key=lambda fl: _SEVERITY_ORDER[fl.severity])  # sort stabil: kontrol sırası korunur
    missing: list[str] = []
    for item in not_evaluated:
        missing += [m for m in item.missing_fields if m not in missing]
    return QualityFlagsResult(
        as_of_period=str(periods[-1].fiscal_year),
        engine_version=engine_version,
        flags=flags,
        passed_checks=passed,
        not_evaluated=not_evaluated,
        missing_fields=missing,
    )
