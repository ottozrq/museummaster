#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SITE_ROOT = path.resolve(SCRIPT_DIR, "..");
const CONTENT_ROOT = path.join(SITE_ROOT, "content", "news");
const TEMPLATES_DIR = path.join(SITE_ROOT, "templates");
const SITEMAP_PATH = path.join(SITE_ROOT, "sitemap.xml");
const SITEMAP_CORE_PATH = path.join(SCRIPT_DIR, "sitemap-core.xml");
const SITE_URL = "https://www.artiou.com";
const LOCALES = ["zh", "en", "fr"];
const HREFLANG = { zh: "zh-Hans", en: "en", fr: "fr" };

const LOCALE_UI = {
  zh: {
    htmlLang: "zh-Hans",
    ogLocale: "zh_CN",
    dateLocale: "zh-CN",
    brandSub: "博物馆 AI 导览",
    primaryNavAria: "新闻导航",
    langNavAria: "语言版本",
    homePath: "/zh/",
    privacyPath: "/zh/privacy/",
    llmsPath: "/llms.txt",
    footerDescription: "艺游 Artiou 的产品新闻、观展灵感与使用更新。",
    footerHome: "官网首页",
    footerPrivacy: "隐私政策",
    footerRights: "All rights reserved.",
    backToNews: "返回新闻站",
    readMore: "阅读全文",
    nav: { home: "首页", features: "功能", news: "新闻" },
    index: {
      pageTitle: "艺游新闻站 | Artiou 产品更新与观展灵感",
      pageDescription: "艺游 Artiou 新闻站持续发布博物馆导览、产品更新、观展技巧与品牌动态。",
      heroTitle: "艺游新闻站",
      heroDescription: "从产品更新到观展灵感，帮助你更轻松地进入每一场展览。",
      kicker: "Artiou 编辑部",
    },
    cta: {
      title: "把新闻里的灵感带进展厅",
      desc: "用 Artiou 拍照识展、收听讲解、收藏你的艺术旅程。",
      button: "下载 Artiou",
    },
  },
  en: {
    htmlLang: "en",
    ogLocale: "en_US",
    dateLocale: "en-US",
    brandSub: "Museum AI guide",
    primaryNavAria: "News navigation",
    langNavAria: "Language",
    homePath: "/en/",
    privacyPath: "/en/privacy/",
    llmsPath: "/llms-en.txt",
    footerDescription: "Product updates, museum ideas, and editorial notes from Artiou.",
    footerHome: "Home",
    footerPrivacy: "Privacy Policy",
    footerRights: "All rights reserved.",
    backToNews: "Back to news",
    readMore: "Read article",
    nav: { home: "Home", features: "Features", news: "News" },
    index: {
      pageTitle: "Artiou News | Product updates and museum ideas",
      pageDescription: "News from Artiou about museum AI guidance, product releases, gallery habits, and brand updates.",
      heroTitle: "Artiou News",
      heroDescription: "Product notes, museum-going ideas, and practical updates from the team behind your pocket curator.",
      kicker: "Artiou editorial",
    },
    cta: {
      title: "Bring these ideas into your next visit",
      desc: "Use Artiou to scan artworks, hear narration, and keep the pieces that stay with you.",
      button: "Get Artiou",
    },
  },
  fr: {
    htmlLang: "fr",
    ogLocale: "fr_FR",
    dateLocale: "fr-FR",
    brandSub: "Guide IA de musée",
    primaryNavAria: "Navigation actualités",
    langNavAria: "Langue",
    homePath: "/fr/",
    privacyPath: "/fr/privacy/",
    llmsPath: "/llms.txt",
    footerDescription: "Actualités produit, idées de visite et notes éditoriales d'Artiou.",
    footerHome: "Accueil",
    footerPrivacy: "Politique de confidentialité",
    footerRights: "All rights reserved.",
    backToNews: "Retour aux actualités",
    readMore: "Lire l'article",
    nav: { home: "Accueil", features: "Fonctionnalités", news: "Actualités" },
    index: {
      pageTitle: "Actualités Artiou | Produit et inspirations musée",
      pageDescription: "Le journal d'Artiou : mises à jour produit, conseils de visite, idées pour mieux vivre les musées.",
      heroTitle: "Actualités Artiou",
      heroDescription: "Nouveautés produit, habitudes de visite et repères pour mieux entrer dans une exposition.",
      kicker: "Artiou éditorial",
    },
    cta: {
      title: "Emportez ces idées dans votre prochaine visite",
      desc: "Avec Artiou, scannez une œuvre, écoutez une narration claire et gardez vos découvertes.",
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

function renderInlineMarkdown(text = "") {
  let output = escapeHtml(text);
  output = output.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  output = output.replace(/\*(.+?)\*/g, "<em>$1</em>");
  output = output.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
    return `<a href="${escapeHtml(href)}">${escapeHtml(label)}</a>`;
  });
  return output;
}

function formatDate(dateValue, locale) {
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return dateValue;
  return new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function parseTags(rawTags = "") {
  const trimmed = rawTags.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    return trimmed
      .slice(1, -1)
      .split(",")
      .map((item) => item.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
  }
  return trimmed.split(",").map((item) => item.trim()).filter(Boolean);
}

function parseFrontmatter(fileContent) {
  if (!fileContent.startsWith("---\n")) {
    throw new Error("Markdown file is missing frontmatter");
  }
  const endMarker = fileContent.indexOf("\n---\n", 4);
  if (endMarker === -1) {
    throw new Error("Frontmatter closing marker missing");
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
      html.push(`<h3>${renderInlineMarkdown(line.slice(4))}</h3>`);
      continue;
    }
    if (line.startsWith("## ")) {
      closeList();
      html.push(`<h2>${renderInlineMarkdown(line.slice(3))}</h2>`);
      continue;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(line.slice(2))}</li>`);
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${renderInlineMarkdown(line.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }
    closeList();
    html.push(`<p>${renderInlineMarkdown(line)}</p>`);
  }

  closeList();
  return html.join("\n");
}

function ensureRequiredFields(meta, sourceFile) {
  for (const field of ["title", "description", "slug", "date", "updated", "author", "category"]) {
    if (!meta[field]) {
      throw new Error(`${sourceFile} missing required field: ${field}`);
    }
  }
}

function renderTemplate(template, replacements) {
  return Object.entries(replacements).reduce((output, [key, value]) => {
    return output.replaceAll(`{{${key}}}`, value == null ? "" : String(value));
  }, template);
}

function writeFile(targetPath, content) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, content, "utf8");
}

function buildHreflangLinks(slug = null) {
  return LOCALES.map((locale) => {
    const href = slug ? `${SITE_URL}/${locale}/news/${slug}/` : `${SITE_URL}/${locale}/news/`;
    return `    <link rel="alternate" hreflang="${HREFLANG[locale]}" href="${href}" />`;
  })
    .concat([
      `    <link rel="alternate" hreflang="x-default" href="${
        slug ? `${SITE_URL}/zh/news/${slug}/` : `${SITE_URL}/zh/news/`
      }" />`,
    ])
    .join("\n");
}

