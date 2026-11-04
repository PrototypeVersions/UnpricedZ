from __future__ import annotations

import hashlib
import pandas as pd

from .data import archive
from .evaluation import portfolio_simulation, summarize, walk_forward
from .features import panel
from .io import ROOT, now, provenance, write


def run_research(data, cfg):
    vintage = archive(data, "research")
    features = panel(data, cfg)
    predictions, folds = walk_forward(features, cfg)
    confirmation = (predictions.date >= pd.Timestamp(cfg["confirmationStart"])) & (predictions.date <= pd.Timestamp(cfg["confirmationEnd"]))
    development = predictions.date < pd.Timestamp(cfg["confirmationStart"])
    recent = predictions.date > pd.Timestamp(cfg["confirmationEnd"])
    report = {"status": "historical-research", "generatedAt": now(), "experiment": cfg["experiment"],
              "inputVintage": vintage, "provenance": provenance(), "horizon": cfg["horizon"],
              "target": "Next session adjusted open to the fifth session adjusted close; excess over SPY",
              "summary": summarize(predictions, cfg),
              "periods": {"development": summarize(predictions[development], cfg),
                          "confirmation": summarize(predictions[confirmation], cfg),
                          "recent": summarize(predictions[recent], cfg)},
              "folds": folds, "portfolio": portfolio_simulation(predictions, cfg),
              "limitations": ["Retrospective, provider-revised adjusted daily data; not an historical as-published data feed.",
                              "Nine legacy sector ETFs selected today; excludes newer sector funds and is not a stock-selection study.",
                              "2025 is the prespecified confirmation year. It is unobserved before the initial frozen specification, but ceases to be untouched after the first run.",
                              "Intervals are descriptive and not adjusted for all model selection. No automatic promotion.",
                              "Adjusted opening prices are reference returns, not claims of executable fills."]}
    archive_dir = ROOT / "archive/research"
    archive_dir.mkdir(parents=True, exist_ok=True)
    csv = predictions.to_csv(index=False, float_format="%.12g")
    checksum = hashlib.sha256(csv.encode()).hexdigest()
    import gzip
    csv_path = archive_dir / f"predictions-{checksum[:16]}.csv.gz"
    if not csv_path.exists():
        csv_path.write_bytes(gzip.compress(csv.encode(), mtime=0))
    report["predictionsArchive"] = {"path": str(csv_path.relative_to(ROOT)), "csvSha256": checksum}
    name = f"{vintage['end']}-{checksum[:12]}.json"
    path = archive_dir / name
    if not path.exists():
        write(path, report, immutable=True)
    report["archivePath"] = str(path.relative_to(ROOT))
    write(ROOT / "site/data/research.json", report)
    return report
