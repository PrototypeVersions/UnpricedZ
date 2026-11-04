from __future__ import annotations

import argparse
import json
import traceback

from .io import ROOT, config, now, provenance, read, write


def main():
    parser = argparse.ArgumentParser(description="UNPRICED Research")
    parser.add_argument("mode", choices=["controls", "research", "daily", "bootstrap"])
    parser.add_argument("--seeds", type=int)
    args = parser.parse_args()
    cfg = config()
    status = {"status": "running", "mode": args.mode, "attemptedAt": now(), "experiment": cfg["experiment"]}
    path = ROOT / "site/data/status.json"
    previous = read(path) if path.exists() else {}
    try:
        if args.mode in ["controls", "bootstrap"]:
            from .controls import run_controls
            run_controls(cfg, args.seeds)
        if args.mode in ["research", "daily", "bootstrap"]:
            from .data import download, market_summary, session_context
            context = session_context()
            data = download(cfg, context["session"])
            if args.mode in ["research", "bootstrap"]:
                from .research import run_research
                run_research(data, cfg)
            from .live import publish
            live = publish(data, cfg, context)
            status["latestSession"] = str(context["session"].date())
            status["liveForecastDates"] = live["forecastDates"]
        status.update(status="healthy", completedAt=now(), lastSuccessfulAt=now(), error=None)
        write(path, status)
    except Exception as exc:
        status.update(status="error", error=f"{type(exc).__name__}: {exc}",
                      lastSuccessfulAt=previous.get("lastSuccessfulAt"))
        write(path, status)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
