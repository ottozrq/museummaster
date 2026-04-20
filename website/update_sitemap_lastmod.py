#!/usr/bin/env python3
"""Update all <lastmod> values in website/sitemap.xml to today's date."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import sys


def main() -> int:
    sitemap_path = Path(__file__).resolve().parents[1] / "sitemap.xml"
    if not sitemap_path.exists():
        print(f"Error: sitemap not found at {sitemap_path}")
        return 1

    xml = sitemap_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    updated_xml, count = re.subn(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{today}</lastmod>", xml)

    if count == 0:
        print("No <lastmod> tags found, nothing changed.")
        return 0

    sitemap_path.write_text(updated_xml, encoding="utf-8")
    print(f"Updated {count} <lastmod> tags to {today}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
