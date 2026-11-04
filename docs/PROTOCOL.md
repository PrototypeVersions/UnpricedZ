# Frozen initial research protocol

Specification: research-2.0.0. Declared before the first automated result is inspected.

## Primary questions

1. Does calibrated regularized logistic improve five-session sector-relative Brier loss over an earlier-data base rate on the prespecified 2025 confirmation year?
2. Does the HAR-style daily variance model improve QLIKE over EWMA on those same decision dates?
3. Does the production pipeline show sensible null false detections and increasing detection with planted signal strength?

Raw logistic, boosted, momentum, rank IC, calibration bins, return-band coverage and paper-policy economics are secondary diagnostics. Report them all; do not choose whichever wins and call it the original primary question.

## Decisions made before evaluation

- Universe, target, features, hyperparameters and trading thresholds: config.json and models.py.
- Historical start 2010; first evaluation 2016; development through 2024; confirmation 2025.
- Models refit at each calendar-quarter boundary, and freeze within that test block.
- Five-year development window including 126 calibration dates; strict label-end purging.
- Date-block bootstrap length 20, 1,500 replicates for market results.
- Fixed seeds beginning 20261104; 12 seeds per synthetic condition; strengths 0/.08/.25.
- Prospective evidence begins only after this version publishes before target entry.
- No adaptive ensemble and no automatic promotion.

## Interpretation and future work

The code configuration is frozen before the first historical computation. A bug repair may be made with a regression test and dated explanation, preserving the old result if one was already published. Retuning because a result is disappointing constitutes a new specification. The 2025 confirmation year becomes observed after the first run and cannot be reused as an untouched test for that new specification.

No hard pass/fail statistic proves market skill. Synthetic positives test pipeline sensitivity under specified generators; simulation success does not transfer automatically to real markets. A 60- or 90-day milestone is operational, not automatic statistical sufficiency.

Future candidate research must state the economic hypothesis, information availability, comparison baseline, expected effect, intended held-out evidence and costs before evaluation. Keep an experiment registry including abandoned and failed hypotheses. Event, options, economic-network and individual-stock models are not implemented by this initial version.

## Specification registry

| ID | Status | Description |
| --- | --- | --- |
| research-2.0.0 | Initial frozen specification | Nine sector ETFs; five-session relative returns and daily variance; no adaptive ensemble |
| risk-1.0.0 | Separately registered risk benchmark version | SPY plus nine sectors; EWMA, daily HAR, GARCH(1,1), and volatility-only drawdown; independent live namespace. See [risk protocol](RISK_PROTOCOL.md). |

Do not revise this table to hide previous tested versions. Append new entries.
