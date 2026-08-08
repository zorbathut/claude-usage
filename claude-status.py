#!/usr/bin/env python3
"""Compact Claude usage status for taskbar display."""

import subprocess
import json
from datetime import datetime, timezone


def format_duration(reset_time_str):
    """Format time until reset as compact string like '3h' or '17m'."""
    if reset_time_str is None:
        return None

    reset_time = datetime.fromisoformat(reset_time_str)
    now = datetime.now(timezone.utc)
    delta = reset_time - now

    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "0m"

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h"
    else:
        return f"{minutes}m"


def find_limit(limits, kind):
    """First entry of the given kind in the API's limits array."""
    for entry in limits:
        if entry.get("kind") == kind:
            return entry
    return None


def legacy_limit(data, key):
    """Fall back to the older top-level {utilization, resets_at} sections."""
    section = data.get(key)
    if not isinstance(section, dict) or section.get("utilization") is None:
        return None
    return {"percent": section["utilization"], "resets_at": section.get("resets_at")}


def format_group(entries):
    """Render one or more related limits as '40%/62%↻31h'."""
    entries = [e for e in entries if e and e.get("percent") is not None]
    if not entries:
        return None

    percents = "/".join(f"{int(e['percent'])}%" for e in entries)
    reset = next(
        (d for d in (format_duration(e.get("resets_at")) for e in entries) if d),
        None
    )

    return f"{percents}↻{reset}" if reset else percents


def main():
    # Call claude-usage.py with --json flag
    result = subprocess.run(
        ["./claude-usage.py", "--json"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)
    limits = data.get("limits") or []

    session = find_limit(limits, "session") or legacy_limit(data, "five_hour")

    # Weekly shows the all-models number first, then any model-scoped limits
    # (currently Fable). The scoped entries may disappear from the API someday.
    weekly = [find_limit(limits, "weekly_all") or legacy_limit(data, "seven_day")]
    weekly += [e for e in limits if e.get("kind") == "weekly_scoped"]

    parts = [p for p in (format_group([session]), format_group(weekly)) if p]

    print(" ".join(parts))


if __name__ == "__main__":
    main()
