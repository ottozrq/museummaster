#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEBSITE_DIR = SCRIPT_DIR;
const CONTENT_ROOT = path.join(SCRIPT_DIR, "content", "news");
const TEMPLATES_DIR = path.join(SCRIPT_DIR, "templates");
const SITEMAP_PATH = path.join(WEBSITE_DIR, "sitemap.xml");
const SITEMAP_CORE_PATH = path.join(SCRIPT_DIR, "sitemap-core.xml");
const SITE_URL = "https://www.artiou.com";

const LOCALES = ["zh", "en", "fr"];

const HREFLANG = { zh: "zh-CN", en: "en-US", fr: "fr-FR" };

/** UI copy + meta for each news locale */
const LOCALE_UI = {
  zh: {
    htmlLang: "zh-CN",
    ogLocale: "zh_CN",
    dateLocale: "zh-CN",
    index: {
      pageTitle: "Artiou 展览资讯 | 巴黎生活与产品更新",
      pageDescription:
        "Artiou 展览资讯持续发布巴黎美术馆展览相关资讯，帮助用户快速获得实用出行信息。",
      heroTitle: "Artiou 展览资讯",
      heroDescription:
        "面向巴黎本地生活场景，持续发布可执行的实用资讯与产品更新。",
      kicker: "Artiou 内容中心",
    },
    nav: {
      home: "官网首页",
      features: "核心功能",
      news: "新闻站",
    },
    footerRights: "保留所有权利。",
    articleCta: {
      title: "用 Artiou 获取巴黎实时生活信息",
      desc: "拍照识别展品，获取专业中文讲解，轻松探索艺术世界。",
      button: "下载 Artiou",
    },
  },
  en: {
    htmlLang: "en-US",
    ogLocale: "en_US",
    dateLocale: "en-US",
    index: {
      pageTitle: "Artiou News | Paris tips & product updates",
      pageDescription:
        "Art guides and exhibitions at Paris museums — from the Artiou team.",
      heroTitle: "Artiou News",
      heroDescription:
        "Practical Paris living tips and product news, written to be easy to scan and act on.",
      kicker: "Artiou editorial",
    },
    nav: {
      home: "Home",
      features: "Features",
      news: "News",
    },
    footerRights: "All rights reserved.",
    articleCta: {
      title: "Live Paris info with Artiou",
      desc: "Scan artworks, get expert commentary, explore art easily.",
      button: "下载 Artiou",
    },
  },
  fr: {
    htmlLang: "fr-FR",
    ogLocale: "fr_FR",
    dateLocale: "fr-FR",
    index: {
      pageTitle: "Artiou Actualités | Paris et produit",
      pageDescription:
        "Guides et expositions des musées de Paris — de l'équipe Artiou.",
      heroTitle: "Actualités Artiou",
      heroDescription:
        "Conseils concrets pour la vie parisienne et nouveautés produit.",
      kicker: "Artiou éditorial",
    },
    nav: {
      home: "Accueil",
      features: "Fonctionnalités",
      news: "Actualités",
    },
    footerRights: "Tous droits réservés.",
    articleCta: {
      title: "Paris en temps réel avec Artiou",
      desc: "Scannez les œuvres, Obtenez des commentaries, Explorez l'art facilement.",
      button: "Télécharger Artiou",
    },
  },
};

