#!/usr/bin/env python3
"""Generate Artiou exhibition news articles from Vision API."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = SITE_ROOT / "content" / "news"
STATE_FILE = SITE_ROOT / "scripts" / "processed_exhibitions.json"
LEGACY_STATE_FILE = SITE_ROOT / "scripts" / "processed_activity_news.json"
BUILD_SCRIPT = SITE_ROOT / "scripts" / "build-news.mjs"
API_BASE = "https://vision.ottozhang.com"
ARTICLE_AUTHOR = "Artiou Team"

EXHIBITION_KEYWORDS = [
    "expo",
    "exposition",
    "exhibition",
    "art",
    "musee",
    "musée",
    "museum",
    "galerie",
    "gallery",
    "peinture",
    "sculpture",
    "photographie",
    "installation",
    "contemporary art",
    "art moderne",
    "art contemporain",
]

NEGATIVE_KEYWORDS = [
    "concert",
    "musique",
    "music",
    "spectacle",
    "theatre",
    "théâtre",
    "danse",
    "sport",
    "marché",
    "market",
    "atelier",
    "workshop",
    "conference",
    "conférence",
    "cinema",
    "cinéma",
]


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


def markdown_paragraphs_from_html(value: str | None) -> str:
    """Keep the source description complete while making it render as paragraphs."""
    text = value or ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)<p[^>]*>", "", text)
    text = re.sub(r"(?i)</?(em|strong|b|i)[^>]*>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text).replace("\xa0", " ")
    paragraphs = []
    for part in re.split(r"\n\s*\n", text):
        clean = re.sub(r"[ \t]+", " ", part).strip()
        if clean:
            paragraphs.append(clean)
    return "\n\n".join(paragraphs)


def request_json(
    url: str,
    token: str | None = None,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    req_headers = {"User-Agent": "ArtiouNewsBot/1.0"}
    if headers:
        req_headers.update(headers)
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=req_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def get_token() -> str:
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
    return value[:72].strip("-") or "artiou-exhibition"


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
                if line.startswith("sourceActivityId:") or line.startswith("activityId:"):
                    value = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if value:
                        ids.add(value)
                    break
        except OSError:
            continue
    return ids


def scan_existing_slugs() -> set[str]:
    slugs: set[str] = set()
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
                if line.startswith("slug:"):
                    value = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if value:
                        slugs.add(value)
                    break
        except OSError:
            continue
    return slugs


def load_processed() -> set[str]:
    processed = scan_existing_activity_ids()
    for state_path in [STATE_FILE, LEGACY_STATE_FILE]:
        if not state_path.exists():
            continue
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                processed.update(str(item) for item in data)
            elif isinstance(data, dict):
                processed.update(str(item) for item in data.get("activity_ids", []))
        except json.JSONDecodeError:
            pass
    return processed


def save_processed(processed: set[str]) -> None:
    STATE_FILE.write_text(json.dumps({"activity_ids": sorted(processed)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def date_range(start_date: str, days: int) -> list[str]:
    start = datetime.fromisoformat(start_date).date()
    return [(start + timedelta(days=offset)).isoformat() for offset in range(days)]


def fetch_candidates(token: str, selected_dates: list[str], max_pages: int) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    for selected_date in selected_dates:
        page_token = "1"
        for _ in range(max_pages):
            params = urllib.parse.urlencode({"page_size": 50, "selected_date": selected_date, "page_token": page_token})
            payload = request_json(f"{API_BASE}/activities/?{params}", token=token)
            for item in payload.get("contents", []):
                activity_id = item.get("activity_id")
                if activity_id and activity_id not in seen:
                    item["_selected_date"] = selected_date
                    candidates.append(item)
                    seen.add(activity_id)
            next_page = payload.get("next_page_token")
            if not next_page or str(next_page) == page_token:
                break
            page_token = str(next_page)
    return candidates


def fetch_activity(token: str, activity_id: str) -> dict:
    return request_json(f"{API_BASE}/activities/{activity_id}", token=token)


def translated(activity: dict, locale: str, field: str) -> str:
    translations = activity.get("translations") or {}
    return ((translations.get(locale) or {}).get(field) or "").strip()


def localized_title(activity: dict, locale: str) -> str:
    translated_titles = activity.get("translated_titles") or {}
    if isinstance(translated_titles, dict) and translated_titles.get(locale):
        return str(translated_titles[locale]).strip()
    return translated(activity, locale, "title") or activity.get("title") or "Exposition a Paris"


def localized_description_text(activity: dict, locale: str) -> str:
    raw = translated(activity, locale, "description") or activity.get("description") or ""
    return markdown_paragraphs_from_html(raw)


def make_date_label(activity: dict, locale: str) -> str:
    if locale == "fr":
        return html_text(translated(activity, "fr", "date_description") or activity.get("date_description")) or "Voir les dates sur la page de l'événement"
    if locale == "en":
        return html_text(translated(activity, "en", "date_description") or activity.get("date_description")) or "See dates on the event page"
    return html_text(translated(activity, "zh", "date_description") or activity.get("date_description")) or "见活动页面"


def source_url(activity: dict) -> str:
    return (activity.get("extras") or {}).get("url") or activity.get("contact_url") or activity.get("access_link") or f"{API_BASE}{activity.get('self_link', '')}"


def price_label(activity: dict, locale: str) -> str:
    price = activity.get("price_detail") or activity.get("price_type") or ""
    if activity.get("price_type") == "gratuit":
        return {"zh": "免费", "en": "free", "fr": "gratuit"}[locale]
    return html_text(price) or {"zh": "见活动页面", "en": "see event page", "fr": "voir la page de l'événement"}[locale]


def audience_label(activity: dict, locale: str) -> str:
    audience = activity.get("audience") or ""
    if audience == "Tout public.":
        return {"zh": "所有观众", "en": "All audiences", "fr": "Tout public"}[locale]
    return audience or {"zh": "所有观众", "en": "All audiences", "fr": "Tout public"}[locale]


def searchable_text(activity: dict) -> str:
    parts: list[str] = []
    for key in ["title", "description", "lead_text", "address_name", "category", "type"]:
        value = activity.get(key)
        if isinstance(value, str):
            parts.append(html_text(value))
    for key in ["qfap_tags", "universe_tags"]:
        value = activity.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts).lower()


def exhibition_score(activity: dict) -> int:
    text = searchable_text(activity)
    title = (activity.get("title") or "").lower()
    venue = (activity.get("address_name") or "").lower()
    tags = {str(item).lower() for item in (activity.get("qfap_tags") or [])}
    strong_tags = {"expo", "art contemporain", "peinture", "photo"}
    negative_tags = {"concert", "musique", "théâtre", "theatre", "sport", "loisirs", "atelier", "conférence", "conference"}
    negative_title = (
        "conférence",
        "conference",
        "représentation",
        "representation",
        "journée",
        "journee",
        "sortie",
        "atelier",
        "forum",
        "nuit des musées",
        "nuit des musees",
    )
    if tags & negative_tags:
        return -100
    if any(word in title for word in negative_title):
        return -100
    if any(word in text for word in NEGATIVE_KEYWORDS) and not (strong_tags & tags):
        return -100
    exhibition_title = any(word in title for word in ["exposition", "exhibition", "expo"])
    exhibition_venue = any(word in venue for word in ["musée", "musee", "museum", "galerie", "gallery"])
    if not (exhibition_title or exhibition_venue or "expo" in tags):
        return -100
    score = 0
    for keyword in EXHIBITION_KEYWORDS:
        if keyword in text:
            score += 3
    if "expo" in tags:
        score += 12
    if exhibition_title:
        score += 10
    if exhibition_venue:
        score += 8
    if strong_tags & tags:
        score += 8
    if activity.get("cover_url"):
        score += 3
    if activity.get("address_name"):
        score += 2
    if activity.get("date_start") and activity.get("date_end"):
        score += 2
    if source_url(activity):
        score += 1
    return score


@dataclass
class LocalizedArticle:
    locale: str
    title: str
    description: str
    category: str
    tags: list[str]
    cover_alt: str
    body: str


def build_localized(activity: dict) -> list[LocalizedArticle]:
    venue = activity.get("address_name") or "Paris"
    street = activity.get("address_street") or ""
    city = activity.get("address_city") or "Paris"
    src = source_url(activity)
    title_fr = localized_title(activity, "fr")
    title_en = localized_title(activity, "en")
    title_zh = localized_title(activity, "zh")
    lead_fr = html_text(translated(activity, "fr", "lead_text") or activity.get("lead_text")) or title_fr
    lead_en = html_text(translated(activity, "en", "lead_text") or activity.get("lead_text")) or title_en
    lead_zh = html_text(translated(activity, "zh", "lead_text") or activity.get("lead_text")) or title_zh
    about_fr = localized_description_text(activity, "fr")
    about_en = localized_description_text(activity, "en")
    about_zh = localized_description_text(activity, "zh")
    return [
        LocalizedArticle("zh", f"{title_zh}：巴黎展览推荐", f"Artiou 推荐 {venue} 的展览「{title_zh}」，适合加入近期巴黎观展清单。", "展览", ["展览", "艺术", "巴黎"], f"{title_zh} 活动图片", f"""## 展览导览

