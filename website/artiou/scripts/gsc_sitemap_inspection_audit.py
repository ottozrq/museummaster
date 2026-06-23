#!/usr/bin/env python3
"""Audit Artiou sitemap reporting against URL Inspection evidence.

Uses local Google ADC, never prints access tokens, and writes a reusable JSON/MD
record for the sitemap indexed=0 vs URL Inspection indexed-state check.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

PROPERTY = "sc-domain:artiou.com"
QUOTA_PROJECT = "ottoclaw-488816"
SITEMAP_URL = "https://www.artiou.com/sitemap.xml"
API_V3 = "https://searchconsole.googleapis.com/webmasters/v3"
INSPECTION_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SCOPE_HINT = "https://www.googleapis.com/auth/webmasters"

CORE_URLS = [
    "https://www.artiou.com/en/",
    "https://www.artiou.com/en/paris-museum-guide/",
    "https://www.artiou.com/en/louvre-first-time-visitor-guide/",
    "https://www.artiou.com/en/musee-orsay-guide/",
    "https://www.artiou.com/en/mona-lisa-guide/",
    "https://www.artiou.com/zh/",
]

EXTRA_SAMPLE_URLS = [
    "https://www.artiou.com/fr/",
    "https://www.artiou.com/zh/paris-museum-guide/",
    "https://www.artiou.com/fr/paris-museum-guide/",
    "https://www.artiou.com/en/museums/louvre/",
]


def access_token() -> str:
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token", "--quiet"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).strip()
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "Could not obtain Google ADC token. Run `gcloud auth application-default login` "
            f"with Search Console access to {PROPERTY}. Scope needed: {SCOPE_HINT}."
        ) from exc
    if not token:
        raise RuntimeError("gcloud returned an empty ADC token")
    return token


def request_json(method: str, url: str, token: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": QUOTA_PROJECT,
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Hermes-Artiou-GSC-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def sitemap_urls() -> list[str]:
    xml = fetch_text(SITEMAP_URL)
    root = ET.fromstring(xml)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls = [node.text.strip() for node in root.findall(f".//{ns}loc") if node.text and node.text.strip()]
    if not urls:
        urls = [node.text.strip() for node in root.findall(".//loc") if node.text and node.text.strip()]
    return urls


def get_sitemaps(token: str) -> list[dict[str, Any]]:
    site = urllib.parse.quote(PROPERTY, safe="")
    return request_json("GET", f"{API_V3}/sites/{site}/sitemaps", token).get("sitemap", [])


def submit_sitemap(token: str) -> None:
    site = urllib.parse.quote(PROPERTY, safe="")
    feed = urllib.parse.quote(SITEMAP_URL, safe="")
    request_json("PUT", f"{API_V3}/sites/{site}/sitemaps/{feed}", token)


def inspect_url(token: str, url: str) -> dict[str, Any]:
    payload = {"inspectionUrl": url, "siteUrl": PROPERTY, "languageCode": "en-US"}
    result = request_json("POST", INSPECTION_URL, token, payload)
    verdict = result.get("inspectionResult", {}).get("indexStatusResult", {})
    return {
        "url": url,
        "coverageState": verdict.get("coverageState"),
        "verdict": verdict.get("verdict"),
        "indexingState": verdict.get("indexingState"),
        "robotsTxtState": verdict.get("robotsTxtState"),
        "pageFetchState": verdict.get("pageFetchState"),
        "lastCrawlTime": verdict.get("lastCrawlTime"),
        "googleCanonical": verdict.get("googleCanonical"),
        "userCanonical": verdict.get("userCanonical"),
        "sitemap": verdict.get("sitemap"),
        "referringUrls": verdict.get("referringUrls", []),
    }


def parse_google_time(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def compact_sitemap(row: dict[str, Any]) -> dict[str, Any]:
    contents = row.get("contents") or []
    primary = contents[0] if contents else {}
    return {
        "path": row.get("path"),
        "lastSubmitted": row.get("lastSubmitted"),
        "lastDownloaded": row.get("lastDownloaded"),
        "isPending": row.get("isPending"),
        "errors": row.get("errors", 0),
        "warnings": row.get("warnings", 0),
        "submitted": primary.get("submitted"),
        "indexed": primary.get("indexed"),
        "type": primary.get("type"),
    }


def markdown(audit: dict[str, Any]) -> str:
    sm = audit["target_sitemap"] or {}
    lines = [
        f"# Artiou GSC sitemap vs URL Inspection audit — {audit['generatedAt'][:10]}",
        "",
        "## Summary",
        "",
        f"- Property: `{audit['property']}`",
        f"- Sitemap: `{audit['sitemapUrl']}`",
        f"- Sitemaps API fields: lastSubmitted=`{sm.get('lastSubmitted')}`, lastDownloaded=`{sm.get('lastDownloaded')}`, submitted=`{sm.get('submitted')}`, indexed=`{sm.get('indexed')}`, errors=`{sm.get('errors')}`, warnings=`{sm.get('warnings')}`.",
        f"- Live sitemap URL count: `{audit['liveSitemapUrlCount']}`.",
        f"- URL Inspection PASS count: `{audit['inspectionPassCount']}/{len(audit['inspections'])}` (PASS means `Submitted and indexed` or equivalent indexed coverage, Google canonical equals user canonical when both are present, and no crawl/robots block signal).",
        f"- Interpretation: {audit['interpretation']}",
        "",
        "## URL Inspection sample",
        "",
        "| URL | coverageState | lastCrawlTime | userCanonical | googleCanonical | result |",
        "|---|---|---|---|---|---|",
    ]
    for row in audit["inspections"]:
        lines.append(
            "| `{url}` | `{coverage}` | `{last}` | `{user}` | `{google}` | {status} |".format(
                url=row["url"],
                coverage=row.get("coverageState"),
                last=row.get("lastCrawlTime"),
                user=row.get("userCanonical"),
                google=row.get("googleCanonical"),
                status="PASS" if row.get("pass") else "FAIL",
            )
        )
    lines += [
        "",
        "## Weekly tracking row",
        "",
        "| Date | sitemap lastDownloaded | sitemap submitted | sitemap indexed | inspection indexed sample | notes |",
        "|---|---|---:|---:|---:|---|",
        f"| {audit['generatedAt'][:10]} | `{sm.get('lastDownloaded')}` | {sm.get('submitted')} | {sm.get('indexed')} | {audit['inspectionPassCount']}/{len(audit['inspections'])} | {audit['trackingNote']} |",
        "",
        "## Next checks",
        "",
        "- Recheck next week whether sitemap `lastDownloaded` advances and whether `indexed` changes from 0.",
        "- Escalate only if URL Inspection shows not indexed / crawl blocked / canonical mismatch on core URLs.",
        "",
        f"Raw JSON artifact: `{audit['jsonArtifact']}`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/Users/otto/.hermes/tmp")
    parser.add_argument("--submit-if-stale-days", type=float, default=7.0)
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between inspection calls")
    args = parser.parse_args()

    generated = dt.datetime.now(dt.timezone.utc)
    token = access_token()
    live_urls = sitemap_urls()
    sample = []
    for url in CORE_URLS + EXTRA_SAMPLE_URLS:
        if url in live_urls and url not in sample:
            sample.append(url)
    if len(sample) < 10:
        for url in live_urls:
            if url not in sample:
                sample.append(url)
            if len(sample) >= 10:
                break

    sitemaps = [compact_sitemap(row) for row in get_sitemaps(token)]
    target = next((row for row in sitemaps if row.get("path") == SITEMAP_URL), None)
    submitted = False
    submit_reason = "not submitted"
    if target:
        last_downloaded = parse_google_time(target.get("lastDownloaded"))
        if last_downloaded:
            age_days = (generated - last_downloaded).total_seconds() / 86400
            if age_days > args.submit_if_stale_days:
                submit_sitemap(token)
                submitted = True
                submit_reason = f"submitted because lastDownloaded age {age_days:.2f}d > {args.submit_if_stale_days:.2f}d"
                sitemaps = [compact_sitemap(row) for row in get_sitemaps(token)]
                target = next((row for row in sitemaps if row.get("path") == SITEMAP_URL), target)
            else:
                submit_reason = f"not submitted because lastDownloaded age {age_days:.2f}d <= {args.submit_if_stale_days:.2f}d"
        else:
            submit_reason = "not submitted because lastDownloaded missing/unparseable"
    else:
        submit_reason = "not submitted because target sitemap not found in Sitemaps API list"

    inspections = []
    for url in sample:
        row = inspect_url(token, url)
        coverage = row.get("coverageState") or ""
        google = row.get("googleCanonical")
        user = row.get("userCanonical")
        canonical_ok = (not google or not user) or google.rstrip("/") == user.rstrip("/")
        indexed_ok = coverage in {"Submitted and indexed", "Indexed, not submitted in sitemap"}
        blocked = row.get("robotsTxtState") == "BLOCKED" or row.get("pageFetchState") in {"BLOCKED_ROBOTS_TXT", "SOFT_404", "NOT_FOUND"}
        row["pass"] = bool(indexed_ok and canonical_ok and not blocked)
        row["canonicalOk"] = canonical_ok
        inspections.append(row)
        time.sleep(args.sleep)

    pass_count = sum(1 for row in inspections if row.get("pass"))
    all_core_pass = all(row.get("pass") for row in inspections if row["url"] in CORE_URLS)
    indexed = target.get("indexed") if target else None
    submitted_count = target.get("submitted") if target else None
    indexed_text = str(indexed) if indexed is not None else ""
    indexed_int = int(indexed_text) if indexed_text.isdigit() else None
    if indexed_int == 0 and pass_count >= 6 and all_core_pass:
        interpretation = (
            "Sitemaps API indexed=0 is a sitemap report lag/reporting inconsistency, not evidence that the core pages are deindexed; "
            "URL Inspection still reports the sampled core pages as submitted and indexed with self-canonical URLs."
        )
    elif not all_core_pass:
        interpretation = "Escalate: at least one core URL Inspection sample failed indexed/self-canonical checks."
    else:
        interpretation = "No P0 indexation failure found in the inspection sample; continue weekly tracking."

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"artiou_gsc_sitemap_inspection_audit_{generated.date().isoformat()}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    audit = {
        "generatedAt": generated.isoformat().replace("+00:00", "Z"),
        "property": PROPERTY,
        "sitemapUrl": SITEMAP_URL,
        "liveSitemapUrlCount": len(live_urls),
        "target_sitemap": target,
        "all_sitemaps": sitemaps,
        "submittedDuringRun": submitted,
        "submitReason": submit_reason,
        "inspections": inspections,
        "inspectionPassCount": pass_count,
        "corePass": all_core_pass,
        "interpretation": interpretation,
        "trackingNote": "report lag" if indexed_int == 0 and pass_count >= 6 and all_core_pass else "watch/escalate per inspection failures",
        "jsonArtifact": str(json_path),
        "submittedField": submitted_count,
        "indexedField": indexed,
    }
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown(audit), encoding="utf-8")
    print(json.dumps({
        "json": str(json_path),
        "markdown": str(md_path),
        "target_sitemap": target,
        "submittedDuringRun": submitted,
        "submitReason": submit_reason,
        "inspectionPassCount": pass_count,
        "inspectionTotal": len(inspections),
        "corePass": all_core_pass,
        "interpretation": interpretation,
    }, ensure_ascii=False, indent=2))
    return 0 if all_core_pass else 2


if __name__ == "__main__":
    sys.exit(main())
