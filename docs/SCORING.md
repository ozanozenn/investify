# Scoring Engine

Implementation: `apps/api/app/scoring_engine/engine.py`, definition:
`apps/api/config/scoring.yaml`. See that file's header comment for the
exact interpolation/rescale contract — this document explains the *why*.

## Design

Every category score (Growth, Profitability, Balance Sheet, Cash Flow,
Valuation) is a weighted sum of 2-4 "components", each mapping one metric
value to points via **piecewise-linear interpolation** over breakpoints
defined in YAML — not code. This satisfies roadmap section 60/3.9: no
magic numbers scattered in code, and every score is explainable as
`Score → [ {metric, value, points, reason}, ... ]` (matching the roadmap's
own example format exactly).

```
Growth Score = 76

Revenue CAGR     +22   (breakpoints: config/scoring.yaml → categories.growth.components)
EBITDA Growth    +18
Net Income Growth +16
Consistency      +10
```

## Missing-data handling

If a component's required metric is `None` (e.g. no historical valuation
median because fewer than 2 years of data exist), that component is
**excluded**, not defaulted to 0 or to a guessed midpoint. The category
score is then rescaled: `score = (sum of earned points / sum of max points
of the AVAILABLE components) × 100`. This means a company scores out of
"what could be evaluated," which is more honest than silently penalizing
it for a data gap — the exclusion itself is visible in
`CategoryScore.components[i].reason == "excluded: required data
unavailable"`.

## Overall score

`Overall = Σ (category_score × weight)`, weights in
`config/scoring.yaml:overall_weights` (Growth 25%, Profitability 20%,
Balance Sheet 20%, Cash Flow 15%, Valuation 20% — a starting point, not a
claimed-optimal weighting; tunable without a code change).

## Unsupported industries

Banks/insurers/REITs/holdings (`Company.is_financial_industry`) get
`scoring_engine.unsupported_score_result()`: all category scores are 0
with an empty component list and `unsupported_reason` set, rather than a
misleading generic score. See `docs/FINANCIAL_ENGINE.md` "Sector-specific
formulas".

## Versioning

`ScoreResult.engine_version` is stored on every `AnalysisSnapshot`
(`Settings.scoring_engine_version`, currently `"v1"`). Bump this string
whenever a change to `scoring.yaml` or `engine.py` would produce a
different score for the same input data, so historical snapshots remain
interpretable (ADR-005).
