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


def main():
    # Call claude-usage.py with --json flag
    result = subprocess.run(
        ["./claude-usage.py", "--json"],
        capture_output=True,
        text=True,
        check=True
    )

    data = json.loads(result.stdout)

    # Extract data (skip opus as requested)
    five_hour = data.get("five_hour", {})
    seven_day = data.get("seven_day", {})

    parts = []

    if five_hour:
        util = five_hour.get("utilization", 0)
        reset = format_duration(five_hour.get("resets_at"))
        if reset:
            parts.append(f"{util}%↻{reset}")
        else:
            parts.append(f"{util}%")

    if seven_day:
        util = seven_day.get("utilization", 0)
        reset = format_duration(seven_day.get("resets_at"))
        if reset:
            parts.append(f"{util}%↻{reset}")
        else:
            parts.append(f"{util}%")

    print(" ".join(parts))


if __name__ == "__main__":
    main()
