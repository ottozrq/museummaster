import { useEffect, useMemo, useState } from "react";
import { I18n } from "i18n-js";

import { translations } from "./translations";

export type AppLanguage = "en" | "zh" | "fr";

const i18n = new I18n(translations);
i18n.enableFallback = true;

function getSystemLanguage(): AppLanguage {
  return "en";
}

function applyLocale(locale: AppLanguage) {
  i18n.locale = locale;
}

// 初始化：应用启动时使用英文作为默认语言
applyLocale(getSystemLanguage());

export function useI18n() {
  const [locale, setLocale] = useState<AppLanguage>(() => getSystemLanguage());

  useEffect(() => {
    applyLocale(locale);
  }, [locale]);

  useEffect(() => {
    setLocale(getSystemLanguage());
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

