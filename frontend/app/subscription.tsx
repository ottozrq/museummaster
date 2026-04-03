import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  loadIosStoreCatalog,
  purchaseIosPlanThenActivate,
  STORE_PRODUCT_UNAVAILABLE,
  storeDescriptionToDetailLines,
  type StoreCatalog,
} from "../src/iap/appleIap";
import {
  activateSubscriptionPlan,
  fetchSubscriptionCurrent,
  type SubscriptionCurrent,
  type SubscriptionPlanType,
} from "../src/services/api";
import { useI18n } from "../src/i18n";

const TOKEN_KEY = "museum_auth_token";
const BRAND_RED = "#EB3A00";
const BG = "#E9E1D3";
const CARD_BG = "#ECE4D6";
const WHITE = "#FFFFFF";

type CardTheme = "outline" | "filled";

function PlanCard(props: {
  titleMain: string;
  titleSub?: string;
  price: string;
  details: string[];
  badge?: string;
  buttonText: string;
  note?: string;
  theme?: CardTheme;
  onPress: () => void;
  disabled?: boolean;
}) {
  const {
    titleMain,
    titleSub,
    price,
    details,
    badge,
    buttonText,
    note,
    theme = "outline",
    onPress,
    disabled,
  } = props;
  const filled = theme === "filled";

  return (
    <View style={[styles.card, filled ? styles.cardFilled : styles.cardOutline]}>
      <View style={styles.cardTitleRow}>
        <Text
          style={[styles.cardTitleMain, filled && styles.cardTitleMainFilled]}
          numberOfLines={3}
          adjustsFontSizeToFit
          minimumFontScale={0.55}
        >
          {titleMain}
        </Text>
        {titleSub ? <Text style={[styles.cardTitleSub, filled && styles.cardTitleSubFilled]}>{titleSub}</Text> : null}
      </View>

      <Text style={[styles.cardPrice, filled && styles.cardPriceFilled]}>{price}</Text>

      <View style={styles.cardDetailBlock}>
        {details.map((line, idx) => (
          <Text key={`${idx}-${line.slice(0, 24)}`} style={[styles.cardDetailText, filled && styles.cardDetailTextFilled]}>
            {line}
          </Text>
        ))}
      </View>

      {badge ? <Text style={[styles.cardBadge, filled && styles.cardBadgeFilled]}>{badge}</Text> : null}

      <Pressable
        style={[styles.cardButton, filled ? styles.cardButtonFilled : styles.cardButtonOutline]}
        onPress={onPress}
        disabled={!!disabled}
      >
        <Text
          numberOfLines={1}
          adjustsFontSizeToFit
          minimumFontScale={0.8}
          style={[styles.cardButtonText, filled && styles.cardButtonTextFilled, disabled && styles.disabledText]}
        >
          {buttonText}
        </Text>
      </Pressable>

      {note ? <Text style={[styles.cardNote, filled && styles.cardNoteFilled]}>{note}</Text> : null}
    </View>
  );
}

