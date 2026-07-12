#!/usr/bin/env python3
"""Summarize Artiou Umami events for the weekly growth report.

This script is intentionally API-client agnostic: export the relevant Umami API
responses as JSON, then pass them here. It keeps the weekly report format stable
without storing API tokens in the repo.

Expected input shape is flexible. Use any of:
- a list of event rows: [{"eventName": "download_click", "url": "/en/", "x": 3}, ...]
- an object containing events/topEvents/top_event_pages/topPages arrays
- Umami metric rows using keys such as event, eventName, name, x, y, views, count

Example:
  python scripts/umami_weekly_funnel_report.py umami-events.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

CORE_EVENTS = {"homepage_download_click", "guide_download_click", "entity_download_click"}
GUIDE_EVENT = "guide_download_click"


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    candidates: list[dict[str, Any]] = []
    for key in ("events", "topEvents", "top_events", "top_event_pages", "topPages", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(r for r in value if isinstance(r, dict))
    if not candidates and all(isinstance(v, (str, int, float, type(None))) for v in payload.values()):
        candidates.append(payload)
    return candidates


def _name(row: dict[str, Any]) -> str:
    for key in ("eventName", "event", "name", "event_name"):
        value = row.get(key)
        if value:
            return str(value)
    return ""


def _path(row: dict[str, Any]) -> str:
    for key in ("source_path", "page_path", "path", "url", "x"):
        value = row.get(key)
        if isinstance(value, str) and value.startswith("/"):
            return value.split("?", 1)[0]
    return "(unknown)"


def _count(row: dict[str, Any]) -> int:
    for key in ("count", "events", "views", "visits", "y", "value"):
        value = row.get(key)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return 1


def summarize(rows: Iterable[dict[str, Any]]) -> str:
    event_counts: Counter[str] = Counter()
    page_event_counts: Counter[tuple[str, str]] = Counter()
    guide_downloads_by_path: Counter[str] = Counter()

    for row in rows:
        name = _name(row)
        if not name:
            continue
        count = _count(row)
        path = _path(row)
        event_counts[name] += count
        if name in CORE_EVENTS:
            page_event_counts[(path, name)] += count
        if name == GUIDE_EVENT:
            guide_downloads_by_path[path] += count

    total_core = sum(event_counts[e] for e in CORE_EVENTS)
    lines = [
        "## Umami events",
        f"- Core CTA events total: {total_core}",
    ]
    for name in ("homepage_download_click", "guide_download_click", "entity_download_click"):
        lines.append(f"- {name}: {event_counts[name]}")

    lines.append("\n## Top event pages")
    if page_event_counts:
        for (path, name), count in page_event_counts.most_common(10):
            lines.append(f"- {path} · {name}: {count}")
    else:
        lines.append("- No core CTA events in input sample.")

    lines.append("\n## Low-sample guide→download funnel")
    guide_total = sum(guide_downloads_by_path.values())
    lines.append(f"- Guide download intents: {guide_total}")
    if guide_downloads_by_path:
        for path, count in guide_downloads_by_path.most_common(10):
            lines.append(f"- {path}: {count} guide_download_click")
    else:
        lines.append("- No guide_download_click events yet; keep this section until sample size grows.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: umami_weekly_funnel_report.py <umami-events.json>", file=sys.stderr)
        return 2
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    print(summarize(_rows(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