{lead_zh}

## 实用信息

- 日期：{make_date_label(activity, 'zh')}
- 地点：{venue}，{street}，{city}
- 票价：{price_label(activity, 'zh')}
- 适合人群：{audience_label(activity, 'zh')}
- 来源：[活动页面]({src})

## 关于展览

{about_zh}
"""),
        LocalizedArticle("en", f"{title_en}: an Artiou exhibition pick in Paris", f"Artiou recommends {title_en}, an exhibition at {venue} for visitors planning an art-focused stop in Paris.", "Exhibition", ["exhibition", "art", "Paris"], f"{title_en} exhibition image", f"""## Exhibition guide

{lead_en}

## Visit details

- Dates: {make_date_label(activity, 'en')}
- Venue: {venue}, {street}, {city}
- Price: {price_label(activity, 'en')}
- Audience: {audience_label(activity, 'en')}
- Source: [Event page]({src})

## About the exhibition

{about_en}
"""),
        LocalizedArticle("fr", f"{title_fr} : la sélection exposition d'Artiou", f"Artiou recommande {title_fr}, une exposition à découvrir à {venue} pour une prochaine sortie culturelle.", "Exposition", ["exposition", "art", "Paris"], f"Image de l'exposition {title_fr}", f"""## Guide d'exposition

