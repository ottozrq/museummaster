# Artiou Umami event model

Last updated: 2026-06-13

## Download / App Store CTA events

Use exactly one core event per user click. Do not emit both a generic CTA event and a download event for the same click.

| Event | When it fires | Funnel use |
| --- | --- | --- |
| `download_click` | Sitewide/homepage download CTAs, App Store links, Google Play links, or `#download` CTAs that are not on guide pages | Homepage/sitewide → download intent |
| `guide_download_click` | Museum guide page download CTAs, App Store links, Google Play links, or `#download` CTAs | Guide landing → download intent |
| `guide_cta_click` | Non-download guide-page buttons/anchors | Guide engagement, not download intent |
| `guide_internal_link_click` | Clicks from one guide page to another guide page | Guide cluster navigation |
| `route_selector_click` | Route selector/detail interactions on guide pages | Guide planning engagement |

Deprecated/legacy names from earlier reports: `app_download_click`, `app_store_click`. Treat them as historical aliases only; new weekly reports should explain them separately from the current model and should not combine them with current `download_click` / `guide_download_click` without noting the instrumentation change.

## Common properties

`static-site.js` attaches page context to every event:

- `page`, `path`, `page_path`: current `window.location.pathname`
- `language`: page language inferred from `<html lang>` or URL prefix

Download events also include:

- `href`: destination URL or anchor
- `target_path`: internal guide target when relevant, otherwise empty
- `text`: clicked link text, trimmed
- `source_page_type`: `guide` or `sitewide`
- `cta_location`: `hero`, `footer`, `guide-card`, `nav`, or `body`

## Weekly report interpretation

For low-sample weekly Umami checks:

1. Report current events by exact event name first.
2. For guide → download funnel, use guide page landings (`/en/*guide/`, `/zh/*guide/`, `/fr/*guide/`) as the landing denominator and `guide_download_click` as the download numerator.
3. Use `download_click` for homepage/sitewide download intent only.
4. If legacy `app_store_click` or `app_download_click` appears in historical ranges, flag it as pre-cleanup instrumentation rather than a separate current funnel step.
5. A week with zero events can be low traffic or a tracking issue; verify live `static-site.js` and one manual click before interpreting conversion.