function buildPrimaryNav(locale) {
  const ui = LOCALE_UI[locale];
  return [
    `<a href="${ui.homePath}">${ui.nav.home}</a>`,
    `<a href="${ui.homePath}#features">${ui.nav.features}</a>`,
    `<a href="${ui.homePath}news/" aria-current="page">${ui.nav.news}</a>`,
  ].join("\n");
}

function buildLangLinks(currentLocale, slug = null) {
  return LOCALES.map((locale) => {
    const href = slug ? `/${locale}/news/${slug}/` : `/${locale}/news/`;
    const label = locale === "zh" ? "中文" : locale.toUpperCase();
    const current = locale === currentLocale ? ' aria-current="page"' : "";
    return `<a href="${href}" hreflang="${HREFLANG[locale]}"${current}>${label}</a>`;
  }).join("\n");
}

function collectArticles() {
  const perLocale = {};
  const articlesBySlug = new Map();

  for (const locale of LOCALES) {
    const localeDir = path.join(CONTENT_ROOT, locale);
    const files = fs.readdirSync(localeDir).filter((name) => name.endsWith(".md")).sort();
    perLocale[locale] = files.map((fileName) => {
      const fullPath = path.join(localeDir, fileName);
      const { meta, body } = parseFrontmatter(fs.readFileSync(fullPath, "utf8"));
      ensureRequiredFields(meta, fullPath);
      const article = { meta, body };
      if (!articlesBySlug.has(meta.slug)) {
        articlesBySlug.set(meta.slug, {});
      }
      articlesBySlug.get(meta.slug)[locale] = article;
      return article;
    });
  }

  return { perLocale, articlesBySlug };
}

