import { Platform } from "react-native";
import {
  ErrorCode,
  PurchaseError,
  finishTransaction,
  getProducts,
  getSubscriptions,
  initConnection,
  requestPurchase,
  requestSubscription,
  type Purchase,
} from "react-native-iap";

import { activateSubscriptionPlan, type SubscriptionPlanType } from "../services/api";

/** 与 App Store Connect 中 In-App Purchase 的 Product ID 一致 */
export const APPLE_PRODUCT_IDS = {
  scan_pack: "com.ottozhang.artiou.scan_pack",
  pro_monthly: "com.ottozhang.artiou.subscription.scan_pro.monthly",
  pro_yearly: "com.ottozhang.artiou.subscription.scan_pro.ywarly",
} as const;

export type PaidPlanType = Exclude<SubscriptionPlanType, "free">;

/** StoreKit 返回的展示信息（对应 ASC 里的显示名称、描述、价格档位） */
export type StoreProductInfo = {
  productId: string;
  localizedPrice: string;
  title: string;
  description: string;
};

export type StoreCatalog = Partial<Record<PaidPlanType, StoreProductInfo>>;

/** 把 ASC / StoreKit 的 description 拆成卡片多行展示 */
export function storeDescriptionToDetailLines(description: string, maxLines: number = 6): string[] {
  const raw = description.trim();
  if (!raw) return [];
  const byNl = raw
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const lines = byNl.length ? byNl : [raw];
  return lines.slice(0, maxLines).map((line) => (line.startsWith("*") ? line : `* ${line}`));
}

let connectionPromise: Promise<boolean> | null = null;

/** 统一前缀，Release 下也能在 Xcode / 设备日志里搜到 */
function iapLog(...args: unknown[]) {
  console.log("[IAP]", ...args);
}

export function ensureIapConnection(): Promise<boolean> {
  if (Platform.OS !== "ios") return Promise.resolve(false);
  if (!connectionPromise) {
    connectionPromise = initConnection().catch((err) => {
      console.warn("[IAP] initConnection rejected:", err);
      return false;
    });
  }
  return connectionPromise;
}

function pickInfo(
  productId: string,
  localizedPrice: string | undefined,
  title: string | undefined,
  description: string | undefined,
): StoreProductInfo | null {
  if (!localizedPrice?.trim()) return null;
  return {
    productId,
    localizedPrice: localizedPrice.trim(),
    title: (title ?? "").trim(),
    description: (description ?? "").trim(),
  };
}

/**
 * 从 App Store 拉取商品展示名、描述、本地化价格（与 ASC 中配置一致）。
 * 需真机；模拟器常返回空。不要求用户已登录。
 */
export async function loadIosStoreCatalog(): Promise<StoreCatalog> {
  if (Platform.OS !== "ios") {
    iapLog("loadIosStoreCatalog skipped (not iOS)");
    return {};
  }
  iapLog("loadIosStoreCatalog: start");
  const connected = await ensureIapConnection();
  if (!connected) {
    console.warn("[IAP] initConnection returned false — StoreKit unavailable, catalog empty");
    return {};
  }
  // Scan Pack 在 ASC 为消耗型/一次性 IAP → 仅 getProducts；勿放进 getSubscriptions
  const subSkus = [APPLE_PRODUCT_IDS.pro_monthly, APPLE_PRODUCT_IDS.pro_yearly];
  let packProducts: Awaited<ReturnType<typeof getProducts>> = [];
  let subs: Awaited<ReturnType<typeof getSubscriptions>> = [];
  try {
    // 须串行：RN IAP 在 iOS 上对并发请求会取消前一个，报
    // "Previous request was cancelled due to a new request"
    packProducts = await getProducts({ skus: [APPLE_PRODUCT_IDS.scan_pack] });
    subs = await getSubscriptions({ skus: subSkus });
  } catch (err) {
    console.warn("[IAP] getProducts / getSubscriptions threw:", err);
    return {};
  }
  iapLog(
    "raw counts — getProducts:",
    packProducts?.length ?? 0,
    "getSubscriptions:",
    subs?.length ?? 0,
  );
  const out: StoreCatalog = {};
  const pack = packProducts[0];
  if (pack?.productId) {
    const info = pickInfo(pack.productId, pack.localizedPrice, pack.title, pack.description);
    if (info) out.scan_pack = info;
  }
  for (const s of subs) {
    if (!("localizedPrice" in s) || !s.productId) continue;
    const title = "title" in s ? (s.title as string | undefined) : undefined;
    const description = "description" in s ? (s.description as string | undefined) : undefined;
    const info = pickInfo(s.productId, s.localizedPrice, title, description);
    if (!info) continue;
    if (s.productId === APPLE_PRODUCT_IDS.pro_monthly) out.pro_monthly = info;
    if (s.productId === APPLE_PRODUCT_IDS.pro_yearly) out.pro_yearly = info;
  }
  iapLog("Store catalog from App Store:", JSON.stringify(out));
  return out;
}

