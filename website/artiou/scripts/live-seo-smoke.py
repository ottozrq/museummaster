#!/usr/bin/env python3
"""Live SEO smoke test for the deployed Artiou marketing site.

The check is intentionally network-based so deployment regressions such as a
missing route returning the SPA fallback can be caught before a release is
marked ready for review.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.message import Message
from html import unescape
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

CANONICAL_ORIGIN = "https://www.artiou.com"
ROOT_ORIGIN = "https://artiou.com"
USER_AGENT = "ArtiouLiveSeoSmoke/1.0 (+https://www.artiou.com/)"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
DEFAULT_MISSING_PATHS = (
    "/en/nonexistent-growth-audit-test/",
    "/en/news/nonexistent-growth-audit-test/",
)
DEFAULT_CORE_URLS = (
    "https://www.artiou.com/en/",
    "https://www.artiou.com/en/paris-museum-guide/",
    "https://www.artiou.com/en/louvre-first-time-visitor-guide/",
    "https://www.artiou.com/en/musee-orsay-guide/",
    "https://www.artiou.com/en/mona-lisa-guide/",
    "https://www.artiou.com/en/monet-water-lilies-guide/",
)
PLANNING_LANGUAGE_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD|lorem ipsum|placeholder copy|internal planning|growth audit)\b|"
    r"(?:验收标准|复查指标|背景证据|待办|占位文案)",
    re.I,
)


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: Message
    body: bytes
    redirects: list[str]


class TrackingRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if request is not None:
            redirects = getattr(req, "redirects", []) + [newurl]
            setattr(request, "redirects", redirects)
        return request


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.canonical: str | None = None
        self.robots: str | None = None
        self.text_parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            self.canonical = attrs_dict.get("href") or self.canonical
        if tag == "meta" and attrs_dict.get("name", "").lower() == "robots":
            self.robots = attrs_dict.get("content") or self.robots

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self.skip_depth:
            self.text_parts.append(data)

    @property
    def title(self) -> str:
        return unescape(" ".join(self.title_parts)).strip()

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", unescape(" ".join(self.text_parts))).strip()


def fetch(url: str, timeout: float, *, allow_http_errors: bool = False) -> FetchResult:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    opener = build_opener(TrackingRedirectHandler)
    try:
        response = opener.open(request, timeout=timeout)
        body = response.read()
        return FetchResult(url, response.geturl(), response.status, response.headers, body, getattr(response, "redirects", []))
    except HTTPError as exc:
        body = exc.read()
        result = FetchResult(url, exc.geturl(), exc.code, exc.headers, body, getattr(exc, "redirects", []))
        if allow_http_errors:
            return result
        raise


def decode_body(result: FetchResult) -> str:
    content_type = result.headers.get("content-type", "")
    charset_match = re.search(r"charset=([\w.-]+)", content_type, re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    return result.body.decode(charset, errors="replace")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return f"{scheme}://{netloc}{path}{('?' + parsed.query) if parsed.query else ''}"


def parse_html(result: FetchResult) -> MetaParser:
    parser = MetaParser()
    parser.feed(decode_body(result))
    return parser


def fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"FAIL {message}")


def ok(message: str) -> None:
    print(f"OK   {message}")


def check_infrastructure(timeout: float, errors: list[str]) -> None:
    root_probe = f"{ROOT_ORIGIN}/en/"
    www_probe = f"{CANONICAL_ORIGIN}/en/"
    www_root_probe = f"{CANONICAL_ORIGIN}/"
    robots_url = f"{CANONICAL_ORIGIN}/robots.txt"

    root = fetch(root_probe, timeout)
    if normalize_url(root.final_url) != www_probe:
        fail(errors, f"root domain must redirect to canonical www URL: {root_probe} -> {root.final_url}")
    else:
        ok(f"root domain redirects to {www_probe}")

    www_root = fetch(www_root_probe, timeout)
    if normalize_url(www_root.final_url) != www_probe:
        fail(errors, f"www root must redirect to default English URL: {www_root_probe} -> {www_root.final_url}")
    else:
        ok(f"www root redirects to default English URL: {www_probe}")

    www = fetch(www_probe, timeout)
    if normalize_url(www.final_url) != www_probe:
        fail(errors, f"www URL must not redirect away/self-loop unexpectedly: {www_probe} -> {www.final_url}")
    elif www.redirects:
        fail(errors, f"www URL should be directly reachable without redirects: redirects={www.redirects}")
    else:
        ok(f"www URL has no redirect self-loop: {www_probe}")

    content_type = www.headers.get("content-type", "")
    if "charset=utf-8" not in content_type.lower():
        fail(errors, f"HTML content type must declare UTF-8: {content_type!r}")
    else:
        ok("HTML declares UTF-8")

    robots = fetch(robots_url, timeout)
    robots_text = decode_body(robots)
    sitemap_line = f"Sitemap: {CANONICAL_ORIGIN}/sitemap.xml"
    if sitemap_line not in robots_text:
        fail(errors, f"robots.txt must declare {sitemap_line}")
    else:
        ok("robots.txt declares canonical sitemap")


def sitemap_locs(timeout: float) -> list[str]:
    sitemap_url = f"{CANONICAL_ORIGIN}/sitemap.xml"
    result = fetch(sitemap_url, timeout)
    content_type = result.headers.get("content-type", "")
    if "charset=utf-8" not in content_type.lower():
        print(f"WARN sitemap content type does not explicitly declare UTF-8: {content_type!r}")
    root = ET.fromstring(result.body)
    locs = [node.text.strip() for node in root.findall("sm:url/sm:loc", SITEMAP_NS) if node.text]
    print(f"OK   parsed sitemap: {len(locs)} URL(s)")
    return locs


def check_page(url: str, timeout: float, errors: list[str]) -> None:
    result = fetch(url, timeout)
    normalized_url = normalize_url(url)
    final_url = normalize_url(result.final_url)
    if result.status != 200:
        fail(errors, f"sitemap URL must return 200: {url} status={result.status}")
        return
    if final_url != normalized_url:
        fail(errors, f"sitemap URL must not redirect/fallback: {url} -> {result.final_url}")
    content_type = result.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        fail(errors, f"sitemap URL must return HTML: {url} content-type={content_type!r}")
    if "charset=utf-8" not in content_type.lower():
        fail(errors, f"sitemap URL must declare UTF-8: {url} content-type={content_type!r}")

    meta = parse_html(result)
    canonical = meta.canonical
    robots = (meta.robots or "").lower()
    if "noindex" in robots:
        fail(errors, f"sitemap URL must be indexable: {url} robots={meta.robots!r}")
    if normalize_url(canonical or "") != normalized_url:
        fail(errors, f"sitemap URL must be self-canonical: {url} canonical={canonical!r}")
    parsed_path = urlparse(url).path or "/"
    canonical_path = urlparse(canonical or "").path or "/"
    if canonical_path != parsed_path:
        fail(errors, f"sitemap URL looks like fallback shell: {url} canonical={canonical!r}")
    if not meta.title:
        fail(errors, f"sitemap URL missing title: {url}")
    if PLANNING_LANGUAGE_RE.search(meta.text):
        fail(errors, f"sitemap URL contains internal planning/placeholder language: {url}")


def check_missing_paths(paths: Iterable[str], timeout: float, errors: list[str]) -> None:
    for path in paths:
        url = urljoin(CANONICAL_ORIGIN, path)
        result = fetch(url, timeout, allow_http_errors=True)
        if result.status not in {404, 410}:
            fail(errors, f"missing path must return 404/410, not fallback: {url} status={result.status} final={result.final_url}")
        else:
            ok(f"missing path returns {result.status}: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live SEO smoke checks against www.artiou.com")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sleep", type=float, default=0.05, help="delay between sitemap URL probes")
    parser.add_argument("--core-only", action="store_true", help="check infrastructure, core URLs, and missing paths only")
    parser.add_argument("--core-url", action="append", default=list(DEFAULT_CORE_URLS))
    parser.add_argument("--missing-path", action="append", default=list(DEFAULT_MISSING_PATHS))
    args = parser.parse_args()

    errors: list[str] = []
    try:
        check_infrastructure(args.timeout, errors)
        locs = sitemap_locs(args.timeout)
        targets = args.core_url if args.core_only else locs
        sitemap_set = {normalize_url(loc) for loc in locs}
        for core_url in args.core_url:
            if normalize_url(core_url) not in sitemap_set:
                fail(errors, f"core URL missing from sitemap: {core_url}")
        for url in targets:
            check_page(url, args.timeout, errors)
            if args.sleep:
                time.sleep(args.sleep)
        check_missing_paths(args.missing_path, args.timeout, errors)
    except (HTTPError, URLError, TimeoutError, ET.ParseError, UnicodeDecodeError) as exc:
        fail(errors, f"unhandled live SEO smoke error: {type(exc).__name__}: {exc}")

    if errors:
        print(f"\nLive SEO smoke FAILED: {len(errors)} error(s)")
        return 1
    print("\nLive SEO smoke PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