function buildArticleJsonLd(article, locale) {
  return JSON.stringify(
    {
      "@context": "https://schema.org",
      "@type": "Article",
      headline: article.meta.title,
      description: article.meta.description,
      inLanguage: LOCALE_UI[locale].htmlLang,
      datePublished: article.meta.date,
      dateModified: article.meta.updated,
      author: { "@type": "Organization", name: article.meta.author },
      publisher: {
        "@type": "Organization",
        name: "Artiou",
        logo: { "@type": "ImageObject", url: `${SITE_URL}/artiou-og.png` },
      },
      image: `${SITE_URL}/artiou-og.png`,
      mainEntityOfPage: `${SITE_URL}/${locale}/news/${article.meta.slug}/`,
    },
    null,
    2,
  );
}

function renderNewsCard(article, locale) {
  const ui = LOCALE_UI[locale];
  const tags = article.meta.tags
    .slice(0, 3)
    .map((tag) => `<span class="news-tag">${escapeHtml(tag)}</span>`)
    .join("");

  return `            <article class="news-card">
              <div class="news-card-meta">
                <span>${escapeHtml(article.meta.category)}</span>
                <span>·</span>
                <time datetime="${escapeHtml(article.meta.date)}">${escapeHtml(
                  formatDate(article.meta.date, ui.dateLocale),
                )}</time>
              </div>
              <h2><a href="/${locale}/news/${article.meta.slug}/">${escapeHtml(article.meta.title)}</a></h2>
              <p>${escapeHtml(article.meta.description)}</p>
              <div class="news-card-footer">
                <div class="news-tag-list">${tags}</div>
                <a class="news-read-more" href="/${locale}/news/${article.meta.slug}/">${ui.readMore}</a>
              </div>
            </article>`;
}

function buildSitemapEntries(articlesBySlug) {
  const today = new Date().toISOString().slice(0, 10);
  const entries = [];

  for (const locale of LOCALES) {
    entries.push(`  <url>
    <loc>${SITE_URL}/${locale}/news/</loc>
    <lastmod>${today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
    <xhtml:link rel="alternate" hreflang="zh-Hans" href="${SITE_URL}/zh/news/"/>
    <xhtml:link rel="alternate" hreflang="en" href="${SITE_URL}/en/news/"/>
    <xhtml:link rel="alternate" hreflang="fr" href="${SITE_URL}/fr/news/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="${SITE_URL}/zh/news/"/>
  </url>`);
  }

  for (const [slug, localized] of articlesBySlug.entries()) {
    for (const locale of LOCALES) {
      if (!localized[locale]) continue;
      entries.push(`  <url>
    <loc>${SITE_URL}/${locale}/news/${slug}/</loc>
    <lastmod>${localized[locale].meta.updated}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
    <xhtml:link rel="alternate" hreflang="zh-Hans" href="${SITE_URL}/zh/news/${slug}/"/>
    <xhtml:link rel="alternate" hreflang="en" href="${SITE_URL}/en/news/${slug}/"/>
    <xhtml:link rel="alternate" hreflang="fr" href="${SITE_URL}/fr/news/${slug}/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="${SITE_URL}/zh/news/${slug}/"/>
  </url>`);
    }
  }

  return entries.join("\n");
}

