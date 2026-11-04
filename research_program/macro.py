"""As-published macro inputs; date-only vintages receive a conservative session lag."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd


class MacroUnavailable(RuntimeError):
    pass


def download_vintages(spec, observation_start="2008-01-01"):
    key = os.environ.get(spec["keyEnvironment"])
    if not key:
        raise MacroUnavailable("FRED_API_KEY repository secret is absent; macro experiment blocked.")
    retrieved = datetime.now(timezone.utc).isoformat()
    result = {"retrievedAt": retrieved, "provider": spec["provider"], "series": {}}
    for series in spec["series"]:
        rows, offset = [], 0
        while True:
            params = {"api_key": key, "file_type": "json", "series_id": series,
                      "realtime_start": "1776-07-04", "realtime_end": retrieved[:10],
                      "observation_start": observation_start, "output_type": 1,
                      "limit": 100000, "offset": offset, "sort_order": "asc"}
            try:
                with urlopen("https://api.stlouisfed.org/fred/series/observations?" + urlencode(params), timeout=90) as response:
                    payload = json.load(response)
            except (HTTPError, URLError, TimeoutError) as exc:
                # Never log a request URL containing the API key.
                raise MacroUnavailable(f"ALFRED request failed for {series}: {type(exc).__name__}") from None
            batch = payload.get("observations", [])
            if not batch:
                if not rows:
                    raise MacroUnavailable(f"ALFRED returned no vintage observations for {series}")
                break
            rows.extend(batch)
            offset += len(batch)
            if offset >= int(payload["count"]):
                break
        # Only data and non-secret provenance enter the archive.
        result["series"][series] = rows
    return result


def asof_series(rows, sessions, max_age, changes=()):
    """Replay revisions in availability order; transform the entire as-of snapshot.

    Old-period revisions cannot replace a newer observation as the latest release.
    A missing-value revision withdraws that value; it does not restore an older one.
    """
    events = {}
    for row in rows:
        vintage = pd.Timestamp(row["realtime_start"])
        observed = pd.Timestamp(row["date"])
        index = sessions.searchsorted(vintage, side="right")
        if index >= len(sessions):
            continue
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            value = np.nan
        events.setdefault(index, []).append((vintage, observed, value))
    state, output = {}, []
    for i, date in enumerate(sessions):
        for _, observed, value in sorted(events.get(i, []), key=lambda x: (x[0], x[1])):
            if observed > date:
                raise ValueError("Observation period is after its alleged availability")
            state[observed] = value
        row = {"date": date, "value": np.nan}
        row.update({f"lag{months}": np.nan for months in changes})
        if state:
            latest = max(state)
            if (date - latest).days <= max_age:
                row["value"] = state[latest]
                for months in changes:
                    row[f"lag{months}"] = state.get(latest - pd.DateOffset(months=months), np.nan)
        output.append(row)
    return pd.DataFrame(output).set_index("date")


def macro_panel(payload, sessions, spec):
    sessions = pd.DatetimeIndex(sessions).sort_values().unique()
    series = {}
    for name, max_age in spec["series"].items():
        if name not in payload["series"]:
            raise MacroUnavailable(f"Missing vintage series {name}")
        lag = (12,) if name == "CPIAUCSL" else (3,) if name == "UNRATE" else ()
        series[name] = asof_series(payload["series"][name], sessions, max_age, lag)
    out = pd.DataFrame(index=sessions)
    out["rate10"] = series["DGS10"].value
    out["slope"] = series["T10Y2Y"].value
    out["credit"] = series["BAA10Y"].value
    out["inflation12"] = 100 * (series["CPIAUCSL"].value / series["CPIAUCSL"].lag12 - 1)
    out["unemployment"] = series["UNRATE"].value
    out["unemployment3"] = series["UNRATE"].value - series["UNRATE"].lag3
    return out.replace([np.inf, -np.inf], np.nan).rename_axis("date").reset_index()
