# News Content Markdown Structure

`website/content/news/` uses locale subfolders:

- `zh/`
- `en/`
- `fr/`

Each activity/article is one markdown file in each locale folder, for example:

- `zh/2026-05-01-activity-slug.md`
- `en/2026-05-01-activity-slug.md`
- `fr/2026-05-01-activity-slug.md`

## Frontmatter template

```md
---
title: "Article title"
date: 2026-05-01
updated: 2026-05-01
slug: activity-slug
cover: /artiou/assets/example-cover.png
description: "Short summary shown on list and detail pages"
excerpt: "Optional short excerpt"
author: Artiou Editorial
category: "Exhibition News"
museum: "Venue name"
location: "City / district"
tags: ["Tag1", "Tag2", "Tag3"]
---

## Section title

Paragraph text.

- Bullet item
- Bullet item
```

## Field notes

- `slug`: must be URL-safe and consistent across `zh/en/fr`.
- `date` and `updated`: use `YYYY-MM-DD`.
- `cover`: image path or full URL.
- `description`: used in list cards, article header, and meta description.
- `category`: list card meta label.
- `tags`: rendered as chips.
- Markdown body supports headings (`##`, `###`), paragraphs, and list items.

## Build

After adding/updating markdown files, rebuild news pages:

```bash
cd website
node build-news.mjs
```

This build also regenerates `website/sitemap.xml`.