function main() {
  const indexTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, "news-index.html"), "utf8");
  const articleTemplate = fs.readFileSync(path.join(TEMPLATES_DIR, "news-article.html"), "utf8");
  const { perLocale, articlesBySlug } = collectArticles();

  for (const locale of LOCALES) {
    const ui = LOCALE_UI[locale];
    const articles = perLocale[locale].sort((a, b) => (a.meta.date < b.meta.date ? 1 : -1));
    const indexHtml = renderTemplate(indexTemplate, {
      HTML_LANG: ui.htmlLang,
      PAGE_TITLE: escapeHtml(ui.index.pageTitle),
      PAGE_DESCRIPTION: escapeHtml(ui.index.pageDescription),
      CANONICAL_URL: `${SITE_URL}/${locale}/news/`,
      HREFLANG_LINKS: buildHreflangLinks(),
      OG_LOCALE: ui.ogLocale,
      ASSET_PREFIX: "../../",
      HOME_URL: ui.homePath,
      BRAND_SUB: escapeHtml(ui.brandSub),
      PRIMARY_NAV_ARIA: escapeHtml(ui.primaryNavAria),
      PRIMARY_NAV: buildPrimaryNav(locale),
      LANG_NAV_ARIA: escapeHtml(ui.langNavAria),
      LANG_SWITCHER: buildLangLinks(locale),
      KICKER: escapeHtml(ui.index.kicker),
      HERO_TITLE: escapeHtml(ui.index.heroTitle),
      HERO_DESCRIPTION: escapeHtml(ui.index.heroDescription),
      ARTICLES: articles.map((article) => renderNewsCard(article, locale)).join("\n"),
      FOOTER_DESCRIPTION: escapeHtml(ui.footerDescription),
      FOOTER_HOME: escapeHtml(ui.footerHome),
      PRIVACY_URL: ui.privacyPath,
      FOOTER_PRIVACY: escapeHtml(ui.footerPrivacy),
      LLMS_URL: ui.llmsPath,
      CURRENT_YEAR: new Date().getFullYear(),
      FOOTER_RIGHTS: escapeHtml(ui.footerRights),
    });

    writeFile(path.join(SITE_ROOT, locale, "news", "index.html"), indexHtml);

    for (const article of articles) {
      const articleHtml = renderTemplate(articleTemplate, {
        HTML_LANG: ui.htmlLang,
        ARTICLE_TITLE: escapeHtml(article.meta.title),
        ARTICLE_HEADING: escapeHtml(article.meta.title),
        ARTICLE_DESCRIPTION: escapeHtml(article.meta.description),
        CANONICAL_URL: `${SITE_URL}/${locale}/news/${article.meta.slug}/`,
        HREFLANG_LINKS: buildHreflangLinks(article.meta.slug),
        OG_LOCALE: ui.ogLocale,
        ARTICLE_OG_IMAGE: `${SITE_URL}/artiou-og.png`,
        ARTICLE_PUBLISHED_TIME: escapeHtml(article.meta.date),
        ARTICLE_MODIFIED_TIME: escapeHtml(article.meta.updated),
        ARTICLE_CATEGORY: escapeHtml(article.meta.category),
        ARTICLE_PUBLISHED_TEXT: escapeHtml(formatDate(article.meta.date, ui.dateLocale)),
        ARTICLE_JSON_LD: buildArticleJsonLd(article, locale),
        ASSET_PREFIX: "../../../",
        HOME_URL: ui.homePath,
        BRAND_SUB: escapeHtml(ui.brandSub),
        PRIMARY_NAV_ARIA: escapeHtml(ui.primaryNavAria),
        PRIMARY_NAV: buildPrimaryNav(locale),
        LANG_NAV_ARIA: escapeHtml(ui.langNavAria),
        LANG_SWITCHER: buildLangLinks(locale, article.meta.slug),
        ARTICLE_CONTENT: markdownToHtml(article.body),
        ARTICLE_TAGS: article.meta.tags
          .map((tag) => `<span class="article-tag">${escapeHtml(tag)}</span>`)
          .join("\n"),
        CTA_TITLE: escapeHtml(ui.cta.title),
        CTA_DESC: escapeHtml(ui.cta.desc),
        CTA_BUTTON: escapeHtml(ui.cta.button),
        NEWS_INDEX_URL: `/${locale}/news/`,
        BACK_TO_NEWS: escapeHtml(ui.backToNews),
        FOOTER_DESCRIPTION: escapeHtml(ui.footerDescription),
        FOOTER_HOME: escapeHtml(ui.footerHome),
        PRIVACY_URL: ui.privacyPath,
        FOOTER_PRIVACY: escapeHtml(ui.footerPrivacy),
        LLMS_URL: ui.llmsPath,
        CURRENT_YEAR: new Date().getFullYear(),
        FOOTER_RIGHTS: escapeHtml(ui.footerRights),
      });

      writeFile(path.join(SITE_ROOT, locale, "news", article.meta.slug, "index.html"), articleHtml);
    }
  }

  const sitemapCore = fs.readFileSync(SITEMAP_CORE_PATH, "utf8").trimEnd();
  writeFile(SITEMAP_PATH, `${sitemapCore}\n${buildSitemapEntries(articlesBySlug)}\n</urlset>\n`);
}

main();
