import { useEffect, useMemo, useState } from "react";
import { I18n } from "i18n-js";
import * as RNLocalize from "react-native-localize";

import { translations } from "./translations";

export type AppLanguage = "en" | "zh" | "fr";

const i18n = new I18n(translations);
i18n.enableFallback = true;

function normalizeLanguageTag(tag: string): AppLanguage {
  const lower = tag.toLowerCase();
  if (lower.startsWith("zh")) return "zh";
  if (lower.startsWith("fr")) return "fr";
  return "en";
}

function getSystemLanguage(): AppLanguage {
  const locales = RNLocalize.getLocales?.() ?? [];
  const first = locales[0]?.languageTag ?? locales[0]?.languageCode ?? "en";
  return normalizeLanguageTag(first);
}

function applyLocale(locale: AppLanguage) {
  i18n.locale = locale;
}

// 初始化：应用启动时就对齐系统语言，避免首屏闪一下默认语言
applyLocale(getSystemLanguage());

export function useI18n() {
  const [locale, setLocale] = useState<AppLanguage>(() => getSystemLanguage());

  useEffect(() => {
    applyLocale(locale);
  }, [locale]);

  useEffect(() => {
    const onChange = () => setLocale(getSystemLanguage());
    // react-native-localize v3: addEventListener returns subscription with remove()
    const sub = (RNLocalize as any).addEventListener?.("change", onChange);
    return () => {
      if (sub?.remove) {
        sub.remove();
        return;
      }
      (RNLocalize as any).removeEventListener?.("change", onChange);
    };
  }, []);

  const t = useMemo(() => {
    return (key: string, options?: Record<string, any>) => i18n.t(key, options);
  }, [locale]);

  return { t, locale };
}

export function t(key: string, options?: Record<string, any>) {
  // 兜底：用于非 React 场景；注意此函数不会触发页面刷新
  applyLocale(getSystemLanguage());
  return i18n.t(key, options);
}

