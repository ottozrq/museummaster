#!/usr/bin/env python3
"""Audit Artiou sitemap URLs for indexability and content-quality gates.

This is a read-only companion to build-news.mjs. It validates every URL that is
already in sitemap.xml so newly-added core/museum/entity pages have an explicit
quality gate before they are submitted to Google.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

SITE_URL = "https://www.artiou.com"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
LOCALE_RE = re.compile(r"^/(zh|en|fr)/")
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    return unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html))).strip()


def attr_content(html: str, pattern: str) -> str | None:
    match = re.search(pattern, html, flags=re.I | re.S)
    return unescape(match.group(1).strip()) if match else None


def local_path_for_url(site_root: Path, loc: str) -> Path | None:
    parsed = urlparse(loc)
    if f"{parsed.scheme}://{parsed.netloc}" != SITE_URL:
        return None
    rel = parsed.path.lstrip("/")
    return site_root / rel / "index.html" if rel.endswith("/") or not rel else site_root / rel


def classify(path: str) -> str:
    if path in ("/", "/zh/", "/en/", "/fr/"):
        return "home"
    if path.endswith("/privacy/") or path.endswith("/legal/"):
        return "policy"
    if path.endswith("/news/"):
        return "news-index"
    if "/news/" in path:
        return "news-article"
    if "museum-guide" in path or "musee-orsay-guide" in path or "louvre-first-time-visitor-guide" in path:
        return "museum-guide"
    return "entity-or-static"


def audit_url(site_root: Path, loc: str) -> dict:
    parsed = urlparse(loc)
    path = parsed.path
    page_type = classify(path)
    item = {"url": loc, "type": page_type, "included": True, "reasons": []}
    html_path = local_path_for_url(site_root, loc)
    if html_path is None:
        item.update(included=False, reasons=["URL is outside canonical host"])
        return item
    if not html_path.exists():
        item.update(included=False, reasons=[f"local HTML missing: {html_path.relative_to(site_root)}"])
        return item

    html = html_path.read_text(encoding="utf-8")
    text = strip_tags(html)
    title = attr_content(html, r"<title[^>]*>(.*?)</title>")
    h1 = attr_content(html, r"<h1[^>]*>(.*?)</h1>")
    canonical = attr_content(html, r"<link[^>]+rel=[\"']canonical[\"'][^>]+href=[\"']([^\"']+)[\"']")
    robots = attr_content(html, r"<meta[^>]+name=[\"']robots[\"'][^>]+content=[\"']([^\"']+)[\"']") or ""

    reasons: list[str] = []
    warnings: list[str] = []
    if page_type == "policy":
        reasons.append("privacy/legal policy pages are excluded from growth sitemap")
    if page_type == "news-index":
        reasons.append("news index hubs are excluded from growth sitemap; submit eligible article URLs only")
    if "noindex" in robots.lower():
        reasons.append("robots contains noindex")
    if canonical != loc:
        reasons.append(f"canonical mismatch: {canonical or 'missing'}")
    if not title:
        reasons.append("missing title")
    elif len(title) < 8:
        warnings.append("short title")
    if not h1:
        reasons.append("missing H1")
    elif len(h1) < 4:
        warnings.append("short H1")
    if canonical in {f"{SITE_URL}/", f"{SITE_URL}/zh/"} and path not in ("/", "/zh/"):
        reasons.append("looks like fallback shell canonical")

    if page_type == "museum-guide":
        lowered = text.lower()
        route_ok = any(word in lowered for word in ["route", "itinerary", "路线", "itinéraire"])
        practical_ok = any(word in lowered for word in ["practical", "tips", "hours", "tickets", "实用", "pratique"])
        faq_ok = "faq" in lowered or "questions" in lowered or "常见" in lowered
        internal_links = len(re.findall(r"href=[\"']/(?:zh|en|fr)/", html))
        if len(text) < 3500:
            warnings.append(f"museum guide body is thin ({len(text)} chars, target 3500+)")
        if not route_ok:
            warnings.append("museum guide missing route/itinerary signal")
        if not practical_ok:
            warnings.append("museum guide missing practical-info signal")
        if not faq_ok:
            warnings.append("museum guide missing FAQ/questions signal")
        if internal_links < 3:
            warnings.append(f"museum guide has few internal links ({internal_links}, target 3+)")
    elif page_type == "news-article" and len(text) < 2500:
        warnings.append(f"news article body is thin ({len(text)} chars, target 2500+)")
    elif page_type == "entity-or-static" and len(text) < 1800:
        warnings.append(f"entity/static body is thin ({len(text)} chars, target 1800+)")

    item.update(
        included=not reasons,
        reasons=reasons or ["passes sitemap indexability/content gate"],
        warnings=warnings,
        path=str(html_path.relative_to(site_root)),
        title=title,
        h1=h1,
        canonical=canonical,
        bodyChars=len(text),
    )
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fail-on-errors", action="store_true")
    args = parser.parse_args()

    sitemap = args.site_root / "sitemap.xml"
    locs = [node.text for node in ET.parse(sitemap).getroot().findall("sm:url/sm:loc", SITEMAP_NS)]
    urls = [audit_url(args.site_root, loc) for loc in locs if loc]
    report = {
        "generatedAt": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "sitemap": str(sitemap),
        "summary": {
            "urlsAudited": len(urls),
            "urlsPassing": sum(1 for item in urls if item["included"]),
            "urlsFailing": sum(1 for item in urls if not item["included"]),
            "urlsWithWarnings": sum(1 for item in urls if item.get("warnings")),
        },
        "urls": urls,
    }
    output = args.output or args.site_root / "scripts" / "sitemap-page-audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.fail_on_errors and report["summary"]["urlsFailing"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
