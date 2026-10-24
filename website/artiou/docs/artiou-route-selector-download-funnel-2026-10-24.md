# Artiou route-selector → download funnel audit (2026-10-24)

## Scope and data limits

Read-only Umami audit for `www.artiou.com`, 28-day UTC window ending 2026-10-24 23:59. Website ID `6f206180-48a8-454d-a1af-a8f45fdee150`. No site or analytics changes. Current definitions cross-checked against `analytics-events.md` and `artiou_zh_cta_baseline_2026-09-09.md`.

## Funnel (observed events, not a conversion rate)

```text
route planning engagement
route_selector_click       19
         │ session linkage is available on raw event rows, but not in aggregate metrics
         ├── guide download intent: guide_download_click  0 in aggregate readback
         ├── homepage download intent: homepage_download_click  9 (different aggregate; not proven downstream)
         ├── guide engagement: guide_cta_click             1 (not a download)
         └── guide navigation: guide_internal_link_click   2 (not a download)
```

The event aggregate reports the counts above. Zero `guide_download_click` means it was absent from the returned event aggregate, not proof no one downloaded. Aggregate counts cannot establish sequence or denominator; do not compute 9/19 as conversion.

## Definitions and dimensions

| Event | Meaning / trigger | Relevant attributes |
|---|---|---|
| `route_selector_click` | Guide route/details interaction; planning engagement only | `page`, `path`, `page_path`, `source_path`, `language`, `source_page_type`, plus `text`, `cta_location`, `section_hint` |
| `homepage_download_click` | Homepage App Store / Play Store / download-section click | Same page context; `href_host`, `href_path`, `target_path`, `download_target`, `store_platform`, `cta_location`, `text` |
| `guide_download_click` | Guide-page App Store / Play Store / download-section click | Same page context and destination/CTA attributes |
| `guide_cta_click` | Non-download guide button/anchor | Page context, `text`, `cta_location`, `cta_type`; engagement only |
| `guide_internal_link_click` | Navigation from one guide page to another | Page context and internal `target_path`; navigation only |

Context includes source URL/path and language, so route clicks can be segmented in raw event rows. Raw `/events` readback returned 158 rows over two pages; 23 had named events. In those named rows, route events were seen on `/zh/paris-museum-guide/` (7), `/en/mona-lisa-guide/` (3), `/en/winged-victory-samothrace-guide/` (2), `/en/louvre-first-time-visitor-guide/` (1), and `/fr/london-museum-guide/` (1). Homepage download events in that sample: `/en/` 6 and `/en/#download` 1. These are a partial raw-event sample, not exhaustive per-path totals.

Aggregate language dimension: en 106, fr 7, zh 5, es 2, da/ko/pl/ru/sv/de/ar 1 each. Device: laptop 81, mobile 43, desktop 3. Umami aggregate dimensions are not cross-tabulated with event type; do not infer event-by-language/device rates from these totals.

## Can the steps be connected?

Yes, individual raw rows carry `sessionId`; the sampled readback included route-selector events with session IDs and timestamps, so session-level linkage is technically possible. However, only 23 named events were present in the 158-row sampled page set. Four route-containing sessions were visible in that sample; none showed a download event in the same observed session. This is not a complete population and cannot support a session conversion estimate. The aggregate endpoint does not provide an event-by-path/language/device cross-tab or a funnel report.

The current instrumentation therefore supports a future privacy-conscious funnel without a new identifier: group existing events by Umami `sessionId`, event name and timestamp, retaining source path/language and device. Do not export IP or city, add cross-site identifiers, or log raw UTM values. For a reliable baseline, fetch all event pages for a fixed window and deduplicate event rows; report route sessions with a later download event divided by route sessions, separately by language/device. Keep homepage-download and guide-download outcomes distinct.

## CTA/page spot-check

All four target pages returned HTTP 200 on 2026-10-24:

- `https://www.artiou.com/en/` — 25,293 bytes
- `https://www.artiou.com/zh/` — 23,686 bytes
- `https://www.artiou.com/en/louvre-first-time-visitor-guide/` — 19,993 bytes
- `https://www.artiou.com/zh/paris-museum-guide/` — 44,103 bytes

The English homepage has homepage download CTAs; the Chinese homepage provides the download section. The English Louvre and Chinese Paris guide pages expose route planning and guide/download CTAs. Existing public-page checks and the live event definitions confirm the current instrumentation; no evidence justifies a UX or code change in this audit.

## Outcome

No new instrumentation was added, so no collector success is presented as acceptance evidence. Existing real named-event aggregates were read back from Umami. The session-level conversion rate remains unavailable from this partial raw-event sample; the next measurement should use complete event pagination and `sessionId` sequencing. This is an analysis/evidence deliverable only: no website, frontend, SEO page, static asset, or deployable code changed; **no deployment required**.
