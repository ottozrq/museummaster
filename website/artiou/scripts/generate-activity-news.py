#!/usr/bin/env python3
"""Generate one daily Artiou exhibition news article from Vision API.

- Fetches active exhibition-like activities from Vision API.
- Picks the first activity_id not present in scripts/processed_activity_news.json.
- Writes zh/en/fr markdown into content/news/{locale}/.
- Runs scripts/build-news.mjs unless --no-build is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = SITE_ROOT / "content" / "news"
STATE_FILE = SITE_ROOT / "scripts" / "processed_activity_news.json"
BUILD_SCRIPT = SITE_ROOT / "scripts" / "build-news.mjs"
ENV_FILE = Path("/var/www/gagaou/.env")
API_BASE = "https://vision.ottozhang.com"
ARTICLE_AUTHOR = "Artiou Team"
EXHIBITION_TAGS = ["Expo", "Art contemporain", "Peinture", "Photo"]

class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

def html_text(value: str | None) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()

def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def request_json(url: str, token: str | None = None, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    req_headers = {"User-Agent": "ArtiouNewsBot/1.0"}
    if headers:
        req_headers.update(headers)
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=req_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def get_token() -> str:
    load_env_file(ENV_FILE)
    username = os.environ.get("VISION_API_USER") or os.environ.get("VISION_USERNAME")
    password = os.environ.get("VISION_API_PASS") or os.environ.get("VISION_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing VISION_API_USER/VISION_API_PASS")
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    payload = request_json(f"{API_BASE}/token/", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    return payload["access_token"]

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    value = re.sub(r"[\s-]+", "-", value).strip("-")
    return value[:72] or "artiou-exhibition"

def frontmatter_value(value: str | int | None) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace('"', "'").strip()

def scan_existing_activity_ids() -> set[str]:
    ids: set[str] = set()
    for path in CONTENT_ROOT.glob("*/*.md"):
        try:
            in_frontmatter = False
            for line in path.read_text(encoding="utf-8").splitlines():
                if line == "---":
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    break
                if not in_frontmatter:
                    continue
                if line.startswith("activityId:"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        ids.add(value)
                    break
        except OSError:
            continue
    return ids

def load_processed() -> set[str]:
    processed: set[str] = set()
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            if isinstance(data, list):
                processed.update(str(item) for item in data)
            elif isinstance(data, dict):
                processed.update(str(item) for item in data.get("activity_ids", []))
        except json.JSONDecodeError:
            pass
    processed.update(scan_existing_activity_ids())
    return processed

def save_processed(processed: set[str]) -> None:
    STATE_FILE.write_text(json.dumps({"activity_ids": sorted(processed)}, ensure_ascii=False, indent=2) + "\n")

def fetch_candidates(token: str, max_pages: int) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    for tag in EXHIBITION_TAGS:
        page_token = "1"
        for _ in range(max_pages):
            params = urllib.parse.urlencode({"page_size": 20, "hide_ended": "true", "tags_csv": tag, "page_token": page_token})
            payload = request_json(f"{API_BASE}/activities/?{params}", token=token)
            for item in payload.get("contents", []):
                activity_id = item.get("activity_id")
                if activity_id and activity_id not in seen:
                    seen.add(activity_id)
                    candidates.append(item)
            next_page = payload.get("next_page_token")
            if not next_page or next_page == page_token:
                break
            page_token = str(next_page)
    return candidates

def fetch_activity(token: str, activity_id: str) -> dict:
    return request_json(f"{API_BASE}/activities/{activity_id}", token=token)

def make_date_label(activity: dict, locale: str) -> str:
    translations = activity.get("translations") or {}
    if locale == "fr":
        return html_text(activity.get("date_description")) or "Voir les dates sur Paris.fr"
    if locale == "en":
        return html_text((translations.get("en") or {}).get("date_description")) or "See dates on Paris.fr"
    return html_text((translations.get("zh") or {}).get("date_description")) or "见活动页面"

def source_url(activity: dict) -> str:
    return (activity.get("extras") or {}).get("url") or activity.get("access_link") or f"{API_BASE}{activity.get('self_link', '')}"

def price_label(activity: dict, locale: str) -> str:
    price = activity.get("price_type") or ""
    if price == "gratuit":
        return {"zh": "免费", "en": "free", "fr": "gratuit"}[locale]
    return price or {"zh": "见活动页面", "en": "see event page", "fr": "voir la page de l'evenement"}[locale]

def audience_label(activity: dict, locale: str) -> str:
    audience = activity.get("audience") or ""
    if audience == "Tout public.":
        return {"zh": "所有观众", "en": "All audiences", "fr": "Tout public"}[locale]
    return audience or {"zh": "所有观众", "en": "All audiences", "fr": "Tout public"}[locale]

@dataclass
class LocalizedArticle:
    locale: str
    title: str
    description: str
    category: str
    tags: list[str]
    cover_alt: str
    body: str

def build_localized(activity: dict, slug: str) -> list[LocalizedArticle]:
    translations = activity.get("translations") or {}
    en = translations.get("en") or {}
    zh = translations.get("zh") or {}
    venue = activity.get("address_name") or "Paris"
    street = activity.get("address_street") or ""
    city = activity.get("address_city") or "Paris"
    src = source_url(activity)
    title_fr = activity.get("title") or "Exposition a Paris"
    title_en = en.get("title") or title_fr
    title_zh = zh.get("title") or title_fr
    lead_fr = html_text(activity.get("lead_text")) or title_fr
    lead_en = html_text(en.get("lead_text")) or lead_fr
    lead_zh = html_text(zh.get("lead_text")) or lead_fr
    return [
        LocalizedArticle("zh", f"{title_zh}：巴黎展览推荐", f"Artiou 推荐 {venue} 的展览「{title_zh}」，适合加入近期巴黎观展清单。", "展览", ["展览", "当代艺术", "巴黎"], f"{title_zh} 活动图片", f"""## 展览概览

