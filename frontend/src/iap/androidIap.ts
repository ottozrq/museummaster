import { Platform } from "react-native";
import {
  ErrorCode,
  PurchaseError,
  PurchaseStateAndroid,
  finishTransaction,
  getAvailablePurchases,
  getProducts,
  getSubscriptions,
  initConnection,
  requestPurchase,
  requestSubscription,
  type ProductPurchase,
  type Purchase,
  type Subscription,
  type SubscriptionAndroid,
} from "react-native-iap";

import { activateSubscriptionPlan, type SubscriptionPlanType } from "../services/api";
import type { PaidPlanType, StoreCatalog, StoreProductInfo } from "./appleIap";

export const GOOGLE_PLAY_PRODUCT_IDS = {
  scan_pack: "com.ottozhang.artiou.iap.scan",
  pro_monthly: "com.ottozhang.artiou.sub.scan.pro.monthly",
  pro_yearly: "com.ottozhang.artiou.sub.scan.pro.yearly",
} as const;

export const GOOGLE_RESTORE_NOTHING_FOUND = "GOOGLE_RESTORE_NOTHING_FOUND";
export const GOOGLE_STORE_PRODUCT_UNAVAILABLE = "GOOGLE_STORE_PRODUCT_UNAVAILABLE";

let connectionPromise: Promise<boolean> | null = null;

function androidLog(...args: unknown[]) {
  console.log("[IAP:Android]", ...args);
}

export function ensureAndroidIapConnection(): Promise<boolean> {
  if (Platform.OS !== "android") return Promise.resolve(false);
  if (!connectionPromise) {
    connectionPromise = initConnection().catch((err) => {
      console.warn("[IAP:Android] initConnection rejected:", err);
      return false;
    });
  }
  return connectionPromise;
}

function productInfo(product: any): StoreProductInfo | null {
  const productId = String(product?.productId ?? "").trim();
  if (!productId) return null;
  const offer = product?.oneTimePurchaseOfferDetails;
  const localizedPrice = String(
    offer?.formattedPrice ?? product?.localizedPrice ?? product?.price ?? "",
  ).trim();
  if (!localizedPrice) return null;
  return {
    productId,
    localizedPrice,
    title: String(product?.name ?? product?.title ?? "").trim(),
    description: String(product?.description ?? "").trim(),
  };
}

function subscriptionInfo(subscription: Subscription): StoreProductInfo | null {
  const sub = subscription as SubscriptionAndroid;
  const productId = String(sub.productId ?? "").trim();
  if (!productId) return null;
  const firstOffer = sub.subscriptionOfferDetails?.[0];
  const firstPhase = firstOffer?.pricingPhases?.pricingPhaseList?.[0];
  const localizedPrice = String(firstPhase?.formattedPrice ?? "").trim();
  if (!localizedPrice) return null;
  return {
    productId,
    localizedPrice,
    title: String(sub.name ?? sub.title ?? "").trim(),
    description: String(sub.description ?? "").trim(),
  };
}

export async function loadAndroidStoreCatalog(): Promise<StoreCatalog> {
  if (Platform.OS !== "android") {
    androidLog("loadAndroidStoreCatalog skipped (not Android)");
    return {};
  }
  const connected = await ensureAndroidIapConnection();
  if (!connected) return {};

  const out: StoreCatalog = {};
  try {
    const products = await getProducts({ skus: [GOOGLE_PLAY_PRODUCT_IDS.scan_pack] });
    const info = productInfo(products?.[0]);
    if (info) out.scan_pack = info;
  } catch (err) {
    console.warn("[IAP:Android] getProducts threw:", err);
  }
  try {
    const subs = await getSubscriptions({
      skus: [GOOGLE_PLAY_PRODUCT_IDS.pro_monthly, GOOGLE_PLAY_PRODUCT_IDS.pro_yearly],
    });
    for (const sub of subs) {
      const info = subscriptionInfo(sub);
      if (!info) continue;
      if (info.productId === GOOGLE_PLAY_PRODUCT_IDS.pro_monthly) out.pro_monthly = info;
      if (info.productId === GOOGLE_PLAY_PRODUCT_IDS.pro_yearly) out.pro_yearly = info;
    }
  } catch (err) {
    console.warn("[IAP:Android] getSubscriptions threw:", err);
  }
  androidLog("Google Play catalog:", JSON.stringify(out));
  return out;
}

function skuForPaidPlan(plan: PaidPlanType): string {
  return GOOGLE_PLAY_PRODUCT_IDS[plan];
}

