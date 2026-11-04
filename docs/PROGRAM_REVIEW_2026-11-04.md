# First registered-program review — 2026-11-04

The implementation passed **24 tests** in GitHub Actions (12 library warnings). The first
registered historical program completed successfully with macro experiments explicitly
blocked because the FRED credential was absent when the workflow was queued.

- [Workflow and full logs](https://github.com/PrototypeVersions/UnpricedZ/actions/runs/41752606082)
- [Immutable report](../archive/program/program-0.1.0/41752606082-1/report.json)
- [Selection audit](../archive/program/program-0.1.0/41752606082-1/selection-audit.json)
- [Registered protocol](RESEARCH_PROGRAM.md)

These are development results, not fresh confirmation or prospective performance. The
official algorithm hash and first live forecast blob remained identical after this run.

## Monthly versus quarterly: same 1,510 dates, 13,590 sector forecasts

Lower loss is better. All rows cover 2019–2024 and the same nine sectors.

| Task | Monthly loss | Quarterly loss | Simple baseline |
| --- | ---: | ---: | --- |
| Beat-SPY event, Brier | 0.25096 | 0.25066 | Event frequency: approximately 0.24999 |
| Variance, QLIKE | 0.49280 | 0.50112 | EWMA: 0.41370 |
| Greater-than-3% drawdown, Brier | 0.14398 | 0.14792 | Event frequency: 0.16017 monthly / 0.16061 quarterly |

Monthly-minus-quarterly improvements (positive means monthly has lower loss):

| Task | Improvement | Descriptive 95% date-block interval |
| --- | ---: | --- |
| Relative return event | −0.00030 | −0.00126 to +0.00074 |
| Variance | +0.00832 | −0.00492 to +0.02783 |
| Drawdown event | +0.00394 | +0.00071 to +0.00868 |

More frequent refitting did not establish better directional predictions. Both variance
regressions lost to EWMA on average. The drawdown result is worth a further controlled test,
but an unconditional event-frequency baseline is weak for a volatility-dependent event.
The next drawdown protocol must include a simple volatility-only baseline and test the
incremental contribution of the other features. Do not revise this first registered result
to pretend that comparison was already performed. The intervals are descriptive, not a
multiple-testing-adjusted basis for promotion.

## Frozen Chronos: a separate 72-date diagnostic

These use only the first exchange session of each month. They cannot be compared with the
all-daily scores above without matching dates. Each row below uses identical monthly origins.

| Task | Chronos loss | Same-date simple baseline | Improvement interval versus that baseline |
| --- | ---: | ---: | --- |
| Relative return event, Brier | 0.25294 | 0.24956 | −0.01118 to +0.00448 |
| Variance, QLIKE | 0.39867 | 0.41523 | −0.02720 to +0.05966 |
| Drawdown event, Brier | 0.13591 | 0.13796 | −0.02155 to +0.02631 |

Chronos has not shown a clear improvement over the relevant simple baseline in this small
screen. Historical pretraining overlap is unverified. Its apparent point-estimate variance
advantage is a hypothesis for future frozen forecasts, not evidence that a large model has
solved market prediction. Fine-tuning is not yet justified by this result.

## Next actions

1. Configure `FRED_API_KEY` privately in UnpricedZ Actions secrets and rerun the registered
   program. Verify actual API access, archived vintage coverage and paired macro comparisons.
2. Request the independent read-only review using [the brief](CROSS_REVIEW_BRIEF.md).
3. Keep the official live record running while defining the shared forecast export contract.
4. Before a new prospective drawdown launch, register the stronger volatility-only baseline
   comparison and relevant synthetic controls. Preserve all results, including failures.
5. Add a shared evaluator only after the two labs agree on exact comparable tasks. Begin with
   a fixed ensemble if compatible forecasts exist; defer learned combination weights.
