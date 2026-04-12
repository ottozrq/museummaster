(function () {
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
})();
