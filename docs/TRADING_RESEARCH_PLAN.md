# Proposed research: using forecasts in trading decisions

**Status: proposal only — not registered, implemented, or running.** This document explains a possible next stage. It does not change either lab’s forecasts, existing portfolios, or live records.

## The question

Does a declared risk-sizing rule improve the Stock Forecasting Lab’s portfolio after costs, and do the Risk Lab’s forecasts add value beyond a simple volatility estimate?

The Stock Forecasting Lab would continue choosing stocks from its rankings. Risk estimates could inform how much to hold and how much capital to leave in cash. A ranking score and a variance forecast would remain different inputs with different units, never averaged into a common forecast score.

The natural home is a separately tracked comparison **within UnpricedX, the Stock Forecasting Lab**, using its existing trading engine. A separate repository or website is not required. UnpricedHub would continue recording and scoring forecast exports. Portfolio profit would need its own explicit evaluation; it is not currently audited by the Hub.

## Keep the comparisons interpretable

| Comparison | Purpose |
| --- | --- |
| Existing stock portfolio | Preserve the current fixed-policy record as the reference. |
| Same rankings with simple volatility-based sizing | Test whether basic risk sizing helps, before attributing value to another lab. |
| Same rankings and sizing rule using Risk Lab forecasts | Test incremental value from those forecasts under otherwise comparable rules. |

Use identical opportunity sets, information cutoffs, evaluation windows, execution assumptions and cost schedules when making comparisons. Report risk and market exposure as well as profit. Include cash and market references with explicit cost conventions. Evaluate turnover, drawdowns and whether apparent benefits are concentrated in a few episodes.

## Work in this order

1. **Establish reliable delivery.** Verify correct dates, on-time receipts, usable prices, completed resolutions, and recoverable failures. Several clean weeks can establish operational readiness; they do not establish forecast skill.
2. **Register a small policy comparison.** Declare the sizing formulas, allowed parameter choices, costs, selection criterion, missing-forecast behavior and review rules before evaluating them. Record every tried policy. Avoid an unrestricted search for a strategy that fits the past.
3. **Test the simple sizing rule historically.** Use time-ordered fits and evaluation, purge overlapping outcomes at boundaries, and retain all results. Already inspected periods are development evidence. Any policy selected there needs genuinely subsequent evidence.
4. **Test the Risk Lab’s incremental contribution.** Historical risk forecasts must be produced without future data and with documented provenance. If comparable forecasts are unavailable, do not fabricate a long combined track record; begin a separate prospective paper record instead.
5. **Run prospective comparisons beside the existing portfolio.** Freeze the plans before entry, preserve the original portfolio, and publish costs, positions, cash and outcomes separately.
6. **Review the evidence at declared checkpoints.** Three months can be a useful review point, but is not automatically enough to prove an advantage. Assess the magnitude and uncertainty of any benefit, its dependence on market regimes, and how many choices were tested before deciding to continue or change the policy.

## Resolve the differences between labs before combining inputs

- The Stock Forecasting Lab ranks individual stocks. The Risk Lab forecasts SPY and nine sector ETFs. A stock-to-sector or market-risk mapping must be explicit; ETF variance is not a complete forecast of individual-stock or portfolio risk.
- Their exact target windows differ. The stock task uses an opening-to-opening window; the risk task uses the next open through the fifth session close. “Five days” is not enough to declare them interchangeable.
- Use only forecasts actually available at the trading decision time. Specify behavior for late, stale, missing or abstained forecasts in advance.
- State how the rule treats overnight risk, position limits, cash, correlation and leverage. A forecast of market volatility alone does not solve portfolio construction.
- Keep forecast evaluation and policy evaluation separate. Better variance loss does not necessarily imply higher trading returns, and a cash-heavy strategy can lose less simply by taking less market exposure.

The present **UnpricedZ sector-ETF $1,000 experiment continues unchanged**. Its fixed direction-based policy and its recorded results must not be spliced into the history of a future stock strategy.
