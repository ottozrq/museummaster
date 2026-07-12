# Artiou Umami event model

Last updated: 2026-07-12

## Download / App Store CTA events

Use exactly one core event per user click. Do not emit both a generic CTA event and a download event for the same click.

| Event | When it fires | Funnel use |
| --- | --- | --- |
| `homepage_download_click` | Homepage download CTAs, App Store links, Google Play links, or `#download` CTAs | Homepage → download intent |
| `guide_download_click` | City/museum guide page download CTAs, App Store links, Google Play links, or `#download` CTAs | Guide landing → download intent |
| `entity_download_click` | Artwork/entity guide page download CTAs, App Store links, Google Play links, or `#download` CTAs | Entity landing → download intent |
| `guide_cta_click` | Non-download guide-page buttons/anchors | Guide engagement, not download intent |
| `guide_internal_link_click` | Clicks from one guide page to another guide page | Guide cluster navigation |
| `route_selector_click` | Route selector/detail interactions on guide pages | Guide planning engagement |

Deprecated/legacy names from earlier reports: `download_click`, `app_download_click`, `app_store_click`. Treat them as historical aliases only; new weekly reports should explain them separately from the current three-step model.

## Common properties

`static-site.js` attaches page context to every event:

- `page`, `path`, `page_path`, `source_path`: current `window.location.pathname`
- `language`: page language inferred from `<html lang>` or URL prefix
- `source_page_type`: `homepage`, `museum_guide`, `entity_page`, or `sitewide`
- `has_utm_source`, `has_utm_medium`, `has_utm_campaign`: coarse presence flags (`1`/`0`); raw query values are intentionally not collected

Download events also include:

- `href_host`, `href_path`: destination host/path without query strings
- `source_path`: current `window.location.pathname` for source-page filtering
- `target_path`: internal guide target when relevant, otherwise empty
- `text`: clicked link text, trimmed
- `source_page_type`: page classification above
- `cta_location`: `hero`, `footer`, `guide-card`, `nav`, or `body`
- `download_target`: `app_store`, `play_store`, `download_section`, or `unknown`
- `store_platform`: `ios`, `android`, `none`, or `unknown`

## Weekly report interpretation

For low-sample weekly Umami checks:

1. Report current events by exact event name first.
2. For guide → download funnel, use guide page landings (`/en/*guide/`, `/zh/*guide/`, `/fr/*guide/`) as the landing denominator and `guide_download_click` as the download numerator.
3. Use `homepage_download_click` for homepage intent and `entity_download_click` for artwork/entity intent.
4. If legacy `download_click`, `app_store_click`, or `app_download_click` appears in historical ranges, flag it as pre-cleanup instrumentation rather than a separate current funnel step.
5. A week with zero events can be low traffic or a tracking issue; verify live `static-site.js` and one manual click before interpreting conversion.
