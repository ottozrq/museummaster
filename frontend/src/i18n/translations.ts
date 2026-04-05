export const translations = {
  en: {
    nav: {
      camera: "Artiou",
      result: "Guide",
      history: "History",
      collection: "My Collection",
      settings: "Settings",
      privacy: "Privacy Policy",
      terms: "Terms of Service",
      subscription: "Subscription",
    },
    camera: {
      permissionTitle: "Camera access needed",
      permissionText: "Point at an exhibit so AI can recognize it.",
      enableCamera: "Enable camera",
      topHint: "Point at an exhibit for AI recognition",
      gallery: "Gallery",
      artiou: "Artiou",
      recognizing: "Recognizing...",
      takeOrChoose: "Take a photo or choose from gallery",
      needPhotoLibraryTitle: "Photo access needed",
      needPhotoLibraryText: "Please allow access to pick a photo",
      analyzeFailedTitle: "Recognition failed",
      unknownError: "Unknown error",
      freeScanLimitTitle: "Free scans used up",
      freeScanLimitText:
        "You have used your 5 free scans. Sign in to unlock more scans and save your journey.",
      goSignIn: "Sign in",
      later: "Maybe later",
    },
    collection: {
      saveFavoritesTitle: "Save your favorite pieces",
      saveFavoritesSubtitle: "Sign in to keep your art journey across visits and devices.",
      continueWithGoogle: "Continue with Google",
      legalPrefix: "By entering, you agree to our ",
      privacyPolicy: "privacy policy",
      and: " & ",
      termsOfService: "terms of service",
      loginFailedTitle: "Sign-in failed",
      noAppleCredential: "Could not get Apple credential",
      noGoogleCredential: "Could not get Google credential",
      googleUnavailable: "Google sign-in is unavailable in this build",
      serverNoToken: "Server did not return an access token",
      signOut: "Sign out",
      settings: "Settings",
      signedInWithApple: "Signed in with Apple",
      remainingScans: "Remaining scans: {{count}}",
      empty: "No favorites yet",
      scan: "Scan",
    },
    settings: {
      title: "Settings",
      signOut: "Sign out",
      deleteAccount: "Delete account",
      deleteConfirmTitle: "Delete account?",
      deleteConfirmText: "This action is permanent and cannot be undone.",
      cancel: "Cancel",
      confirmDelete: "Delete",
      deleteSuccessTitle: "Account deleted",
      deleteSuccessText: "Your account has been permanently deleted.",
      deleteFailedTitle: "Delete failed",
      notLoggedInTitle: "Not signed in",
      notLoggedInText: "Please sign in first.",
      unknownError: "Unknown error",
    },
    result: {
      loadFailedTitle: "Load failed",
      loadFailedFallback: "Could not load favorite content",
      recognizeFailedTitle: "Recognition failed",
      playFailedTitle: "Playback failed",
      dailyQuotaExceededTitle: "Daily scan limit reached",
      dailyQuotaExceededText:
        "You have used your scan quota. Please check your subscription plan to keep scanning.",
      viewPlans: "View plans",
      needLoginTitle: "Sign-in required",
      needLoginText: "Sign in to save to your collection",
      cancel: "Cancel",
      goSignIn: "Sign in",
      notReadyTitle: "Not ready yet",
      notReadyText: "This record is still being processed. Please try again later.",
      favoriteFailed: "Save failed",
      unfavoriteFailed: "Remove failed",
      lockscreenTitle: "Audio guide",
      lockscreenArtist: "Artiou",
      title: "Result",
      subtitleStreaming: "AI is explaining the artwork for you…",
      subtitleDone: "AI explains the recognized artwork",
      bodyStreaming: "AI is analyzing this artwork, please wait…",
      bodyEmpty: "No result",
      collectedToast: "Added to collection",
    },
    subscription: {
      title: "Subscription",
      currentPlan: "CURRENT PLAN",
      freePlan: "FREE PLAN",
      scanPackPlan: "Scan Pack",
      proMonthlyPlan: "Scan Pro monthly",
      proYearlyPlan: "Scan Pro yearly",
      changePlan: "CHANGE PLAN",
      buyScanPack: "BUY PACK",
      startPro: "START PRO",
      cancelAnytime: "Cancel anytime",
      freePlanSubtitle: "5 Scans / Day",
      scanPackPrice: "€2.99",
      scanPackSubtitle: "50 Scans",
      proMonthlyPrice: "€5.99 / month",
      proYearlyPrice: "€59.99 / year",
      proSubtitle: "200 scans / month",
      iosOnlyPurchase:
        "In-app purchases are only available on the iOS app. Please use an iPhone or iPad with the App Store version.",
      priceLoading: "Loading price…",
      storeCatalogEmpty:
        "Could not load products from the App Store. Use a physical device, check the bundle ID and product IDs match App Store Connect, and that products are cleared for sale.",
      headlineLine1: "unlock full",
      headlineLine2: "experience",
      scanButton: "SCAN",
      bottomSlogan: "Discover art like never before.",
      legalPrivacyLink: "Privacy Policy",
      legalTermsEulaLink: "Terms of Use (EULA)",
      mostPopular: "MOST POPULAR !",
      activating: "…",
      freePlanDetail1: "* Basic artwork",
      freePlanDetail2: "recognition",
      scanPackFallback1: "* 50 Scans",
      scanPackFallback2: "* Best for",
      scanPackFallback3: "occasional visits",
      proMonthlyFallback1: "* 200 scans / month",
      proMonthlyFallback2: "* Perfect for",
      proMonthlyFallback3: "museum lovers",
      proYearlyFallback1: "* 200 scans / month",
      proYearlyFallback2: "* 2,400 scans / year",
      proYearlyFallback3: "* Best for frequent visitors",
      restorePurchases: "Restore Purchases",
      restoringPurchases: "Restoring…",
      restoreSuccessTitle: "Restored",
      restoreSuccessBody: "Your App Store purchases have been synced to your account.",
      restoreNothingTitle: "Nothing to restore",
      restoreNothingBody:
        "We could not find any active purchases for this Apple ID on this device. Use the same Apple ID you used to buy, or purchase a plan below.",
      restoreNeedSignInTitle: "Sign in required",
      restoreNeedSignInBody: "Sign in with your Artiou account so we can apply your restored purchases to your subscription.",
    },
    legal: {
      back: "← Back",
      privacyTitle: "Privacy Policy",
      termsTitle: "Terms of Service",
      privacyLoadError: "Could not load this page. Check your network connection.",
      privacyWebHint: "View the full privacy policy in your browser.",
      openInBrowser: "Open in browser",
      termsBody: `
Last updated: March 2025

Welcome to Artiou. By downloading, installing, or using the Artiou app ("App", "Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree, do not use the App.

1. Description of the Service

Artiou is a museum guide application that allows you to:
• Take or upload photos of artworks and receive AI-generated descriptions and audio guides.
• Save favorites and, when logged in, sync them across your devices.
• Use text-to-speech to listen to artwork descriptions.

The Service is provided "as is" for personal, non-commercial use in museum and cultural settings.

2. Eligibility

You must be at least 13 years old (or the minimum age in your jurisdiction to consent to use of the Service) and have the legal capacity to enter into these Terms. By using the App, you represent that you meet these requirements.

3. Acceptable Use

You agree not to:
• Use the App for any illegal purpose or in violation of any law.
• Use the App to harass, abuse, or harm others, or to collect or share others’ personal information without consent.
• Attempt to reverse-engineer, decompile, or extract the source code of the App or our systems.
• Use automated means (bots, scrapers) to access the Service without our permission.
• Resell, sublicense, or commercially exploit the App or content generated by the App (e.g., descriptions, audio) except for your own personal use.
• Upload or submit content that infringes intellectual property, privacy, or other rights of any third party.

We may suspend or terminate your access if we reasonably believe you have violated these Terms.

4. Account and Sign-In

• You may use the App without an account for basic recognition and local collection. To sync your collection across devices, you can sign in with Apple.
• You are responsible for keeping your device and Apple account secure. Notify us if you suspect unauthorized access to your account.

5. AI-Generated Content and Accuracy

• Descriptions and audio guides are generated by artificial intelligence and may contain errors, omissions, or subjective interpretations. They are for general guidance only and do not replace expert advice or official museum information.
• We do not guarantee the accuracy, completeness, or suitability of any AI-generated content. You use such content at your own risk.

6. Intellectual Property

• The App, its design, branding, and our original content are owned by us or our licensors. You do not acquire any ownership by using the App.
• You retain ownership of photos you upload. By submitting a photo, you grant us a limited license to process it (e.g., send it to our AI and voice services) solely to provide the Service to you.
• AI-generated descriptions and audio are provided for your personal use; commercial use may require separate permission.

7. Privacy

Your use of the App is also governed by our Privacy Policy. By using the App, you consent to the collection and use of information as described in the Privacy Policy.

8. Disclaimers

TO THE MAXIMUM EXTENT PERMITTED BY LAW:
• THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED.
• WE DISCLAIM ALL WARRANTIES, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
• WE DO NOT WARRANT THAT THE APP WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF HARMFUL COMPONENTS.

9. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW:
• WE (AND OUR AFFILIATES, SUPPLIERS, AND LICENSORS) SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR FOR LOSS OF PROFITS, DATA, OR GOODWILL, ARISING FROM YOUR USE OF THE APP.
• OUR TOTAL LIABILITY FOR ANY CLAIMS ARISING OUT OF OR RELATED TO THESE TERMS OR THE APP SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE TWELVE (12) MONTHS BEFORE THE CLAIM (OR, IF YOU PAID NOTHING, ONE HUNDRED U.S. DOLLARS).

Some jurisdictions do not allow certain limitations; in such cases, the above limitations apply to you only to the extent permitted.

10. Indemnification

You agree to indemnify and hold harmless us and our officers, directors, employees, and agents from any claims, damages, losses, or expenses (including reasonable attorneys’ fees) arising from your use of the App, your violation of these Terms, or your violation of any third-party rights.

11. Changes to the Service and Terms

We may change the App or these Terms at any time. We will notify you of material changes to the Terms by posting the updated Terms in the App or by other reasonable means. Your continued use of the App after the effective date of the changes means you accept the new Terms. If you do not agree, you must stop using the App.

12. General

• Governing law: These Terms are governed by the laws of the jurisdiction in which we operate, without regard to conflict-of-law principles.
• Severability: If any part of these Terms is held invalid or unenforceable, the remaining parts will remain in effect.
• Entire agreement: These Terms (together with the Privacy Policy and any in-app rules) constitute the entire agreement between you and us regarding the App.
• No waiver: Our failure to enforce any right or provision of these Terms does not waive that right or provision.

13. Contact

For questions about these Terms of Service, please contact us at:
Email: legal@example.com
(Replace with your actual contact email or support URL.)
`.trim(),
    },
    history: {
      collectionLink: "My Collection",
      empty: "No history yet",
    },
  },
  zh: {
    nav: {
      camera: "艺游",
      result: "讲解结果",
      history: "历史记录",
      collection: "我的收藏夹",
      settings: "设置",
      privacy: "隐私政策",
      terms: "服务条款",
      subscription: "订阅",
    },
    camera: {
      permissionTitle: "需要相机权限",
      permissionText: "请对准展品，让 AI 识别并讲解。",
      enableCamera: "开启相机",
      topHint: "对准展品，AI 将为你识别讲解",
      gallery: "相册",
      artiou: "ARTIOU",
      recognizing: "识别中…",
      takeOrChoose: "拍照或从相册选择",
      needPhotoLibraryTitle: "需要相册权限",
      needPhotoLibraryText: "请允许访问相册以选择图片",
      analyzeFailedTitle: "识别失败",
      unknownError: "未知错误",
      freeScanLimitTitle: "免费扫码次数已用完",
      freeScanLimitText: "未登录状态下每天可免费识别 5 次，登录后可继续使用并同步收藏。",
      goSignIn: "去登录",
      later: "稍后再说",
    },
    collection: {
      saveFavoritesTitle: "保存你喜欢的作品",
      saveFavoritesSubtitle: "登录后可在不同设备与不同参观中同步你的艺术旅程。",
      continueWithGoogle: "使用 Google 继续",
      legalPrefix: "继续即表示你同意我们的",
      privacyPolicy: "隐私政策",
      and: "与",
      termsOfService: "服务条款",
      loginFailedTitle: "登录失败",
      noAppleCredential: "未能获取 Apple 身份凭证",
      noGoogleCredential: "未能获取 Google 身份凭证",
      googleUnavailable: "当前构建不支持 Google 登录",
      serverNoToken: "服务器未返回访问令牌",
      signOut: "退出",
      settings: "设置",
      signedInWithApple: "已使用 Apple 登录",
      remainingScans: "还剩 {{count}} 次识别",
      empty: "暂无收藏",
      scan: "扫描",
    },
    settings: {
      title: "设置",
      signOut: "退出登录",
      deleteAccount: "删除账号",
      deleteConfirmTitle: "确认删除账号？",
      deleteConfirmText: "删除后不可恢复，账号数据将被永久删除。",
      cancel: "取消",
      confirmDelete: "确认删除",
      deleteSuccessTitle: "账号已删除",
      deleteSuccessText: "你的账号已被永久删除。",
      deleteFailedTitle: "删除失败",
      notLoggedInTitle: "未登录",
      notLoggedInText: "请先登录后再操作。",
      unknownError: "未知错误",
    },
    result: {
      loadFailedTitle: "加载失败",
      loadFailedFallback: "无法加载收藏内容",
      recognizeFailedTitle: "识别失败",
      playFailedTitle: "播放失败",
      dailyQuotaExceededTitle: "今日识别额度已用完",
      dailyQuotaExceededText: "你的识别额度已用完，请查看订阅方案以继续扫描。",
      viewPlans: "查看订阅",
      needLoginTitle: "需要登录",
      needLoginText: "登录后才能收藏作品",
      cancel: "取消",
      goSignIn: "去登录",
      notReadyTitle: "暂不可收藏",
      notReadyText: "当前识别记录尚未完成，请稍后重试。",
      favoriteFailed: "收藏失败",
      unfavoriteFailed: "取消收藏失败",
      lockscreenTitle: "作品讲解",
      lockscreenArtist: "Artiou",
      title: "识别结果",
      subtitleStreaming: "AI 正在为你讲解本次识别到的展品…",
      subtitleDone: "AI 为你讲解本次识别到的展品",
      bodyStreaming: "AI 正在分析这件艺术品，请稍候…",
      bodyEmpty: "暂无结果",
      collectedToast: "作品已加入收藏夹",
    },
    subscription: {
      title: "订阅",
      currentPlan: "当前套餐",
      freePlan: "免费套餐",
      scanPackPlan: "Scan Pack",
      proMonthlyPlan: "Scan Pro 月付",
      proYearlyPlan: "Scan Pro 年付",
      changePlan: "更换套餐",
      buyScanPack: "购买加量包",
      startPro: "开通专业版",
      cancelAnytime: "可随时取消",
      freePlanSubtitle: "每天 5 次识别",
      scanPackPrice: "€2.99",
      scanPackSubtitle: "共 50 次识别",
      proMonthlyPrice: "€5.99 / 月",
      proYearlyPrice: "€59.99 / 年",
      proSubtitle: "每月 200 次识别",
      iosOnlyPurchase: "应用内购买仅支持 iOS 正式版。请在 iPhone 或 iPad 上使用 App Store 版本购买。",
      priceLoading: "正在加载价格…",
      storeCatalogEmpty:
        "无法从 App Store 读取商品。请使用真机，确认 Bundle ID、商品 ID 与 App Store Connect 一致，且商品已可供销售。",
      headlineLine1: "完整解锁",
      headlineLine2: "沉浸体验",
      scanButton: "扫描",
      bottomSlogan: "从未如此走近艺术。",
      legalPrivacyLink: "隐私政策",
      legalTermsEulaLink: "使用条款（EULA）",
      mostPopular: "最受欢迎",
      activating: "…",
      freePlanDetail1: "* 基础作品",
      freePlanDetail2: "识别",
      scanPackFallback1: "* 共 50 次识别",
      scanPackFallback2: "* 适合",
      scanPackFallback3: "偶尔观展",
      proMonthlyFallback1: "* 每月 200 次识别",
      proMonthlyFallback2: "* 适合",
      proMonthlyFallback3: "博物馆爱好者",
      proYearlyFallback1: "* 每月 200 次识别",
      proYearlyFallback2: "* 每年共 2,400 次识别",
      proYearlyFallback3: "* 适合常访客",
      restorePurchases: "恢复购买",
      restoringPurchases: "正在恢复…",
      restoreSuccessTitle: "已恢复",
      restoreSuccessBody: "已将 App Store 购买同步到你的账号。",
      restoreNothingTitle: "没有可恢复项",
      restoreNothingBody:
        "未在本设备上找到该 Apple ID 的有效购买记录。请使用购买时所用的 Apple ID，或在下方选购套餐。",
      restoreNeedSignInTitle: "需要先登录",
      restoreNeedSignInBody: "请登录 Artiou 账号，以便将恢复的购买同步到订阅权益。",
    },
    legal: {
      back: "← 返回",
      privacyTitle: "隐私政策",
      termsTitle: "服务条款",
      privacyLoadError: "无法加载此页面，请检查网络连接。",
      privacyWebHint: "在浏览器中查看完整隐私政策。",
      openInBrowser: "在浏览器中打开",
      termsBody: `
更新日期：2025 年 3 月

欢迎使用 Artiou。下载、安装或使用 Artiou（“应用”“服务”）即表示你同意接受本服务条款（“条款”）的约束；若不同意，请不要使用本应用。

1. 服务说明

Artiou 提供：
• 拍摄或上传作品图片，获取 AI 生成的讲解与音频；
• 保存收藏，并在登录后跨设备同步；
• 使用文本转语音收听讲解。

本服务按“现状”提供，用于个人、非商业的博物馆与文化场景。

2. 使用资格

你需年满 13 周岁（或你所在司法辖区规定的最低同意年龄），并具备签署本条款的民事行为能力。使用本应用即表示你满足这些条件。

3. 合理使用

你同意不会：
• 用于任何非法目的或违反任何法律法规；
• 骚扰、辱骂或伤害他人，或未经同意收集/分享他人个人信息；
• 逆向工程、反编译或试图提取应用或系统源代码；
• 未经许可使用机器人/爬虫等自动化方式访问服务；
• 转售、再许可或商业化利用应用或其生成内容（除个人使用外）；
• 上传侵犯知识产权、隐私或其他第三方权利的内容。

如我们合理认为你违反条款，可能暂停或终止你的访问。

4. 账号与登录

• 你可在不登录的情况下使用基础识别与本地收藏；若要跨设备同步，可使用 Apple 登录。
• 你需自行确保设备与 Apple 账号安全；如怀疑被未授权访问，请及时通知我们。

5. AI 内容与准确性

• 讲解与音频由 AI 生成，可能存在错误、遗漏或主观表述，仅供参考，不替代专家意见或博物馆官方信息。
• 我们不保证 AI 内容的准确性、完整性或适用性；你需自行承担使用风险。

6. 知识产权

• 应用的设计、品牌与原创内容归我们或许可方所有；你不会因使用而获得任何所有权。
• 你保留上传图片的所有权；提交图片即授予我们为向你提供服务所需的有限处理许可。
• AI 生成讲解与音频供个人使用；商业用途可能需要另行授权。

7. 隐私

你对应用的使用同样受《隐私政策》约束。使用应用即表示你同意按隐私政策所述收集与使用信息。

8. 免责声明

在法律允许的最大范围内：
• 服务按“现状”“可用”提供，不作任何明示或暗示保证；
• 我们不保证应用不中断、无错误或不含有害组件。

9. 责任限制

在法律允许的最大范围内：
• 我们（及关联方/供应商/许可方）不对间接、附带、特殊、后果性或惩罚性损害承担责任；
• 因本条款或应用产生的总责任不超过你在提出索赔前 12 个月支付给我们的金额（如未支付，则不超过 100 美元）。

部分司法辖区不允许某些限制，上述限制仅在法律允许范围内适用。

10. 赔偿

因你使用应用、违反条款或侵犯第三方权利而导致的索赔、损失与费用（含合理律师费），你同意对我们进行赔偿并使我们免责。

11. 服务与条款变更

我们可能随时变更应用或条款。若条款有重大变更，我们会在应用内发布或以合理方式通知。变更生效后继续使用即表示你接受新条款；不同意则应停止使用。

12. 其他

• 适用法律：以我们运营所在地法律为准（不含冲突法规则）。
• 可分割性：如条款部分无效，不影响其余部分效力。
• 完整协议：本条款与隐私政策构成你与我们之间关于应用的完整协议。
• 不弃权：我们未行使某项权利不代表放弃该权利。

13. 联系方式

如对本条款有疑问，请联系：
邮箱：legal@example.com
（请替换为实际联系方式）
`.trim(),
    },
    history: {
      collectionLink: "我的收藏夹",
      empty: "暂无历史记录",
    },
  },
  fr: {
    nav: {
      camera: "Artiou",
      result: "Guide",
      history: "Historique",
      collection: "Ma collection",
      settings: "Parametres",
      privacy: "Politique de confidentialité",
      terms: "Conditions d’utilisation",
      subscription: "Abonnement",
    },
    camera: {
      permissionTitle: "Accès à la caméra requis",
      permissionText: "Visez une œuvre pour que l’IA puisse la reconnaître.",
      enableCamera: "Activer la caméra",
      topHint: "Visez une œuvre pour la reconnaissance IA",
      gallery: "Galerie",
      artiou: "Artiou",
      recognizing: "Reconnaissance…",
      takeOrChoose: "Prendre une photo ou choisir dans la galerie",
      needPhotoLibraryTitle: "Accès aux photos requis",
      needPhotoLibraryText: "Autorisez l’accès pour choisir une photo",
      analyzeFailedTitle: "Échec de la reconnaissance",
      unknownError: "Erreur inconnue",
      freeScanLimitTitle: "Limite de scans atteinte",
      freeScanLimitText:
        "Vous avez utilisé vos 5 scans gratuits du jour. Connectez-vous pour continuer à scanner et enregistrer votre parcours.",
      goSignIn: "Se connecter",
      later: "Plus tard",
    },
    collection: {
      saveFavoritesTitle: "Enregistrez vos œuvres favorites",
      saveFavoritesSubtitle:
        "Connectez-vous pour retrouver votre parcours artistique sur plusieurs visites et appareils.",
      continueWithGoogle: "Continuer avec Google",
      legalPrefix: "En continuant, vous acceptez notre ",
      privacyPolicy: "politique de confidentialité",
      and: " et ",
      termsOfService: "conditions d’utilisation",
      loginFailedTitle: "Échec de la connexion",
      noAppleCredential: "Impossible d’obtenir l’identifiant Apple",
      noGoogleCredential: "Impossible d’obtenir l’identifiant Google",
      googleUnavailable: "La connexion Google n'est pas disponible dans cette version",
      serverNoToken: "Le serveur n’a pas renvoyé de jeton d’accès",
      signOut: "Se déconnecter",
      settings: "Parametres",
      signedInWithApple: "Connecté avec Apple",
      remainingScans: "Scans restants : {{count}}",
      empty: "Aucun favori",
      scan: "Scanner",
    },
    settings: {
      title: "Parametres",
      signOut: "Se deconnecter",
      deleteAccount: "Supprimer le compte",
      deleteConfirmTitle: "Supprimer le compte ?",
      deleteConfirmText: "Cette action est definitive et irreversible.",
      cancel: "Annuler",
      confirmDelete: "Supprimer",
      deleteSuccessTitle: "Compte supprime",
      deleteSuccessText: "Votre compte a ete supprime definitivement.",
      deleteFailedTitle: "Echec de la suppression",
      notLoggedInTitle: "Non connecte",
      notLoggedInText: "Veuillez vous connecter d'abord.",
      unknownError: "Erreur inconnue",
    },
    result: {
      loadFailedTitle: "Échec du chargement",
      loadFailedFallback: "Impossible de charger le contenu favori",
      recognizeFailedTitle: "Échec de la reconnaissance",
      playFailedTitle: "Échec de la lecture",
      dailyQuotaExceededTitle: "Limite de scans atteinte",
      dailyQuotaExceededText:
        "Vous avez atteint votre limite de scans. Consultez votre offre d’abonnement pour continuer.",
      viewPlans: "Voir les offres",
      needLoginTitle: "Connexion requise",
      needLoginText: "Connectez-vous pour enregistrer dans votre collection",
      cancel: "Annuler",
      goSignIn: "Se connecter",
      notReadyTitle: "Pas encore prêt",
      notReadyText: "Cet élément est en cours de traitement. Réessayez plus tard.",
      favoriteFailed: "Échec de l’enregistrement",
      unfavoriteFailed: "Échec de la suppression",
      lockscreenTitle: "Guide audio",
      lockscreenArtist: "Artiou",
      title: "Résultat",
      subtitleStreaming: "L’IA vous explique l’œuvre…",
      subtitleDone: "L’IA explique l’œuvre reconnue",
      bodyStreaming: "Analyse de l’œuvre en cours, veuillez patienter…",
      bodyEmpty: "Aucun résultat",
      collectedToast: "Ajouté à la collection",
    },
    subscription: {
      title: "Abonnement",
      currentPlan: "PLAN ACTUEL",
      freePlan: "FORFAIT GRATUIT",
      scanPackPlan: "Scan Pack",
      proMonthlyPlan: "Scan Pro mensuel",
      proYearlyPlan: "Scan Pro annuel",
      changePlan: "CHANGER DE PLAN",
      buyScanPack: "ACHETER LE PACK",
      startPro: "DÉMARRER PRO",
      cancelAnytime: "Annulez à tout moment",
      freePlanSubtitle: "5 scans / jour",
      scanPackPrice: "€2,99",
      scanPackSubtitle: "50 scans",
      proMonthlyPrice: "€5,99 / mois",
      proYearlyPrice: "€59,99 / an",
      proSubtitle: "200 scans / mois",
      iosOnlyPurchase:
        "Les achats intégrés sont disponibles uniquement sur l’app iOS (App Store). Utilisez un iPhone ou un iPad.",
      priceLoading: "Chargement du prix…",
      storeCatalogEmpty:
        "Impossible de charger les produits App Store. Utilisez un appareil réel, vérifiez l’identifiant bundle et les IDs produits, et que les produits sont disponibles à la vente.",
      headlineLine1: "libérez toute",
      headlineLine2: "l’expérience",
      scanButton: "SCAN",
      bottomSlogan: "Découvrez l’art comme jamais auparavant.",
      legalPrivacyLink: "Politique de confidentialité",
      legalTermsEulaLink: "Conditions d’utilisation (EULA)",
      mostPopular: "LE PLUS POPULAIRE !",
      activating: "…",
      freePlanDetail1: "* Reconnaissance d’œuvres",
      freePlanDetail2: "de base",
      scanPackFallback1: "* 50 scans",
      scanPackFallback2: "* Idéal pour",
      scanPackFallback3: "les visites occasionnelles",
      proMonthlyFallback1: "* 200 scans / mois",
      proMonthlyFallback2: "* Parfait pour",
      proMonthlyFallback3: "les passionnés de musées",
      proYearlyFallback1: "* 200 scans / mois",
      proYearlyFallback2: "* 2 400 scans / an",
      proYearlyFallback3: "* Idéal pour les visiteurs assidus",
      restorePurchases: "Restaurer les achats",
      restoringPurchases: "Restauration…",
      restoreSuccessTitle: "Restauré",
      restoreSuccessBody: "Vos achats App Store ont été synchronisés avec votre compte.",
      restoreNothingTitle: "Aucun achat à restaurer",
      restoreNothingBody:
        "Aucun achat actif trouvé pour cet identifiant Apple sur cet appareil. Utilisez le même compte Apple que lors de l’achat, ou choisissez une offre ci-dessous.",
      restoreNeedSignInTitle: "Connexion requise",
      restoreNeedSignInBody: "Connectez-vous à Artiou pour appliquer vos achats restaurés à votre abonnement.",
    },
    legal: {
      back: "← Retour",
      privacyTitle: "Politique de confidentialité",
      termsTitle: "Conditions d’utilisation",
      privacyLoadError: "Impossible de charger cette page. Vérifiez votre connexion.",
      privacyWebHint: "Consultez la politique de confidentialité complète dans votre navigateur.",
      openInBrowser: "Ouvrir dans le navigateur",
      termsBody: `
Dernière mise à jour : mars 2025

En utilisant Artiou, vous acceptez ces conditions d’utilisation. Si vous n’êtes pas d’accord, n’utilisez pas l’application.

Artiou permet de photographier une œuvre, recevoir une description/guidage audio générés par IA, enregistrer des favoris et écouter en synthèse vocale.

Le service est fourni « en l’état » pour un usage personnel et non commercial.

Contact : legal@example.com
`.trim(),
    },
    history: {
      collectionLink: "Ma collection",
      empty: "Aucun historique",
    },
  },
} as const;

