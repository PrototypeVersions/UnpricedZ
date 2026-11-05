# Operations and scheduled review

## Continuing direction data pipeline

GitHub Actions, not the user's local machine, runs the data pipeline. Scheduled UTC attempts are 21:17, 22:17 and 23:47 on weekdays. NYSE trading sessions, actual times and current data control eligibility. This accommodates US daylight saving changes and provider delays. Early-close publication happens later that same evening; no perfect 13:45 timing is claimed.

Each run tests integrity, downloads/validates required data, resolves mature forecasts, publishes a new forecast only within its valid window, saves input vintages and exact features, and saves its public data. A following website job publishes the complete site. Repeated runs preserve the first same-session snapshot. No missing session is backfilled as live. New entries after the next opening are prohibited by publication checks.

A bootstrap computes all controls and historical research before attempting a prospective snapshot. If that computation crosses the target entry opening, the snapshot is missed. Do not relax the boundary to make launch look complete.

## Research updates

The historical evaluation is reproducible with `python -m unpriced research`. It is not rerun every day. Code-changing pushes run relevant integrity checks and regenerate historical research; new information or bug fixes must be logged. Model-policy changes must create a new specification/version with separate artifacts, not replace the running one.

Quarterly live model artifacts are immutable. A changed config hash within a stored model quarter fails instead of silently applying different rules. Before a future version transition, deliberately create a version-specific artifact namespace and preserve the old records.

## Weekly autonomous research review

The user authorized scheduled work to improve this lab. The ChatGPT task **UNPRICED Risk Lab review** is enabled for Sunday mornings around 08:00 America/Chicago, beginning 2026-11-08. It runs separately from GitHub's daily data jobs and prepares reviewed changes; it does not automatically merge a new research specification. The review should:

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

The four-part program is complete. Sunday reviews now prioritize the Risk Lab mandate below,
unresolved defects and the independent prospective record. They may inspect UnpricedX read-only for compatibility.
It cannot change X, run its holdout, contact another agent, create UnpricedHub, automatically
fine-tune/promote models or change the official research-2.0.0 policy. See
[the program](RESEARCH_PROGRAM.md) and [cross-lab strategy](MULTI_LAB_STRATEGY.md).

## Independent historical export and timely Hub delivery

The risk workflow also publishes the derived file at site/data/export/risk-v1-variance-oos-2019-2024.csv from the **original immutable** risk research predictions archive, without refitting models. See [historical variance export](HISTORICAL_VARIANCE_EXPORT.md). It is retrospective walk-forward evidence, not forecasts issued live in 2019–2024. The exporter checks original source hashes and refuses to overwrite changed output bytes.

Two additional overnight scheduled retries supplement the original daily risk workflow. All must respect the existing next-open deadline, and a successful risk forecast is not necessarily an on-time Hub receipt. Check both saved issue timestamps and Hub receipt timestamps. Earlier late receipts are preserved.

## Risk Lab mandate

The owner assigned overall project leadership to Claude and made UnpricedZ the Risk Lab.
The completed program-0.1.0 is retained as development evidence; the holiday-corrected macro
results are in [the registered macro review](PROGRAM_MACRO_REVIEW_2026-11-04.md).
Ongoing research prioritizes [risk-1.0.0](RISK_PROTOCOL.md), SPY/sector variance and drawdown,
strong baselines, data integrity and prospective scoring. Stop adding direction complexity.
The original research-2.0.0 models, code and daily ledger continue without replacement.
UnpricedX may not be modified. The owner authorized this handoff's new notes under Hub's
`notes/to-claude/`; every other Hub path remains read-only. Future autonomous reviews may
read coordination notes as advice, but must not send messages or modify Hub without authorization.

## Independent risk pipeline and exports

`Risk Lab benchmarks and daily record` runs at 21:29, 22:29 and 23:59 UTC on weekdays, with
the same NYSE timing gates and serialized publication group as the direction workflow.
The first operation runs six fixed synthetic diagnostics, the registered 2019–24 development
benchmark and the first eligible live publication. Subsequent daily runs resolve matured
outcomes, update variance states and publish before the next entry open. Monthly fitted
artifacts are immutable and code/dependency/registry mismatches fail closed.

The environment is installed with `pip install -r risk_lab/requirements.txt -r hub_export/requirements.txt`.
Run `python -m risk_lab bootstrap` once, or `daily`, `research`, `controls` separately; then
`python -m hub_export`. The workflow tests integrity and validates exports using the exact
pinned `hub/core.py validate()` plus JSON Schema before publication. The two latest paths
and task identifiers are in [the risk protocol](RISK_PROTOCOL.md). Dated export copies are
immutable; reissuing the same forecast ID must produce identical bytes. Hub receipt time is
independent of the source's issue timestamp.

Risk forecasts/resolutions live in `risk_records/risk-1.0.0/`; models, inputs and all research
attempts live in `risk_archive/`. Neither root overlaps the continuing direction ledger.
The website opens on Risk Lab, while every existing direction page remains available.

## Failure behavior

The last successful records remain available. The public status file reports a cycle error if the engine fails; GitHub Actions contains installation/test/deployment failures too. Never infer successful timely publication from a green workflow alone. Inspect record timestamps and target entry deadlines.

The provider can revise prices, throttle requests, or return incomplete data. Preserve uncertainty and missingness. All required current symbols must be present before publication. A stale forecast must retain its actual date.

## Deployment

GitHub Pages serves `site/` through Actions. The **Publish UNPRICED site** workflow is the single publisher. After a direction, risk, registered-program or archive-recovery job completes, it checks out current main, builds the display history, exchange calendar and on-site document readers, then publishes one complete bundle. It also runs for website/document changes and can be dispatched manually. Research jobs preserve their evidence and status but do not independently deploy a partial website.

The research schedules, model operations and record commits remain the same. Workflow-only publication edits do not trigger research reruns; changes to research code retain the existing triggers. A failed research job can still be followed by site publication so the error status remains visible.

Each website artifact is named with its workflow run ID and attempt number. Deployment selects that exact name. This prevents a retry from finding multiple artifacts named `github-pages` in the same workflow run; old artifacts can remain available without confusing the publisher.

The document reader copies original source bytes, reports their SHA-256 fingerprints and creates readable HTML. The build does not fit models, recompute scores or rewrite source records. Hub receipt context is a dated, optional read-only copy; a failed Hub fetch is shown as unavailable and does not block publication. The build installs its Markdown dependency separately from the frozen research environments.

No server, account registration or installation is required for visitors. The browser loads static JSON and refreshes while visible. Read methods, reports and frozen records in the on-site reference pages, with original-file downloads and optional GitHub provenance links. The publisher checks live file hashes against its artifact, including the new reference pages. Exact market-execution timing is not claimed by this static site.

## Storage

Full historical inputs are archived for research and quarterly model fits. Daily smaller windows preserve feature and resolution data. Track repository growth. If archives eventually move to durable object storage, retain content hashes, immutable references and a migration manifest; do not silently remove the evidence.

