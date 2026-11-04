"""As-published macro inputs; date-only vintages receive a conservative session lag."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd


class MacroUnavailable(RuntimeError):
    pass


def http_failure(exc, key, series):
    """Keep the API's diagnostic, never a credential-bearing request URL/body."""
    detail = ""
    try:
        payload = json.loads(exc.read(8192).decode("utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("error_message"), str):
            detail = payload["error_message"]
    except (ValueError, UnicodeError, OSError):
        pass
    if key:
        detail = re.sub(re.escape(key), "[redacted]", detail, flags=re.IGNORECASE)
    detail = re.sub(r"(?i)(api_key\s*[=:]\s*)[^&\s\"'<>]+", r"\1[redacted]", detail)
    detail = " ".join(detail.split())[:500]
    return f"ALFRED request failed for {series}: HTTP {exc.code}" + (f" — {detail}" if detail else "")


def fred_request(key, series, endpoint, params):
    query = {"api_key": key, "file_type": "json", "series_id": series, **params}
    try:
        with urlopen("https://api.stlouisfed.org/fred/series/" + endpoint + "?" + urlencode(query), timeout=90) as response:
            return json.load(response)
    except HTTPError as exc:
        raise MacroUnavailable(http_failure(exc, key, series)) from None
    except (URLError, TimeoutError) as exc:
        raise MacroUnavailable(f"ALFRED request failed for {series}: {type(exc).__name__}") from None


def observations_request(key, series, params):
    return fred_request(key, series, "observations", params)


def first_vintage(key, series, end):
    payload = fred_request(key, series, "vintagedates", {
        "realtime_start": "1776-07-04", "realtime_end": end, "sort_order": "asc", "limit": 1})
    dates = payload.get("vintage_dates", [])
    if not dates:
        raise MacroUnavailable(f"ALFRED has no archived vintages for {series}")
    try:
        first = date.fromisoformat(dates[0]).isoformat()
    except (ValueError, TypeError):
        raise MacroUnavailable(f"ALFRED returned an invalid first vintage for {series}") from None
    if first > end:
        raise MacroUnavailable(f"ALFRED returned a future first vintage for {series}")
    return first


def realtime_windows(start, end):
    """At most 1,000 calendar dates, below FRED's 2,000 JSON-vintage limit."""
    cursor, final = date.fromisoformat(start), date.fromisoformat(end)
    while cursor <= final:
        stop = min(cursor + timedelta(days=999), final)
        yield cursor.isoformat(), stop.isoformat()
        cursor = stop + timedelta(days=1)


def download_vintages(spec, observation_start="2008-01-01"):
    key = os.environ.get(spec["keyEnvironment"])
    if not key:
        raise MacroUnavailable("FRED_API_KEY repository secret is absent; macro experiment blocked.")
    retrieved = datetime.now(timezone.utc).isoformat()
    # A one-row current-date probe reads only the server's date. Its revised
    # observation is deliberately discarded, never used as a historical input.
    probe = observations_request(key, next(iter(spec["series"])),
                                 {"observation_start": observation_start, "limit": 1})
    server_end = probe.get("realtime_end")
    try:
        valid_end = isinstance(server_end, str) and observation_start <= server_end <= retrieved[:10]
        valid_end = valid_end and date.fromisoformat(server_end).isoformat() == server_end
    except ValueError:
        valid_end = False
    if not valid_end:
        raise MacroUnavailable("FRED omitted a valid current-date boundary")
    result = {"retrievedAt": retrieved, "provider": spec["provider"], "series": {},
              "realtimeEnd": server_end, "realtimeWindows": {}, "firstVintageDates": {}}
    for series in spec["series"]:
        earliest = first_vintage(key, series, server_end)
        # A range wholly before a series existed in ALFRED returns HTTP 400,
        # rather than an empty list. Query its documented coverage boundary first.
        windows = list(realtime_windows(max(observation_start, earliest), server_end))
        result["firstVintageDates"][series] = earliest
        result["realtimeWindows"][series] = windows
        rows = []
        for start, end in windows:
            offset = 0
            while True:
                payload = observations_request(key, series, {
                    "realtime_start": start, "realtime_end": end,
                    "observation_start": observation_start, "output_type": 1,
                    "limit": 100000, "offset": offset, "sort_order": "asc"})
                if payload.get("realtime_start") != start or payload.get("realtime_end") != end:
                    raise MacroUnavailable(f"ALFRED changed the requested real-time boundary for {series}")
                batch = payload.get("observations", [])
                count = int(payload["count"])
                if not batch and offset < count:
                    raise MacroUnavailable(f"ALFRED returned an incomplete page for {series}")
                rows.extend(batch)
                offset += len(batch)
                if offset >= count:
                    break
        if not rows:
            raise MacroUnavailable(f"ALFRED returned no vintage observations for {series}")
        # Only data and non-secret provenance enter the archive.
        result["series"][series] = rows
        print(f"Archived {series}: {len(rows)} vintage observations", flush=True)
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
