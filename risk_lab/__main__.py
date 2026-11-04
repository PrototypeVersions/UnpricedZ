from __future__ import annotations

import argparse

from .storage import ROOT, config, now, read, write


def main():
    parser = argparse.ArgumentParser(description="UNPRICED Risk Lab")
    parser.add_argument("mode", choices=["daily", "research", "controls", "bootstrap"])
    args = parser.parse_args()
    cfg = config()
    path = ROOT / "site/data/risk_status.json"
    previous = read(path) if path.exists() else {}
    status = {"experiment": cfg["experiment"], "mode": args.mode, "status": "running", "attemptedAt": now()}
    try:
        if args.mode in ["controls", "bootstrap"]:
            from .controls import run_controls
            run_controls(cfg)
        if args.mode in ["research", "bootstrap"]:
            from .evaluate import run_research
            run_research(cfg)
        if args.mode in ["daily", "bootstrap"]:
            from .live import run_daily
            live = run_daily(cfg)
            status["forecastDates"] = live["forecastDates"]
        status.update(status="healthy", completedAt=now(), lastSuccessfulAt=now(), error=None)
    except Exception as exc:
        status.update(status="error", error=f"{type(exc).__name__}: {exc}", lastSuccessfulAt=previous.get("lastSuccessfulAt"))
        raise
    finally:
        write(path, status)


if __name__ == "__main__":
    main()