{lead_fr}

## Informations pratiques

- Dates : {make_date_label(activity, 'fr')}
- Lieu : {venue}, {street}, {city}
- Tarif : {price_label(activity, 'fr')}
- Public : {audience_label(activity, 'fr')}
- Source : [Page de l'événement]({src})

## À propos de l'exposition

{about_fr}
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
        "coverImage": activity.get("cover_url") or "",
        "coverAlt": localized.cover_alt,
        "source": "Vision API",
        "sourceUrl": source_url(activity),
        "sourceActivityId": activity.get("activity_id") or "",
        "eventStartDate": activity.get("date_start") or "",
        "eventEndDate": activity.get("date_end") or "",
        "eventLocationName": activity.get("address_name") or "",
        "eventStreetAddress": activity.get("address_street") or "",
        "eventAddressLocality": activity.get("address_city") or "",
        "eventPostalCode": activity.get("address_zipcode") or "",
        "eventAddressCountry": "FR",
        "eventPrice": event_price,
        "eventCurrency": event_currency,
    }
    lines = ["---"]
    for key, value in meta.items():
        if value != "":
            lines.append(f'{key}: "{frontmatter_value(value)}"')
    lines.append(f"tags: [{', '.join(localized.tags)}]")
    lines.append("---")
    lines.append("")
    lines.append(localized.body.strip())
    lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def pick_activities(candidates: list[dict], processed: set[str], existing_slugs: set[str], per_day: int) -> list[dict]:
    by_day: dict[str, list[dict]] = {}
    for item in candidates:
        activity_id = item.get("activity_id")
        if not activity_id or activity_id in processed:
            continue
        score = exhibition_score(item)
        if score < 12:
            continue
        item["_score"] = score
        by_day.setdefault(item.get("_selected_date") or "", []).append(item)

    picked: list[dict] = []
    picked_ids: set[str] = set()
    for selected_date in sorted(by_day):
        day_items = sorted(by_day[selected_date], key=lambda item: item.get("_score", 0), reverse=True)
        day_count = 0
        for item in day_items:
            if day_count >= per_day:
                break
            activity_id = item.get("activity_id")
            if activity_id in picked_ids:
                continue
            title = item.get("title") or activity_id
            candidate_slug = slugify(title)
            if candidate_slug in existing_slugs:
                continue
            picked.append(item)
            picked_ids.add(activity_id)
            day_count += 1
    return picked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--days", type=int, default=8)
    parser.add_argument("--per-day", type=int, default=2)
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    token = get_token()
    processed = load_processed()
    existing_slugs = scan_existing_slugs()
    selected_dates = date_range(args.date, args.days)
    candidates = fetch_candidates(token, selected_dates, args.max_pages)
    picked_items = pick_activities(candidates, processed, existing_slugs, args.per_day)

    details: list[tuple[dict, str]] = []
    for picked in picked_items:
        activity = fetch_activity(token, picked["activity_id"])
        if exhibition_score(activity) < 12:
            continue
        title_for_slug = localized_title(activity, "en") or activity.get("title") or picked["activity_id"]
        slug = slugify(title_for_slug)
        if slug in existing_slugs:
            continue
        while any((CONTENT_ROOT / locale / f"{args.date}-{slug}.md").exists() for locale in ["zh", "en", "fr"]):
            slug = slugify(f"{title_for_slug}-{picked['activity_id'][:8]}")
        details.append((activity, slug))
        existing_slugs.add(slug)

    print(f"Scanned {len(candidates)} activities from {selected_dates[0]} to {selected_dates[-1]}.")
    if not details:
        print("No suitable exhibition activity found.")
        return 0

    for activity, slug in details:
        print(f"Selected {activity.get('activity_id')}: {activity.get('title')} [{slug}]")
    if args.dry_run:
        return 0

    written: list[Path] = []
    description_sources: list[str] = []
    for activity, slug in details:
        for localized in build_localized(activity):
            written.append(write_article(activity, localized, args.date, slug))
        for locale in ["zh", "en", "fr"]:
            source = "translations" if translated(activity, locale, "description") else "original"
            description_sources.append(f"{activity.get('activity_id')}:{locale}:{source}")
        processed.add(activity["activity_id"])

    if not args.no_build:
        subprocess.run(["node", str(BUILD_SCRIPT)], cwd=str(SITE_ROOT), check=True)
    save_processed(processed)

    for path in written:
        print(path.relative_to(SITE_ROOT))
    print("Description sources: " + ", ".join(description_sources))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
