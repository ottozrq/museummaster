import type { AppLanguage } from "../i18n";

/** 官网托管的 Artiou 隐私政策（与 App Store Connect 隐私政策 URL 应对齐） */
const PRIVACY_BASE = "https://www.ottozhang.com/it/policy/artiou";

export function getArtiouPrivacyPolicyUrl(locale: AppLanguage): string {
  switch (locale) {
    case "zh":
      return `${PRIVACY_BASE}/zh`;
    case "fr":
      return `${PRIVACY_BASE}/fr`;
    default:
      return `${PRIVACY_BASE}/en`;
  }
}