function skuForPaidPlan(plan: PaidPlanType): string {
  return APPLE_PRODUCT_IDS[plan];
}

/** App Store 未返回该 SKU（或未就绪）时抛出，供 UI 映射为本地化说明 */
export const STORE_PRODUCT_UNAVAILABLE = "STORE_PRODUCT_UNAVAILABLE";

/**
 * iOS：StoreKit 1/2 的购买都依赖「先 getProducts / getSubscriptions 把商品放进原生缓存」，
 * 否则 requestPurchase / requestSubscription 会报 Invalid product ID（与是否消耗型无关）。
 * 须在每次购买前调用，避免用户抢在订阅页首次拉目录完成前点击。
 */
async function ensureIosSkuLoadedBeforePurchase(plan: PaidPlanType, sku: string): Promise<void> {
  if (plan === "scan_pack") {
    const products = await getProducts({ skus: [sku] });
    if (!products?.length) {
      throw new Error(STORE_PRODUCT_UNAVAILABLE);
    }
    return;
  }
  const subs = await getSubscriptions({ skus: [sku] });
  if (!subs?.length) {
    throw new Error(STORE_PRODUCT_UNAVAILABLE);
  }
}

function normalizePurchase(result: Purchase | Purchase[] | void | null): Purchase | null {
  if (result == null) return null;
  if (Array.isArray(result)) return result[0] ?? null;
  return result;
}

function isUserCancelled(e: unknown): boolean {
  return e instanceof PurchaseError && e.code === ErrorCode.E_USER_CANCELLED;
}

/**
 * iOS：先走 StoreKit 购买，成功后再调用现有后端 /subscription/activate 同步额度。
 * 生产环境应在服务端用 App Store 收据校验替代「仅靠 activate」。
 */
export async function purchaseIosPlanThenActivate(token: string, plan: PaidPlanType): Promise<void> {
  if (Platform.OS !== "ios") {
    throw new Error("SUBSCRIPTION_IOS_ONLY");
  }
  await ensureIapConnection();
  const sku = skuForPaidPlan(plan);
  const autoFinish = false;
  try {
    await ensureIosSkuLoadedBeforePurchase(plan, sku);
    let purchase: Purchase | null = null;
    if (plan === "scan_pack") {
      purchase = normalizePurchase(
        await requestPurchase({
          sku,
          andDangerouslyFinishTransactionAutomaticallyIOS: autoFinish,
        }),
      );
    } else {
      purchase = normalizePurchase(
        await requestSubscription({ sku, andDangerouslyFinishTransactionAutomaticallyIOS: autoFinish }),
      );
    }
    await activateSubscriptionPlan(token, plan);
    if (purchase?.transactionId) {
      await finishTransaction({
        purchase,
        isConsumable: plan === "scan_pack",
      });
    }
  } catch (e) {
    if (isUserCancelled(e)) {
      throw new Error("E_USER_CANCELLED");
    }
    throw e;
  }
}
