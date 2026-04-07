(function () {
  var STORAGE_KEY = "artiou-site-lang";
  var supported = ["zh", "en", "fr"];

  function detectLocale() {
    var stored = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch (_) {}
    if (stored && supported.indexOf(stored) !== -1) return stored;
    var nav = (navigator.language || "en").toLowerCase();
    if (nav.indexOf("zh") === 0) return "zh";
    if (nav.indexOf("fr") === 0) return "fr";
    return "en";
  }

  function applyLocale(lang) {
    document.documentElement.lang = lang === "zh" ? "zh-Hans" : lang === "fr" ? "fr" : "en";
    var map = STRINGS[lang];
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var key = el.getAttribute("data-i18n");
      if (map && map[key]) el.textContent = map[key];
    }
    var privacy = document.getElementById("privacy-link");
    if (privacy && map && map.privacyHref) privacy.setAttribute("href", map.privacyHref);
    var mediaSets = document.querySelectorAll("[data-lang-media]");
    for (var k = 0; k < mediaSets.length; k++) {
      var set = mediaSets[k];
      set.hidden = set.getAttribute("data-lang-media") !== lang;
    }
    var buttons = document.querySelectorAll(".nav-lang button");
    for (var j = 0; j < buttons.length; j++) {
      var b = buttons[j];
      b.setAttribute("aria-pressed", b.getAttribute("data-lang") === lang ? "true" : "false");
    }
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (_) {}
    wireStoreLinks();
  }

  function wireStoreLinks() {
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
  }

  var STRINGS = {
    zh: {
      "brand.sub": "博物馆 AI 导览",
      "hero.kicker": "拍照识展 · 即时讲解",
      "hero.title": "把展厅装进你的口袋",
      "hero.lead":
        "艺游 Artiou 用视觉识别与中文语音，帮你在博物馆里听懂每一件作品——少排队，多沉浸。",
      "hero.card.title": "为观展而生",
      "hero.card.li1": "对准展品拍照，快速识别并生成讲解",
      "hero.card.li2": "自然中文语音，边走边听",
      "hero.card.li3": "收藏与管理你的艺术旅程",
      "cta.primary": "下载 App",
      "cta.secondary": "了解功能",
      "features.title": "为什么用艺游",
      "features.intro": "更少准备，更多专注。让参观回到作品本身。",
      "visuals.title": "品牌视觉",
      "visuals.intro": "以下展示素材会跟随当前语言切换。",
      "f1.title": "一拍即识",
      "f1.body": "用相机捕捉展品，AI 协助识别并整理关键信息。",
      "f2.title": "中文讲解",
      "f2.body": "生成易听易懂的讲解音频，适配展厅里的节奏。",
      "f3.title": "你的收藏",
      "f3.body": "保存喜欢的作品与讲解，随时回顾。",
      "how.title": "三步开始你的导览",
      "how.intro": "从举起手机到听懂作品，不到一分钟。",
      "how.s1.title": "对准展品",
      "how.s1.body": "打开 Artiou，用相机框住你想了解的作品。",
      "how.s2.title": "获取讲解",
      "how.s2.body": "AI 识别内容后，生成简洁准确的中文导览。",
      "how.s3.title": "边走边听",
      "how.s3.body": "佩戴耳机或外放收听，把节奏留给展厅与自己。",
      "scenes.title": "适合哪些场景",
      "scenes.c1.title": "第一次来美术馆",
      "scenes.c1.body": "快速建立理解，不再只看“看不懂”的标签。",
      "scenes.c2.title": "城市旅行",
      "scenes.c2.body": "在陌生展馆里，也能获得熟悉语言的讲解体验。",
      "scenes.c3.title": "亲子共学",
      "scenes.c3.body": "把作品讲给孩子听，让参观更像一场共同探索。",
      "scenes.c4.title": "深度回顾",
      "scenes.c4.body": "把喜欢的展品加入收藏，离开展馆后继续回看。",
      "trust.title": "隐私与数据说明",
      "trust.intro": "我们把“可解释、可控制”放在第一位。你可以在应用内随时管理收藏与账号数据。",
      "trust.l1": "仅在你主动拍照或上传时处理图像。",
      "trust.l2": "提供隐私政策与使用条款公开链接。",
      "trust.l3": "支持账号注销与历史数据清理。",
      "trust.panel.title": "给机构与策展团队",
      "trust.panel.body": "如果你希望在展览活动中试用 Artiou，欢迎联系合作测试与内容共建。",
      "trust.panel.cta": "联系合作",
      "faq.title": "常见问题",
      "faq.q1": "是否必须登录才能使用识别？",
      "faq.a1": "可以先游客体验，登录后可获得更多额度并同步收藏记录。",
      "faq.q2": "支持哪些语言的讲解？",
      "faq.a2": "目前已支持中文、英文、法文三语讲解。",
      "faq.q3": "识别结果不准确怎么办？",
      "faq.a3": "识别误差多数来自 AI 模型边界（如抽象作品、非常规材质或信息稀缺展品）。你可以重拍更清晰的正面图，或补充作品标题/作者信息以提升结果。",
      "download.title": "在手机上开启艺游",
      "download.intro": "iOS 与 Android 版本陆续上架中。点击下方按钮前往应用商店（链接可在部署前替换）。",
      "download.appstore": "App Store",
      "download.play": "Google Play",
      "download.hint": "若商店链接尚未公开，可先通过 TestFlight / 内测渠道获取。",
      "footer.tagline": "艺游 Artiou — 博物馆里的私人导览。",
      "footer.privacy": "隐私政策",
      "footer.terms": "使用条款（Apple 标准 EULA）",
      privacyHref: "https://www.ottozhang.com/it/policy/artiou/zh",
    },
    en: {
      "brand.sub": "Museum AI guide",
      "hero.kicker": "Scan · Listen · Wander",
      "hero.title": "Your pocket curator",
      "hero.lead":
        "Artiou uses on-device capture, recognition, and natural Chinese narration so you can focus on the art—not the wall text.",
      "hero.card.title": "Built for the gallery",
      "hero.card.li1": "Point, capture, and get context fast",
      "hero.card.li2": "Clear Chinese audio you can walk with",
      "hero.card.li3": "Save favorites and revisit your journey",
      "cta.primary": "Get the app",
      "cta.secondary": "Explore features",
      "features.title": "Why Artiou",
      "features.intro": "Less friction, more presence—stay with the work.",
      "visuals.title": "Brand Visuals",
      "visuals.intro": "These visual assets switch with your selected language.",
      "f1.title": "Snap to recognize",
      "f1.body": "Use your camera to identify an exhibit and surface key details.",
      "f2.title": "Narration in Chinese",
      "f2.body": "Listen to approachable audio that matches a museum pace.",
      "f3.title": "Your collection",
      "f3.body": "Keep pieces and guides you care about for later.",
      "how.title": "Start in three steps",
      "how.intro": "From raising your phone to understanding a work, in under a minute.",
      "how.s1.title": "Frame the artwork",
      "how.s1.body": "Open Artiou and point your camera at the piece you want to learn about.",
      "how.s2.title": "Get instant guidance",
      "how.s2.body": "AI identifies context and turns it into clear, concise Chinese narration.",
      "how.s3.title": "Listen as you move",
      "how.s3.body": "Use earphones or speaker and keep your pace with the gallery.",
      "scenes.title": "Perfect for these moments",
      "scenes.c1.title": "First museum visit",
      "scenes.c1.body": "Build context quickly instead of staring at labels you cannot decode.",
      "scenes.c2.title": "Travel days",
      "scenes.c2.body": "Get familiar-language guidance even in an unfamiliar city museum.",
      "scenes.c3.title": "Family learning",
      "scenes.c3.body": "Turn each piece into a shared conversation with kids.",
      "scenes.c4.title": "Deep revisits",
      "scenes.c4.body": "Save favorites and revisit your journey after leaving the venue.",
      "trust.title": "Privacy and data clarity",
      "trust.intro": "We prioritize explainable flows and user control. Manage your saved items and account data anytime.",
      "trust.l1": "Images are processed only when you explicitly capture or upload.",
      "trust.l2": "Public links are available for Privacy Policy and Terms of Use.",
      "trust.l3": "Account deletion and data cleanup are supported in-app.",
      "trust.panel.title": "For institutions and curators",
      "trust.panel.body": "Interested in piloting Artiou for exhibitions? Reach out for partnership and content collaboration.",
      "trust.panel.cta": "Contact us",
      "faq.title": "FAQ",
      "faq.q1": "Do I need to sign in before scanning?",
      "faq.a1": "You can try Artiou as a guest first. Sign-in unlocks higher limits and syncs collections.",
      "faq.q2": "Which narration languages are supported?",
      "faq.a2": "Narration is currently available in Chinese, English, and French.",
      "faq.q3": "What if recognition is inaccurate?",
      "faq.a3": "Most errors come from model limits (for abstract works, unusual materials, or sparse metadata). Retake a clearer frontal photo, or add the artwork title/artist to improve results.",
      "download.title": "Take Artiou with you",
      "download.intro":
        "iOS and Android builds are rolling out. Replace the store URLs below when your listings go live.",
      "download.appstore": "App Store",
      "download.play": "Google Play",
      "download.hint": "Until public links are ready, distribute via TestFlight or internal testing.",
      "footer.tagline": "Artiou — a quieter way through the museum.",
      "footer.privacy": "Privacy Policy",
      "footer.terms": "Terms of Use (Apple Standard EULA)",
      privacyHref: "https://www.ottozhang.com/it/policy/artiou/en",
    },
    fr: {
      "brand.sub": "Guide IA de musee",
      "hero.kicker": "Scanner · Ecouter · Explorer",
      "hero.title": "Votre guide de poche au musee",
      "hero.lead":
        "Artiou utilise la reconnaissance visuelle et la narration en chinois pour vous aider a comprendre les oeuvres, sans casser votre rythme de visite.",
      "hero.card.title": "Concu pour la visite",
      "hero.card.li1": "Cadrez une oeuvre et obtenez rapidement du contexte",
      "hero.card.li2": "Ecoutez un commentaire clair en chinois",
      "hero.card.li3": "Sauvegardez vos oeuvres preferees",
      "cta.primary": "Telecharger l'app",
      "cta.secondary": "Voir les fonctionnalites",
      "features.title": "Pourquoi Artiou",
      "features.intro": "Moins de friction, plus d'immersion devant les oeuvres.",
      "visuals.title": "Visuels de marque",
      "visuals.intro": "Ces visuels changent automatiquement selon la langue selectionnee.",
      "f1.title": "Identifier en un scan",
      "f1.body": "Utilisez l'appareil photo pour identifier une oeuvre et afficher les points essentiels.",
      "f2.title": "Narration en chinois",
      "f2.body": "Un audio simple et naturel, adapte au rythme du musee.",
      "f3.title": "Votre collection",
      "f3.body": "Conservez les oeuvres et guides que vous aimez pour y revenir plus tard.",
      "how.title": "Commencez en trois etapes",
      "how.intro": "De la prise de vue a la comprehension d'une oeuvre, en moins d'une minute.",
      "how.s1.title": "Cadrez l'oeuvre",
      "how.s1.body": "Ouvrez Artiou et pointez la camera vers l'oeuvre que vous souhaitez explorer.",
      "how.s2.title": "Recevez un guide instantane",
      "how.s2.body": "L'IA reconnait l'oeuvre et genere une explication concise en chinois.",
      "how.s3.title": "Ecoutez en vous deplacant",
      "how.s3.body": "Avec des ecouteurs ou le haut-parleur, gardez votre propre cadence dans l'exposition.",
      "scenes.title": "Cas d'usage ideaux",
      "scenes.c1.title": "Premiere visite de musee",
      "scenes.c1.body": "Comprenez vite les oeuvres, au-dela de simples etiquettes.",
      "scenes.c2.title": "Voyage en ville",
      "scenes.c2.body": "Profitez d'un guidage dans votre langue, meme dans un musee inconnu.",
      "scenes.c3.title": "Visite en famille",
      "scenes.c3.body": "Transformez chaque oeuvre en conversation partagee avec les enfants.",
      "scenes.c4.title": "Relecture approfondie",
      "scenes.c4.body": "Sauvegardez vos coups de coeur et revisitez-les apres votre sortie.",
      "trust.title": "Confidentialite et donnees",
      "trust.intro": "Nous privilegions la transparence et le controle utilisateur. Vous pouvez gerer vos donnees a tout moment.",
      "trust.l1": "Les images sont traitees uniquement quand vous prenez ou envoyez une photo.",
      "trust.l2": "Les liens vers la politique de confidentialite et les conditions d'utilisation sont publics.",
      "trust.l3": "La suppression de compte et le nettoyage des donnees sont disponibles dans l'app.",
      "trust.panel.title": "Pour institutions et curateurs",
      "trust.panel.body": "Vous souhaitez tester Artiou pour une exposition ? Contactez-nous pour une collaboration.",
      "trust.panel.cta": "Nous contacter",
      "faq.title": "FAQ",
      "faq.q1": "Faut-il se connecter pour scanner ?",
      "faq.a1": "Vous pouvez commencer en mode invite. La connexion debloque plus de quota et la synchro des favoris.",
      "faq.q2": "Quelles langues de narration sont prises en charge ?",
      "faq.a2": "La narration est actuellement disponible en chinois, anglais et francais.",
      "faq.q3": "Que faire si la reconnaissance est imprecise ?",
      "faq.a3": "Les erreurs viennent surtout des limites du modele (oeuvres abstraites, materiaux atypiques, ou peu de metadonnees). Reprenez une photo frontale plus nette, ou ajoutez le titre/l'artiste pour ameliorer le resultat.",
      "download.title": "Emportez Artiou avec vous",
      "download.intro":
        "Les versions iOS et Android arrivent progressivement. Remplacez les liens ci-dessous une fois les fiches stores publiees.",
      "download.appstore": "App Store",
      "download.play": "Google Play",
      "download.hint": "En attendant les liens publics, utilisez TestFlight ou les canaux de test interne.",
      "footer.tagline": "Artiou — une visite plus fluide au musee.",
      "footer.privacy": "Politique de confidentialite",
      "footer.terms": "Conditions d'utilisation (EULA Apple standard)",
      privacyHref: "https://www.ottozhang.com/it/policy/artiou/fr",
    },
  };

  document.addEventListener("DOMContentLoaded", function () {
    var lang = detectLocale();
    applyLocale(lang);

    document.querySelectorAll(".nav-lang button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = btn.getAttribute("data-lang");
        if (next && supported.indexOf(next) !== -1) applyLocale(next);
      });
    });

    var ctaSecondary = document.getElementById("cta-secondary");
    if (ctaSecondary) {
      ctaSecondary.addEventListener("click", function () {
        document.getElementById("features").scrollIntoView({ behavior: "smooth" });
      });
    }
  });
})();
