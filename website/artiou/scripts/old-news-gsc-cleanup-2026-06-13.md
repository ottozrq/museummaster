# Artiou old news GSC residual cleanup audit — 2026-06-13

## Scope

Todoist card: `artiou P0：追踪并清除旧 news 404 的 GSC 索引残留`.

Primary target slug: `the-last-sun-by-emmanuel-rgent` across `en`, `zh`, and `fr`.

## GSC page-dimension residuals

Range: 2026-05-14 → 2026-06-10, property `sc-domain:artiou.com`.

News URLs still appearing in GSC page dimension:

| URL | Classification | Clicks | Impressions | Live status |
|---|---|---:|---:|---:|
| `https://www.artiou.com/en/news/` | retained hub | 0 | 2 | 200 |
| `https://www.artiou.com/en/news/artiou-newsroom-launch/` | retained editorial | 0 | 1 | 200 |
| `https://www.artiou.com/en/news/the-last-sun-by-emmanuel-rgent/` | deleted generated article | 0 | 1 | 404 |
| `https://www.artiou.com/fr/news/` | retained hub | 0 | 1 | 200 |
| `https://www.artiou.com/fr/news/the-last-sun-by-emmanuel-rgent/` | deleted generated article | 0 | 1 | 404 |
| `https://www.artiou.com/zh/news/` | retained hub | 0 | 1 | 200 |
| `https://www.artiou.com/zh/news/artiou-newsroom-launch/` | retained editorial | 0 | 4 | 200 |

Deleted old-news residual total: 2 URLs / 2 impressions / 0 clicks in the current 28-day GSC page window.

## URL Inspection snapshot

| URL | Live | URL Inspection coverage | Last crawl |
|---|---:|---|---|
| `https://www.artiou.com/en/news/the-last-sun-by-emmanuel-rgent/` | 404 | Submitted and indexed | 2026-05-11T02:42:05Z |
| `https://www.artiou.com/zh/news/the-last-sun-by-emmanuel-rgent/` | 404 | Submitted and indexed | 2026-05-16T13:07:48Z |
| `https://www.artiou.com/fr/news/the-last-sun-by-emmanuel-rgent/` | 404 | Submitted and indexed | 2026-05-11T02:42:57Z |

Interpretation: live site is already serving removal signals (`404`) for all three target URLs, but Google has not recrawled them since May and still reports the stale indexed state.

## Sitemap verification

Live `https://www.artiou.com/sitemap.xml`:

- URL count: 70
- `/news/` URL count: 0
- contains `the-last-sun`: false

This confirms old news is not being resubmitted through the live sitemap.

## Action taken / blocker

Completed in this run:

- Re-listed GSC page dimension and split old news into retained hub/editorial vs deleted generated articles.
- Rechecked live HTTP status for `the-last-sun` in `en`, `zh`, and `fr`: all return `404`.
- Re-ran URL Inspection for all three `the-last-sun` locales: all still stale `Submitted and indexed`.
- Reconfirmed live sitemap has zero news URLs and does not contain `the-last-sun`.

Blocked from fully clearing in this autonomous cron run:

- Search Console Removals has no public API available through the existing GSC API token.
- Browser access to Search Console requires an interactive Google login in this cron context.
- Returning `410` requires production nginx/server config access; the repository static site can only verify/maintain the current `404` behavior.

Recommended next action: in an interactive authenticated Search Console session, submit temporary removals for the three `the-last-sun` URLs, or add production nginx `return 410` rules for `/en|zh|fr/news/the-last-sun-by-emmanuel-rgent/` and redeploy/reload nginx. After that, re-run this audit and move the card to REVIEW once URL Inspection no longer reports `Submitted and indexed` or the removals are visible.

Raw audit artifact: `/Users/otto/.hermes/tmp/artiou_old_news_gsc_audit_2026_06_13.json`.
