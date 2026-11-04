# Read-only review request for Claude

Please review https://github.com/PrototypeVersions/UnpricedZ alongside UnpricedX.
Do not modify either repository or run/tune against UnpricedX's sealed holdout.

Read AGENTS.md, docs/METHODOLOGY.md, docs/PROTOCOL.md, docs/FIRST_REVIEW.md,
docs/RESEARCH_PROGRAM.md and docs/MULTI_LAB_STRATEGY.md, then inspect the implementation.

Please return:

1. Concrete leakage, timing, target, missing-data or scoring defects, with file/line evidence
   and a minimal failing example. Separate verified bugs from assumptions and hypotheses.
2. A mapping of each lab's universe, information cutoff, entry/exit convention, forecast type,
   baseline and metric. Say which outputs are actually comparable without retraining.
3. One proposed shared benchmark and the smallest independent shadow adapter needed in each
   lab. Do not convert a rank to a probability or change the endpoint without a new experiment.
4. At most two transferable ideas, each with an economic reason, a fixed ablation, data needs,
   validation plan, expected cost, and a trial-registry entry.
5. An independent critique of repeated holdout use, sequential promotion assumptions, and
   pretrained-model historical contamination. Explain what would constitute new evidence.
6. A proposed machine-readable export for a read-only UnpricedHub that can timestamp receipts
   and independently recompute results. Do not let the hub silently choose or promote winners.

The goal is a reliable comparison and a small number of stronger hypotheses. Agreement between
AI reviewers and favorable backtests do not establish a live forecasting edge.
