# Operations and scheduled review

## Daily data pipeline

GitHub Actions, not the user's local machine, runs the data pipeline. Scheduled UTC attempts are 21:17, 22:17 and 23:47 on weekdays. NYSE trading sessions, actual times and current data control eligibility. This accommodates US daylight saving changes and provider delays. Early-close publication happens later that same evening; no perfect 13:45 timing is claimed.

Each run tests integrity, downloads/validates required data, resolves mature forecasts, publishes a new forecast only within its valid window, saves input vintages and exact features, and deploys the public site. Repeated runs preserve the first same-session snapshot. No missing session is backfilled as live. New entries after the next opening are prohibited by publication checks.

A bootstrap computes all controls and historical research before attempting a prospective snapshot. If that computation crosses the target entry opening, the snapshot is missed. Do not relax the boundary to make launch look complete.

## Research updates

The historical evaluation is reproducible with `python -m unpriced research`. It is not rerun every day. Code-changing pushes run relevant integrity checks and regenerate historical research; new information or bug fixes must be logged. Model-policy changes must create a new specification/version with separate artifacts, not replace the running one.

Quarterly live model artifacts are immutable. A changed config hash within a stored model quarter fails instead of silently applying different rules. Before a future version transition, deliberately create a version-specific artifact namespace and preserve the old records.

## Weekly autonomous research review

The user authorized scheduled work to improve this lab. The ChatGPT task **UNPRICED research review** is enabled for Sunday mornings around 08:00 America/Chicago, beginning 2026-11-08. It runs separately from GitHub's daily data jobs and prepares reviewed changes; it does not automatically merge a new research specification. The review should:

1. Read this repository's protocol, changes and actual workflow results.
2. Check that completed sessions have valid snapshots or explicit missed-window records, with no premature resolutions.
3. Examine null controls, model performance, uncertainty, coverage and paper-policy consistency by forecast date.
4. Correct genuine reproducible software/data defects in a tested branch/PR, with an additive audit of affected older outputs.
5. If useful, prepare one clearly specified challenger experiment in isolation. Do not optimize on the observed confirmation year and describe it as new evidence.
6. Report concrete changes, tests, unresolved problems, and the most useful next research step.

Never modify PrototypeVersions/Unpriced, its automations, or its historical records. Do not silently promote a model, change live trading rules, execute real trades, erase results, purchase data, or send messages to other people.

## Registered upgrade program

The separate `Registered research program` workflow executes the bounded comparisons in
`research_program/registry.json`, preserving every attempt under `archive/program/` and a
current presentation at `site/data/program.json`. It runs on program-code changes or manual
dispatch, not as an unbounded recurring search. Its CPU job has a 50-minute limit. Its inputs
use the pinned price archive; optional ALFRED retrieval needs the repository secret
`FRED_API_KEY`. Missing credentials are a blocked experiment, not a successful macro test.

The Sunday review now prioritizes this four-part program, unresolved defects, and a carefully
specified prospective shadow launch. It may inspect UnpricedX read-only for compatibility.
It cannot change X, run its holdout, contact another agent, create UnpricedHub, automatically
fine-tune/promote models or change the official research-2.0.0 policy. See
[the program](RESEARCH_PROGRAM.md) and [cross-lab strategy](MULTI_LAB_STRATEGY.md).

## Failure behavior

The last successful records remain available. The public status file reports a cycle error if the engine fails; GitHub Actions contains installation/test/deployment failures too. Never infer successful timely publication from a green workflow alone. Inspect record timestamps and target entry deadlines.

The provider can revise prices, throttle requests, or return incomplete data. Preserve uncertainty and missingness. All required current symbols must be present before publication. A stale forecast must retain its actual date.

## Deployment

GitHub Pages serves site/ through Actions. No server, account registration or installation is required for visitors. The browser loads static JSON and refreshes while visible. Use the raw archives and Git history for independent inspection. Exact market-execution timing is not claimed by this static site.

## Storage

Full historical inputs are archived for research and quarterly model fits. Daily smaller windows preserve feature and resolution data. Track repository growth. If archives eventually move to durable object storage, retain content hashes, immutable references and a migration manifest; do not silently remove the evidence.
