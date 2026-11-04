"""Reject invalid JSON and accidental invention of live results."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for folder in ["site/data", "records"]:
    for path in (root / folder).rglob("*.json"):
        value = json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        if "forecasts" in str(path) and isinstance(value, dict) and "publishedAt" in value:
            assert value["publishedAt"] < value["entryOpen"], "Publication must precede entry"
            assert len(value["forecasts"]) == 9
            assert value["experiment"] == "research-2.0.0"
print("JSON and live publication invariants validated")