{lead_zh}

## 为什么值得加入观展清单

这场活动来自 Vision API 的巴黎展览数据，结合地点、时间和主题，适合正在寻找巴黎当代艺术、摄影或展览活动的观众。Artiou 会持续挑选可看性强、信息完整的展览，方便用户把线上的灵感带进真实展厅。

## 实用信息

- 日期：{make_date_label(activity, 'zh')}
- 地点：{venue}，{street}，{city}
- 票价：{price_label(activity, 'zh')}
- 适合人群：{audience_label(activity, 'zh')}

来源：[Paris.fr]({src})
"""),
        LocalizedArticle("en", f"{title_en}: an Artiou exhibition pick in Paris", f"Artiou recommends {title_en}, an exhibition at {venue} for visitors planning a cultural stop in Paris.", "Exhibition", ["exhibition", "contemporary art", "Paris"], f"{title_en} exhibition image", f"""## Exhibition overview

{lead_en}

## Why it belongs on your museum list

This pick comes from Vision API's Paris activity data and is selected for visitors looking for current exhibitions, contemporary art, photography, or cultural events around Paris. Artiou turns these listings into concise museum-going notes so readers can move from discovery to an actual visit.

## Practical details

- Dates: {make_date_label(activity, 'en')}
- Venue: {venue}, {street}, {city}
- Price: {price_label(activity, 'en')}
- Audience: {audience_label(activity, 'en')}

Source: [Paris.fr]({src})
"""),
        LocalizedArticle("fr", f"{title_fr} : la selection exposition d'Artiou", f"Artiou recommande {title_fr}, une exposition a decouvrir a {venue} pour une prochaine sortie culturelle.", "Exposition", ["exposition", "art contemporain", "Paris"], f"Image de l'exposition {title_fr}", f"""## Apercu de l'exposition

{lead_fr}

## Pourquoi l'ajouter a votre agenda

Cette selection vient des donnees d'activites parisiennes de Vision API et met en avant une exposition utile pour les visiteurs qui cherchent une sortie culturelle actuelle, lisible et facile a planifier. Artiou transforme ces informations en notes courtes pour passer plus simplement de la decouverte a la visite.

## Informations pratiques

- Dates : {make_date_label(activity, 'fr')}
- Lieu : {venue}, {street}, {city}
- Tarif : {price_label(activity, 'fr')}
- Public : {audience_label(activity, 'fr')}

Source : [Paris.fr]({src})
"""),
    ]

def write_article(activity: dict, localized: LocalizedArticle, date: str, slug: str) -> Path:
    target = CONTENT_ROOT / localized.locale / f"{date}-{slug}.md"
    event_price = "0" if activity.get("price_type") == "gratuit" else ""
    event_currency = "EUR" if event_price else ""
    meta = {
        "title": localized.title,
        "description": localized.description,
        "slug": slug,
        "date": date,
        "updated": date,
        "author": ARTICLE_AUTHOR,
        "category": localized.category,
        "activityId": activity.get("activity_id") or "",
        "coverImage": activity.get("cover_url") or "",
        "coverAlt": localized.cover_alt,
        "eventStartDate": activity.get("date_start") or "",
        "eventEndDate": activity.get("date_end") or "",
        "eventLocationName": activity.get("address_name") or "",
        "eventStreetAddress": activity.get("address_street") or "",
        "eventAddressLocality": activity.get("address_city") or "",
        "eventPostalCode": activity.get("address_zipcode") or "",
        "eventAddressCountry": "FR",
        "eventPrice": event_price,
        "eventCurrency": event_currency,
        "sourceUrl": source_url(activity),
    }
    lines = ["---"]
    for key, value in meta.items():
        if value != "":
            lines.append(f"{key}: {frontmatter_value(value)}")
    lines.append(f"tags: [{', '.join(localized.tags)}]")
    lines.append("---")
    lines.append("")
    lines.append(localized.body.strip())
    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target

def pick_activity(candidates: list[dict], processed: set[str]) -> dict | None:
    for item in candidates:
        activity_id = item.get("activity_id")
        if not activity_id or activity_id in processed:
            continue
        title = item.get("title") or ""
        tags = set(item.get("qfap_tags") or [])
        if "Expo" in tags or "Art contemporain" in tags or "Photo" in tags or "Peinture" in tags or "exposition" in title.lower():
            return item
    return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()
    token = get_token()
    processed = load_processed()
    candidates = fetch_candidates(token, args.max_pages)
    picked = pick_activity(candidates, processed)
    if not picked:
        print("No unprocessed exhibition activity found.")
        return 0
    activity = fetch_activity(token, picked["activity_id"])
    title_for_slug = (activity.get("translations") or {}).get("en", {}).get("title") or activity.get("title") or picked["activity_id"]
    slug = slugify(title_for_slug)
    while any((CONTENT_ROOT / locale / f"{args.date}-{slug}.md").exists() for locale in ["zh", "en", "fr"]):
        slug = slugify(f"{title_for_slug}-{picked['activity_id'][:8]}")
    print(f"Selected {picked['activity_id']}: {activity.get('title')}")
    print(f"Slug: {slug}")
    if args.dry_run:
        return 0
    written = []
    for localized in build_localized(activity, slug):
        written.append(write_article(activity, localized, args.date, slug))
    if not args.no_build:
        subprocess.run(["node", str(BUILD_SCRIPT)], cwd=str(SITE_ROOT), check=True)
    processed.add(picked["activity_id"])
    save_processed(processed)
    for path in written:
        print(path.relative_to(SITE_ROOT))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
