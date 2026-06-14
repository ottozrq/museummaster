(function () {
  function cleanText(value) {
    return (value || "").trim().replace(/\s+/g, " ").slice(0, 120);
  }

  function getLanguage() {
    var lang = document.documentElement && document.documentElement.getAttribute("lang");
    if (lang) return lang;
    var match = window.location.pathname.match(/^\/(zh|en|fr)\//);
    return match ? match[1] : "unknown";
  }

  function getPageContext() {
    return {
      page: window.location.pathname,
      path: window.location.pathname,
      page_path: window.location.pathname,
      language: getLanguage(),
    };
  }

  function track(eventName, props) {
    if (!window.umami || typeof window.umami.track !== "function") return;
    window.umami.track(eventName, Object.assign(getPageContext(), props || {}));
  }

  function isGuidePage() {
    return /\/(?:zh|en|fr)\/[^?#]*guide\/?$/.test(window.location.pathname) || !!document.querySelector(".guide-page");
  }

  function isDownloadLink(link, text, href) {
    if (!link) return false;
    if (link.id === "link-app-store" || link.id === "link-play-store") return true;
    if (/apps\.apple\.com|play\.google\.com/.test(href)) return true;
    if (/#download$/.test(href)) return true;
    return /download|get the app|app store|google play|use artiou|télécharger|下载/i.test(text + " " + href);
  }

  function getCtaLocation(link) {
    if (!link || !link.closest) return "unknown";
    if (link.closest("header, .guide-hero, .hero, .hero-section")) return "hero";
    if (link.closest("footer, .site-footer, #download")) return "footer";
    if (link.closest(".guide-card, .guide-panel, .museum-card, .article-card, .card")) return "guide-card";
    if (link.closest("nav, .nav")) return "nav";
    return "body";
  }

  function getInternalGuideUrl(href) {
    try {
      var url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return null;
      return /\/(?:zh|en|fr)\/[^?#]*guide\/?$/.test(url.pathname) ? url : null;
    } catch (e) {
      return null;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var y = document.getElementById("year");
    if (y) y.textContent = new Date().getFullYear();

    var cfg = typeof window !== "undefined" && window.ARTIOU_STORE_URLS ? window.ARTIOU_STORE_URLS : {};
    var app = (cfg.appStore || "").trim();
    var play = (cfg.playStore || "").trim();
    var a = document.getElementById("link-app-store");
    var p = document.getElementById("link-play-store");
    if (a) {
      if (app) {
        a.setAttribute("href", app);
        a.removeAttribute("aria-disabled");
      } else {
        a.setAttribute("href", "#download");
        a.setAttribute("aria-disabled", "true");
      }
    }
    if (p) {
      if (play) {
        p.setAttribute("href", play);
        p.removeAttribute("aria-disabled");
      } else {
        p.setAttribute("href", "#download");
        p.setAttribute("aria-disabled", "true");
      }
    }

    var ctaSecondary = document.getElementById("cta-secondary");
    if (ctaSecondary) {
      ctaSecondary.addEventListener("click", function () {
        var feat = document.getElementById("features");
        if (feat) feat.scrollIntoView({ behavior: "smooth" });
      });
    }
  });

  if (window.ARTIOU_BEHAVIOR_TRACKING_ATTACHED) return;
  window.ARTIOU_BEHAVIOR_TRACKING_ATTACHED = true;

  window.addEventListener("click", function (event) {
    var link = event.target && event.target.closest ? event.target.closest("a") : null;
    if (!link) return;

    var href = link.getAttribute("href") || "";
    var absoluteHref = link.href || href;
    var text = cleanText(link.textContent);
    var guide = isGuidePage();
    var ctaLocation = getCtaLocation(link);
    var targetGuideUrl = getInternalGuideUrl(absoluteHref);

    if (isDownloadLink(link, text, absoluteHref)) {
      track(guide ? "guide_download_click" : "download_click", {
        href: absoluteHref,
        target_path: targetGuideUrl ? targetGuideUrl.pathname : "",
        text: text,
        source_page_type: guide ? "guide" : "sitewide",
        cta_location: ctaLocation,
      });
      return;
    }

    if (guide && (link.classList.contains("btn") || /^#/.test(href))) {
      track("guide_cta_click", {
        href: absoluteHref,
        text: text,
        cta_location: ctaLocation,
        cta_type: link.classList.contains("btn-primary") ? "primary" : link.classList.contains("btn-ghost") ? "secondary" : "anchor",
      });
    }

    if (guide && targetGuideUrl && targetGuideUrl.pathname !== window.location.pathname) {
      track("guide_internal_link_click", {
        href: absoluteHref,
        text: text,
        cta_location: ctaLocation,
        source_path: window.location.pathname,
        target_path: targetGuideUrl.pathname,
      });
    }
  });

  window.addEventListener("toggle", function (event) {
    var details = event.target;
    if (!details || details.tagName !== "DETAILS" || !details.open || !isGuidePage()) return;
    var summary = details.querySelector("summary");
    var parentText = cleanText(details.closest("section") && details.closest("section").textContent);
    track("route_selector_click", {
      text: cleanText(summary && summary.textContent),
      cta_location: "route-selector",
      section_hint: /route|hour|day|itin|路线/i.test(parentText) ? "route" : "faq",
    });
  }, true);

  window.addEventListener("click", function (event) {
    var routeCard = event.target && event.target.closest ? event.target.closest(".route-card") : null;
    if (!routeCard || !isGuidePage()) return;
    track("route_selector_click", {
      text: cleanText(routeCard.querySelector("h3") && routeCard.querySelector("h3").textContent),
      cta_location: "route-card",
      section_hint: "route_card",
    });
  });
})();
