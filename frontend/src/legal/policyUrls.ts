import type { AppLanguage } from "../i18n";

/** 官网托管的 Artiou 隐私政策（与 App Store Connect 隐私政策 URL 应对齐） */
const PRIVACY_BASE = "https://www.ottozhang.com/it/policy/artiou";

/** Apple 标准《使用条款》(EULA)。若在 ASC 使用标准 EULA，App 描述与订阅页应指向同一链接。 */
export const APPLE_STANDARD_EULA_URL =
  "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/";

/**
 * 订阅购买流程中展示的「使用条款 / EULA」链接。
 * 使用自定义 EULA 时请在环境变量中设置与 App Store Connect 一致的 HTTPS 地址。
 */
export function getSubscriptionTermsOfUseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_TERMS_OF_USE_URL?.trim();
  if (fromEnv) return fromEnv;
  return APPLE_STANDARD_EULA_URL;
}

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