export default function SubscriptionScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const insets = useSafeAreaInsets();

  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [current, setCurrent] = useState<SubscriptionCurrent | null>(null);
  const [activating, setActivating] = useState<SubscriptionPlanType | null>(null);
  const [storeCatalog, setStoreCatalog] = useState<StoreCatalog>({});
  const [storeCatalogReady, setStoreCatalogReady] = useState(Platform.OS !== "ios");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const v = await AsyncStorage.getItem(TOKEN_KEY);
        if (!cancelled) setToken(v);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!token) {
      setCurrent(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchSubscriptionCurrent(token);
        if (!cancelled) setCurrent(data);
      } catch (e) {
        console.warn("fetchSubscriptionCurrent failed", e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (Platform.OS !== "ios") {
      setStoreCatalog({});
      setStoreCatalogReady(true);
      return;
    }
    let cancelled = false;
    setStoreCatalogReady(false);
    void (async () => {
      try {
        const cat = await loadIosStoreCatalog();
        if (!cancelled) setStoreCatalog(cat);
      } catch (e) {
        console.warn("[IAP] loadIosStoreCatalog failed (subscription screen):", e);
      } finally {
        if (!cancelled) setStoreCatalogReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const activePlan: SubscriptionPlanType | null = useMemo(() => {
    if (!current?.plan) return null;
    const p = current.plan as SubscriptionPlanType;
    if (p === "free" || p === "scan_pack" || p === "pro_monthly" || p === "pro_yearly") return p;
    return null;
  }, [current?.plan]);

  const cards = useMemo(() => {
    const isCurrent = (p: SubscriptionPlanType) => activePlan === p;
    const paidPrice = (plan: "scan_pack" | "pro_monthly" | "pro_yearly", fallback: string) => {
      if (Platform.OS === "ios" && !storeCatalogReady) return t("subscription.priceLoading");
      return storeCatalog[plan]?.localizedPrice ?? fallback;
    };
    const paidTitle = (plan: "scan_pack" | "pro_monthly" | "pro_yearly", fallbackMain: string, fallbackSub: string) => {
      const info = storeCatalog[plan];
      if (info?.title) {
        return { main: info.title, sub: "" as const };
      }
      return { main: fallbackMain, sub: fallbackSub };
    };
    const paidDetails = (
      plan: "scan_pack" | "pro_monthly" | "pro_yearly",
      fallback: string[],
    ): string[] => {
      const desc = storeCatalog[plan]?.description ?? "";
      const fromStore = storeDescriptionToDetailLines(desc);
      return fromStore.length ? fromStore : fallback;
    };

    const sp = paidTitle("scan_pack", t("subscription.scanPackPlan"), "");
    const pm = paidTitle("pro_monthly", t("subscription.proMonthlyPlan"), "");
    const py = paidTitle("pro_yearly", t("subscription.proYearlyPlan"), "");

    return [
      {
        plan: "free" as const,
        titleMain: "FREE PLAN",
        titleSub: "",
        price: t("subscription.freePlanSubtitle"),
        details: ["* Basic artwork", "recognition"],
        badge: undefined as string | undefined,
        buttonText: isCurrent("free") ? "CURRENT PLAN" : "CHANGE PLAN",
        note: undefined as string | undefined,
        theme: (isCurrent("free") ? "filled" : "outline") as CardTheme,
        isCurrent: isCurrent("free"),
      },
      {
        plan: "scan_pack" as const,
        titleMain: sp.main,
        titleSub: sp.sub,
        price: paidPrice("scan_pack", t("subscription.scanPackPrice")),
        details: paidDetails("scan_pack", ["* 50 Scans", "*Best for", "occasional visits"]),
        badge: undefined as string | undefined,
        buttonText: t("subscription.buyScanPack"),
        note: undefined as string | undefined,
        theme: "outline" as CardTheme,
        isCurrent: false,
      },
      {
        plan: "pro_monthly" as const,
        titleMain: pm.main,
        titleSub: pm.sub,
        price: paidPrice("pro_monthly", t("subscription.proMonthlyPrice")),
        details: paidDetails("pro_monthly", ["* 200 scans / month", "*Perfect for", "museum lovers"]),
        badge: "MOST POPULAR !",
        buttonText: isCurrent("pro_monthly") ? "CURRENT PLAN" : "START PRO",
        note: "Cancel anytime",
        theme: (isCurrent("pro_monthly") ? "filled" : "outline") as CardTheme,
        isCurrent: isCurrent("pro_monthly"),
      },
      {
        plan: "pro_yearly" as const,
        titleMain: py.main,
        titleSub: py.sub,
        price: paidPrice("pro_yearly", t("subscription.proYearlyPrice")),
        details: paidDetails("pro_yearly", ["* 200 scans / month", "*2,400 scans / year", "*Best for frequent visitors"]),
        badge: undefined as string | undefined,
        buttonText: isCurrent("pro_yearly") ? "CURRENT PLAN" : "CHANGE PLAN",
        note: "Cancel anytime",
        theme: (isCurrent("pro_yearly") ? "filled" : "outline") as CardTheme,
        isCurrent: isCurrent("pro_yearly"),
      },
    ];
  }, [activePlan, storeCatalog, storeCatalogReady, t]);

  const showStoreCatalogHint = useMemo(() => {
    if (Platform.OS !== "ios" || !storeCatalogReady) return false;
    return !storeCatalog.scan_pack && !storeCatalog.pro_monthly && !storeCatalog.pro_yearly;
  }, [storeCatalog, storeCatalogReady]);

  const onActivate = async (plan: SubscriptionPlanType) => {
    if (!token) {
      Alert.alert(t("result.needLoginTitle"), t("result.needLoginText"), [
        { text: t("result.goSignIn"), onPress: () => router.push("/collection") },
      ]);
      return;
    }
    if (plan !== "free" && Platform.OS !== "ios") {
      Alert.alert(t("subscription.title"), t("subscription.iosOnlyPurchase"));
      return;
    }
    try {
      setActivating(plan);
      if (plan === "free") {
        const data = await activateSubscriptionPlan(token, plan);
        setCurrent(data);
      } else {
        await purchaseIosPlanThenActivate(token, plan);
        const data = await fetchSubscriptionCurrent(token);
        setCurrent(data);
      }
    } catch (e) {
      if (e instanceof Error && e.message === "E_USER_CANCELLED") {
        return;
      }
      const isIosOnly = e instanceof Error && e.message === "SUBSCRIPTION_IOS_ONLY";
      const storeUnavailable = e instanceof Error && e.message === STORE_PRODUCT_UNAVAILABLE;
      Alert.alert(
        t("result.recognizeFailedTitle"),
        isIosOnly
          ? t("subscription.iosOnlyPurchase")
          : storeUnavailable
            ? t("subscription.storeCatalogEmpty")
            : e instanceof Error
              ? e.message
              : t("camera.unknownError"),
      );
    } finally {
      setActivating(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={BRAND_RED} />
      </View>
    );
  }

  if (!token) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Subscription</Text>
        <Text style={styles.hint}>{t("collection.saveFavoritesSubtitle")}</Text>
        <Pressable style={styles.primaryButton} onPress={() => router.push("/collection")}>
          <Text style={styles.primaryButtonText}>{t("result.goSignIn")}</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headline} numberOfLines={2}>
          unlock full{"\n"}experience
        </Text>
        <Pressable style={styles.headerScan} onPress={() => router.push("/")}>
          <View style={styles.scanFrame}>
            <View style={[styles.scanCorner, styles.scanTopLeft]} />
            <View style={[styles.scanCorner, styles.scanTopRight]} />
            <View style={[styles.scanCorner, styles.scanBottomLeft]} />
            <View style={[styles.scanCorner, styles.scanBottomRight]} />
            <Text style={styles.scanText}>SCAN</Text>
          </View>
        </Pressable>
      </View>

      <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        {showStoreCatalogHint ? (
          <Text style={styles.storeHint}>{t("subscription.storeCatalogEmpty")}</Text>
        ) : null}
        <View style={styles.grid}>
          {cards.map((c) => (
            <PlanCard
              key={c.plan}
              titleMain={c.titleMain}
              titleSub={c.titleSub || undefined}
              price={c.price}
              details={c.details}
              badge={c.badge}
              buttonText={activating === c.plan ? "..." : c.buttonText}
              note={c.note}
              theme={c.theme}
              onPress={() => onActivate(c.plan)}
              disabled={
                c.isCurrent ||
                activating !== null ||
                (Platform.OS === "ios" && c.plan !== "free" && !storeCatalogReady)
              }
            />
          ))}
        </View>
      </ScrollView>

      <View style={[styles.bottomBar, { paddingBottom: Math.max(insets.bottom, 6) }]}>
        <Pressable style={styles.closeWrap} onPress={() => router.back()}>
          <View style={styles.closeXLeft} />
          <View style={styles.closeXRight} />
        </Pressable>
        <Text style={styles.bottomSlogan}>Discover art like never before.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6E7D7",
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  storeHint: {
    color: BRAND_RED,
    fontSize: 12,
    lineHeight: 16,
    marginBottom: 12,
    opacity: 0.92,
  },
  bottomBar: {
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 4,
    backgroundColor: "#F6E7D7",
  },
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#F6E7D7",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 52,
    paddingBottom: 14,
  },
  /** 与 scanFrame 同高 88，两行 lineHeight 44 → 总高 88 */
  headline: {
    color: BRAND_RED,
    fontSize: 32,
    lineHeight: 44,
    height: 88,
    fontWeight: "900",
    letterSpacing: 0.2,
    flex: 1,
    marginTop: 0,
    paddingRight: 8,
    textAlignVertical: "center",
  },
  headerScan: {
    justifyContent: "space-between",
    alignItems: "center",
  },
  scanFrame: {
    width: 88,
    aspectRatio: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  scanText: {
    color: BRAND_RED,
    fontSize: 22,
    fontWeight: "700",
  },
  scanCorner: {
    position: "absolute",
    width: 30,
    height: 30,
    borderColor: BRAND_RED,
  },
  scanTopLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  scanTopRight: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
  },
  scanBottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
  },
  scanBottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 3,
    borderRightWidth: 3,
  },
  title: {
    fontSize: 26,
    fontWeight: "900",
    color: BRAND_RED,
    textAlign: "center",
    marginBottom: 10,
  },
  hint: {
    color: BRAND_RED,
    textAlign: "center",
    marginBottom: 18,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    rowGap: 14,
  },
  card: {
    width: "48.3%",
    borderRadius: 20,
    borderWidth: 2,
    borderColor: BRAND_RED,
    paddingTop: 14,
    paddingBottom: 10,
    paddingHorizontal: 10,
    minHeight: 250,
  },
  cardOutline: {
    backgroundColor: CARD_BG,
  },
  cardFilled: {
    backgroundColor: BRAND_RED,
  },
  cardTitleRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "center",
    gap: 6,
    marginBottom: 6,
  },
  cardTitleMain: {
    color: BRAND_RED,
    fontWeight: "900",
    fontSize: 45 / 2,
    letterSpacing: 0.2,
  },
  cardTitleMainFilled: {
    color: WHITE,
  },
  cardTitleSub: {
    color: BRAND_RED,
    fontWeight: "800",
    fontSize: 24 / 2,
    marginBottom: 2,
  },
  cardTitleSubFilled: {
    color: WHITE,
  },
  cardPrice: {
    color: BRAND_RED,
    fontSize: 47 / 2,
    fontWeight: "900",
    textAlign: "center",
    marginTop: 2,
    marginBottom: 10,
  },
  cardPriceFilled: {
    color: WHITE,
  },
  cardDetailBlock: {
    alignItems: "center",
    minHeight: 56,
    paddingVertical: 10,
    marginBottom: 6,
  },
  cardDetailText: {
    color: BRAND_RED,
    fontSize: 19,
    textAlign: "center",
    lineHeight: 22,
  },
  cardDetailTextFilled: {
    color: WHITE,
  },
  cardBadge: {
    color: BRAND_RED,
    fontWeight: "900",
    fontSize: 38 / 2,
    textAlign: "center",
    marginBottom: 8,
  },
  cardBadgeFilled: {
    color: WHITE,
  },
  cardButton: {
    borderRadius: 9999,
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginTop: "auto",
  },
  cardButtonOutline: {
    borderColor: BRAND_RED,
    backgroundColor: BRAND_RED,
  },
  cardButtonFilled: {
    borderColor: CARD_BG,
    backgroundColor: CARD_BG,
  },
  cardButtonText: {
    color: WHITE,
    fontWeight: "800",
    fontSize: 19,
    letterSpacing: 0.2,
    textAlign: "center",
  },
  cardButtonTextFilled: {
    color: BRAND_RED,
  },
  disabledText: {
    opacity: 0.9,
  },
  cardNote: {
    color: BRAND_RED,
    textAlign: "center",
    fontSize: 10,
    marginTop: 4,
  },
  cardNoteFilled: {
    color: CARD_BG,
  },
  closeWrap: {
    width: 36,
    height: 36,
    alignSelf: "center",
    marginBottom: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  closeXLeft: {
    position: "absolute",
    width: 34,
    height: 2.2,
    backgroundColor: BRAND_RED,
    transform: [{ rotate: "45deg" }],
    borderRadius: 2,
  },
  closeXRight: {
    position: "absolute",
    width: 34,
    height: 2.2,
    backgroundColor: BRAND_RED,
    transform: [{ rotate: "-45deg" }],
    borderRadius: 2,
  },
  bottomSlogan: {
    textAlign: "center",
    color: BRAND_RED,
    fontSize: 44 / 2,
    fontWeight: "900",
    letterSpacing: 0.2,
    marginTop: 4,
  },
  primaryButton: {
    backgroundColor: BRAND_RED,
    borderRadius: 999,
    paddingHorizontal: 18,
    paddingVertical: 12,
    alignSelf: "center",
  },
  primaryButtonText: {
    color: WHITE,
    fontWeight: "900",
  },
});