function paidPlanFromProductId(productId: string): PaidPlanType | null {
  if (productId === GOOGLE_PLAY_PRODUCT_IDS.scan_pack) return "scan_pack";
  if (productId === GOOGLE_PLAY_PRODUCT_IDS.pro_monthly) return "pro_monthly";
  if (productId === GOOGLE_PLAY_PRODUCT_IDS.pro_yearly) return "pro_yearly";
  return null;
}

function normalizePurchase(result: Purchase | Purchase[] | void | null): Purchase | null {
  if (result == null) return null;
  if (Array.isArray(result)) return result[0] ?? null;
  return result;
}

function productIdFromPurchase(purchase: Purchase): string {
  return purchase.productId || purchase.productIds?.[0] || "";
}

function purchasePayload(purchase: Purchase) {
  return {
    google_product_id: productIdFromPurchase(purchase),
    google_purchase_token: purchase.purchaseToken,
    google_order_id: purchase.transactionId,
    google_package_name: purchase.packageNameAndroid,
  };
}

function isAndroidPurchased(purchase: Purchase): boolean {
  return (
    purchase.purchaseStateAndroid == null ||
    purchase.purchaseStateAndroid === PurchaseStateAndroid.PURCHASED
  );
}

function isUserCancelled(e: unknown): boolean {
  if (e instanceof PurchaseError && e.code === ErrorCode.E_USER_CANCELLED) return true;
  return e instanceof Error && /cancel/i.test(e.message);
}

async function ensureAndroidSkuLoadedBeforePurchase(plan: PaidPlanType, sku: string): Promise<SubscriptionAndroid | null> {
  if (plan === "scan_pack") {
    const products = await getProducts({ skus: [sku] });
    if (!products?.length) throw new Error(GOOGLE_STORE_PRODUCT_UNAVAILABLE);
    return null;
  }
  const subs = await getSubscriptions({ skus: [sku] });
  const sub = subs.find((item) => item.productId === sku) as SubscriptionAndroid | undefined;
  if (!sub?.subscriptionOfferDetails?.length) throw new Error(GOOGLE_STORE_PRODUCT_UNAVAILABLE);
  return sub;
}

export async function purchaseAndroidPlanThenActivate(token: string, plan: PaidPlanType): Promise<void> {
  if (Platform.OS !== "android") throw new Error("SUBSCRIPTION_ANDROID_ONLY");
  const connected = await ensureAndroidIapConnection();
  if (!connected) throw new Error(GOOGLE_STORE_PRODUCT_UNAVAILABLE);
  const sku = skuForPaidPlan(plan);
  try {
    const sub = await ensureAndroidSkuLoadedBeforePurchase(plan, sku);
    const purchase = normalizePurchase(
      plan === "scan_pack"
        ? await requestPurchase({ skus: [sku] })
        : await requestSubscription({
            subscriptionOffers: [
              {
                sku,
                offerToken: sub?.subscriptionOfferDetails?.[0]?.offerToken ?? "",
              },
            ],
          }),
    );
    if (!purchase || !purchase.purchaseToken || !isAndroidPurchased(purchase)) {
      throw new Error(GOOGLE_STORE_PRODUCT_UNAVAILABLE);
    }
    await activateSubscriptionPlan(token, plan, purchasePayload(purchase));
    await finishTransaction({ purchase, isConsumable: plan === "scan_pack" });
  } catch (e) {
    if (isUserCancelled(e)) throw new Error("E_USER_CANCELLED");
    throw e;
  }
}

export async function restoreAndroidPurchasesThenActivate(token: string): Promise<SubscriptionPlanType> {
  if (Platform.OS !== "android") throw new Error("SUBSCRIPTION_ANDROID_ONLY");
  await ensureAndroidIapConnection();
  const purchases = await getAvailablePurchases();
  const matched: { plan: PaidPlanType; purchase: ProductPurchase }[] = [];
  for (const purchase of purchases) {
    const plan = paidPlanFromProductId(productIdFromPurchase(purchase));
    if (plan && purchase.purchaseToken && isAndroidPurchased(purchase)) {
      matched.push({ plan, purchase });
    }
  }
  if (!matched.length) throw new Error(GOOGLE_RESTORE_NOTHING_FOUND);
  const rank: Record<PaidPlanType, number> = {
    scan_pack: 1,
    pro_monthly: 2,
    pro_yearly: 3,
  };
  const best = matched.reduce((a, b) => (rank[b.plan] > rank[a.plan] ? b : a));
  await activateSubscriptionPlan(token, best.plan, purchasePayload(best.purchase));
  await finishTransaction({ purchase: best.purchase, isConsumable: best.plan === "scan_pack" });
  return best.plan;
}