function escapeHtml(value = "") {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(dateValue, dateLocale) {
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) {
    return dateValue;
  }
  return new Intl.DateTimeFormat(dateLocale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function parseTags(rawTags = "") {
  const trimmed = rawTags.trim();
  if (!trimmed) {
    return [];
  }
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    return trimmed
      .slice(1, -1)
      .split(",")
      .map((item) => item.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
  }
  return trimmed
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseFrontmatter(fileContent) {
  if (!fileContent.startsWith("---\n")) {
    throw new Error("Markdown 文件缺少 frontmatter");
  }
  const endMarker = fileContent.indexOf("\n---\n", 4);
  if (endMarker === -1) {
    throw new Error("frontmatter 结束标记缺失");
  }

  const frontmatterBlock = fileContent.slice(4, endMarker);
  const body = fileContent.slice(endMarker + 5).trim();
  const meta = {};

  for (const line of frontmatterBlock.split("\n")) {
    if (!line.trim()) continue;
    const separator = line.indexOf(":");
    if (separator === -1) continue;
    const key = line.slice(0, separator).trim();
    let rawValue = line.slice(separator + 1).trim();
    if (
      (rawValue.startsWith('"') && rawValue.endsWith('"')) ||
      (rawValue.startsWith("'") && rawValue.endsWith("'"))
    ) {
      rawValue = rawValue.slice(1, -1);
    }
    meta[key] = rawValue;
  }

  meta.tags = parseTags(meta.tags || "");
  return { meta, body };
}

function markdownToHtml(markdown) {
  const lines = markdown.split("\n");
  const html = [];
  let inList = false;

  function closeList() {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      continue;
    }

    if (line.startsWith("### ")) {
      closeList();
      html.push(`<h3>${escapeHtml(line.slice(4))}</h3>`);
      continue;
    }
    if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
      continue;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${escapeHtml(line.slice(2))}</li>`);
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      const content = line.replace(/^\d+\.\s+/, "");
      html.push(`<li>${escapeHtml(content)}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${escapeHtml(line)}</p>`);
  }

  closeList();
  return html.join("\n");
}

function ensureRequiredFields(meta, sourceFile) {
  const required = [
    "title",
    "description",
    "slug",
    "date",
    "updated",
    "author",
    "category",
  ];
  for (const field of required) {
    if (!meta[field]) {
      throw new Error(`${sourceFile} 缺少必填字段: ${field}`);
    }
  }
}

function renderTemplate(template, replacements) {
  return Object.entries(replacements).reduce(
    (output, [key, value]) =>
      output.replaceAll(`{{${key}}}`, value == null ? "" : String(value)),
    template,
  );
}

/** Per-locale URL & asset paths */
function getLocalePaths(locale) {
  // 静态资源一律用站点根绝对路径，避免当某条路由误返回首页 HTML 时相对路径解析到错误目录
  //（例如 /news/script.js 返回 HTML → Unexpected token '<'）。
  const assetRoot = "/";
  if (locale === "zh") {
    return {
      newsRootDir: path.join(WEBSITE_DIR, "news"),
      newsIndexUrl: "/news/",
      articlePath: (slug) => `/news/${slug}/`,
      siteNewsIndexUrl: `${SITE_URL}/news/`,
      siteArticleUrl: (slug) => `${SITE_URL}/news/${slug}/`,
      assetIndex: assetRoot,
      assetArticle: assetRoot,
    };
  }
  return {
    newsRootDir: path.join(WEBSITE_DIR, locale, "news"),
    newsIndexUrl: `/${locale}/news/`,
    articlePath: (slug) => `/${locale}/news/${slug}/`,
    siteNewsIndexUrl: `${SITE_URL}/${locale}/news/`,
    siteArticleUrl: (slug) => `${SITE_URL}/${locale}/news/${slug}/`,
    assetIndex: assetRoot,
    assetArticle: assetRoot,
  };
}

function getArticleCoverPath(article) {
  return article.cover || article.coverImage || "/artiou/assets/1F-e01f5905-7038-4137-a0c2-2ac1159af0b5.png";
}

function toAbsoluteImageUrl(imagePath) {
  if (/^https?:\/\//i.test(imagePath)) {
    return imagePath;
  }
  return `${SITE_URL}${imagePath}`;
}

function loadArticlesForLocale(locale) {
  const dir = path.join(CONTENT_ROOT, locale);
  if (!fs.existsSync(dir)) {
    return [];
  }
  const files = fs
    .readdirSync(dir)
    .filter((file) => file.endsWith(".md"))
    .sort();

  return files.map((file) => {
    const sourcePath = path.join(dir, file);
    const content = fs.readFileSync(sourcePath, "utf-8");
    const { meta, body } = parseFrontmatter(content);
    ensureRequiredFields(meta, `${locale}/${file}`);
    return {
      locale,
      ...meta,
      tags: meta.tags || [],
      bodyHtml: markdownToHtml(body),
      sourcePath,
    };
  });
}

function slugAvailability(byLocale, slug) {
  const set = {};
  for (const loc of LOCALES) {
    set[loc] = byLocale[loc].some((a) => a.slug === slug);
  }
  return set;
}

function articleRecordForSlug(byLocale, slug, locale) {
  return byLocale[locale].find((a) => a.slug === slug);
}

function buildHreflangArticle(slug, byLocale) {
  const avail = slugAvailability(byLocale, slug);
  const lines = [];
  for (const loc of LOCALES) {
    if (!avail[loc]) continue;
    const paths = getLocalePaths(loc);
    lines.push(`    <link rel="alternate" hreflang="${HREFLANG[loc]}" href="${paths.siteArticleUrl(slug)}">`);
  }
  const defaultLoc =
    LOCALES.find((l) => avail[l]) || "zh";
  lines.push(
    `    <link rel="alternate" hreflang="x-default" href="${getLocalePaths(defaultLoc).siteArticleUrl(slug)}">`,
  );
  return lines.join("\n");
}

function buildHreflangNewsIndices() {
  const lines = [];
  for (const loc of LOCALES) {
    const paths = getLocalePaths(loc);
    lines.push(`    <link rel="alternate" hreflang="${HREFLANG[loc]}" href="${paths.siteNewsIndexUrl}">`);
  }
  lines.push(`    <link rel="alternate" hreflang="x-default" href="${getLocalePaths("zh").siteNewsIndexUrl}">`);
  return lines.join("\n");
}

/** 新闻页顶栏：中 / EN / FR 入口，与官网语言切换一致 */
function buildLangSwitcherIndex(currentLocale) {
  const defs = [
    { loc: "zh", label: "中文" },
    { loc: "en", label: "EN" },
    { loc: "fr", label: "FR" },
  ];
  return defs
    .map(({ loc, label }) => {
      const paths = getLocalePaths(loc);
      const href = paths.newsIndexUrl;
      const active = loc === currentLocale ? " active" : "";
      return `                    <a href="${href}" class="lang-btn${active}">${label}</a>`;
    })
    .join("\n");
}

function buildLangSwitcherArticle(slug, currentLocale, byLocale) {
  const defs = [
    { loc: "zh", label: "中文" },
    { loc: "en", label: "EN" },
    { loc: "fr", label: "FR" },
  ];
  return defs
    .map(({ loc, label }) => {
      const paths = getLocalePaths(loc);
      const has = byLocale[loc].some((a) => a.slug === slug);
      const href = has ? paths.articlePath(slug) : paths.newsIndexUrl;
      const active = loc === currentLocale ? " active" : "";
      const title = has
        ? ""
        : ' title="该语言暂无此文章，将打开该语言新闻列表"';
      return `                    <a href="${href}" class="lang-btn${active}"${title}>${label}</a>`;
    })
    .join("\n");
}

function schemaInLanguage(locale) {
  return locale === "zh" ? "zh-CN" : locale === "fr" ? "fr-FR" : "en-US";
}

function buildNavMenuItems(locale, variant) {
  const ui = LOCALE_UI[locale];
  const paths = getLocalePaths(locale);
  const ap = variant === "index" ? paths.assetIndex : paths.assetArticle;
  const newsHref = paths.newsIndexUrl;

  if (variant === "index") {
    return `
                    <li><a href="${ap}" class="nav-link">${escapeHtml(ui.nav.home)}</a></li>
                    <li><a href="${ap}#features" class="nav-link">${escapeHtml(ui.nav.features)}</a></li>
                    <li><a href="${newsHref}" class="nav-link">${escapeHtml(ui.nav.news)}</a></li>`;
  }
  return `
                    <li><a href="${ap}" class="nav-link">${escapeHtml(ui.nav.home)}</a></li>
                    <li><a href="${newsHref}" class="nav-link">${escapeHtml(ui.nav.news)}</a></li>`;
}

function writeArticlePagesForLocale(
  locale,
  articles,
  articleTemplate,
  byLocale,
) {
  const paths = getLocalePaths(locale);
  const ui = LOCALE_UI[locale];

  for (const article of articles) {
    const targetDir = path.join(paths.newsRootDir, article.slug);
    fs.mkdirSync(targetDir, { recursive: true });

    const canonicalUrl = paths.siteArticleUrl(article.slug);
    const hreflang = buildHreflangArticle(article.slug, byLocale);
    const coverPath = getArticleCoverPath(article);

    const articleJsonLd = JSON.stringify(
      {
        "@context": "https://schema.org",
        "@type": "Article",
        headline: article.title,
        inLanguage: schemaInLanguage(locale),
        datePublished: new Date(article.date).toISOString(),
        dateModified: new Date(article.updated).toISOString(),
        author: {
          "@type": "Organization",
          name: article.author,
        },
        publisher: {
          "@type": "Organization",
          name: "Artiou",
        },
        image: toAbsoluteImageUrl(coverPath),
        description: article.description,
        mainEntityOfPage: canonicalUrl,
      },
      null,
      2,
    );

    const tagsHtml = article.tags
      .map((tag) => `<span class="news-chip">${escapeHtml(tag)}</span>`)
      .join("");

    const html = renderTemplate(articleTemplate, {
      HTML_LANG: ui.htmlLang,
      HREFLANG_LINKS: hreflang,
      OG_LOCALE: ui.ogLocale,
      LANG_SWITCHER: buildLangSwitcherArticle(article.slug, locale, byLocale),
      ARTICLE_TITLE: escapeHtml(article.title),
      ARTICLE_HEADING: escapeHtml(article.title),
      ARTICLE_DESCRIPTION: escapeHtml(article.description),
      ARTICLE_CONTENT: article.bodyHtml,
      ARTICLE_CATEGORY: escapeHtml(article.category),
      ARTICLE_PUBLISHED_TIME: new Date(article.date).toISOString(),
      ARTICLE_MODIFIED_TIME: new Date(article.updated).toISOString(),
      ARTICLE_PUBLISHED_TEXT: escapeHtml(
        formatDate(article.date, ui.dateLocale),
      ),
      ARTICLE_OG_IMAGE: toAbsoluteImageUrl(coverPath),
      ARTICLE_COVER_IMAGE: coverPath,
      ARTICLE_COVER_ALT: escapeHtml(article.title),
      ARTICLE_TAGS: tagsHtml,
      ARTICLE_JSON_LD: articleJsonLd,
      CANONICAL_URL: canonicalUrl,
      ASSET_PREFIX: paths.assetArticle,
      NAV_MENU_ITEMS: buildNavMenuItems(locale, "article"),
      FOOTER_RIGHTS: escapeHtml(ui.footerRights),
      CTA_TITLE: escapeHtml(ui.articleCta.title),
      CTA_DESC: escapeHtml(ui.articleCta.desc),
      CTA_BUTTON: escapeHtml(ui.articleCta.button),
      CURRENT_YEAR: new Date().getFullYear(),
    });

    fs.writeFileSync(path.join(targetDir, "index.html"), html, "utf-8");
  }
}

function writeNewsIndexForLocale(locale, articles, indexTemplate) {
  const paths = getLocalePaths(locale);
  const ui = LOCALE_UI[locale];
  const idx = ui.index;

  const articleCards = articles
    .map((article) => {
      const tagsHtml = article.tags
        .slice(0, 4)
        .map((tag) => `<span class="news-chip">${escapeHtml(tag)}</span>`)
        .join("");
      const cardHref = paths.articlePath(article.slug);
      return `
        <a class="news-card" href="${cardHref}">
          <p class="news-card-meta">${escapeHtml(article.category)} · ${escapeHtml(formatDate(article.date, ui.dateLocale))}</p>
          <h2>${escapeHtml(article.title)}</h2>
          <p>${escapeHtml(article.description)}</p>
          <div class="news-chip-row">${tagsHtml}</div>
        </a>`;
    })
    .join("\n");

  const hreflang = buildHreflangNewsIndices();

  const html = renderTemplate(indexTemplate, {
    HTML_LANG: ui.htmlLang,
    HREFLANG_LINKS: hreflang,
    OG_LOCALE: ui.ogLocale,
    LANG_SWITCHER: buildLangSwitcherIndex(locale),
    PAGE_TITLE: escapeHtml(idx.pageTitle),
    PAGE_DESCRIPTION: escapeHtml(idx.pageDescription),
    CANONICAL_URL: paths.siteNewsIndexUrl,
    HERO_TITLE: escapeHtml(idx.heroTitle),
    HERO_DESCRIPTION: escapeHtml(idx.heroDescription),
    KICKER: escapeHtml(idx.kicker),
    ARTICLES: articleCards,
    ASSET_PREFIX: paths.assetIndex,
    NAV_MENU_ITEMS: buildNavMenuItems(locale, "index"),
    FOOTER_RIGHTS: escapeHtml(ui.footerRights),
    CURRENT_YEAR: new Date().getFullYear(),
  });

  fs.mkdirSync(paths.newsRootDir, { recursive: true });
  fs.writeFileSync(path.join(paths.newsRootDir, "index.html"), html, "utf-8");
}

function writeSitemap(byLocale) {
  const today = new Date().toISOString().slice(0, 10);
  if (!fs.existsSync(SITEMAP_CORE_PATH)) {
    throw new Error(`缺少静态 sitemap 片段: ${SITEMAP_CORE_PATH}`);
  }
  const core = fs.readFileSync(SITEMAP_CORE_PATH, "utf-8").trimEnd();

  const newsIndexBlocks = LOCALES.map((loc) => {
    const paths = getLocalePaths(loc);
    const links = LOCALES.map((l) => {
      const p = getLocalePaths(l);
      return `        <xhtml:link rel="alternate" hreflang="${HREFLANG[l]}" href="${p.siteNewsIndexUrl}"/>`;
    }).join("\n");
    const xDefault = `        <xhtml:link rel="alternate" hreflang="x-default" href="${getLocalePaths("zh").siteNewsIndexUrl}"/>`;
    return `    <url>
        <loc>${paths.siteNewsIndexUrl}</loc>
        <lastmod>${today}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
${links}
${xDefault}
    </url>`;
  }).join("\n");

  const slugSet = new Set();
  for (const loc of LOCALES) {
    for (const a of byLocale[loc]) {
      slugSet.add(a.slug);
    }
  }

  const articleBlocks = [...slugSet]
    .sort()
    .map((slug) => {
      const avail = slugAvailability(byLocale, slug);
      const blocks = [];
      for (const loc of LOCALES) {
        if (!avail[loc]) continue;
        const art = articleRecordForSlug(byLocale, slug, loc);
        const paths = getLocalePaths(loc);
        const alternates = LOCALES.filter((l) => avail[l])
          .map((l) => {
            const p = getLocalePaths(l);
            return `        <xhtml:link rel="alternate" hreflang="${HREFLANG[l]}" href="${p.siteArticleUrl(slug)}"/>`;
          })
          .join("\n");
        const defaultLoc = LOCALES.find((l) => avail[l]);
        const xDefault = `        <xhtml:link rel="alternate" hreflang="x-default" href="${getLocalePaths(defaultLoc).siteArticleUrl(slug)}"/>`;
        blocks.push(`    <url>
        <loc>${paths.siteArticleUrl(slug)}</loc>
        <lastmod>${art.updated || art.date}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
${alternates}
${xDefault}
    </url>`);
      }
      return blocks.join("\n");
    })
    .join("\n");

  const sitemap = `${core}\n${newsIndexBlocks}\n${articleBlocks}\n</urlset>\n`;
  fs.writeFileSync(SITEMAP_PATH, sitemap, "utf-8");
}

function main() {
  if (!fs.existsSync(CONTENT_ROOT)) {
    throw new Error(`找不到内容目录: ${CONTENT_ROOT}`);
  }

  const indexTemplate = fs.readFileSync(
    path.join(TEMPLATES_DIR, "news-index.html"),
    "utf-8",
  );
  const articleTemplate = fs.readFileSync(
    path.join(TEMPLATES_DIR, "news-article.html"),
    "utf-8",
  );

  const byLocale = {};
  let totalArticles = 0;
  for (const loc of LOCALES) {
    byLocale[loc] = loadArticlesForLocale(loc).sort(
      (a, b) => new Date(b.date) - new Date(a.date),
    );
    totalArticles += byLocale[loc].length;
  }

  for (const loc of LOCALES) {
    writeArticlePagesForLocale(loc, byLocale[loc], articleTemplate, byLocale);
    writeNewsIndexForLocale(loc, byLocale[loc], indexTemplate);
  }

  writeSitemap(byLocale);

  console.log(
    `News build completed. Locales: ${LOCALES.join(", ")}. Total article files: ${totalArticles}.`,
  );
}

main();
