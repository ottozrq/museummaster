// 使用 expo-file-system 的 legacy API，以便在新版本中继续使用 readAsStringAsync
import * as FileSystem from "expo-file-system/legacy";
import AsyncStorage from "@react-native-async-storage/async-storage";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || "https://museumapi.ottozhang.com";
const USE_FAKE_ANALYZE = process.env.EXPO_PUBLIC_USE_FAKE_ANALYZE === "true";

type AnalyzeResponse = {
  text: string;
  scan_id?: string;
};

type TTSResponse = {
  audio_base64: string;
  mime_type: string;
  voice: string;
  audio_path?: string;
};

export type ScanRecord = {
  scan_id: string;
  artwork_code: string;
  image_path: string;
  text: string;
  audio_path?: string | null;
  inserted_at?: string;
};

export type ScanRecordCollection = {
  items: ScanRecord[];
  total?: number;
  page?: number;
  page_size?: number;
};

export type AnalyzeStreamHandlers = {
  onText: (fullText: string) => void;
  onError?: (error: Error) => void;
  onDone?: (scanId?: string) => void;
};

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fakeAnalyzeImage(_: string): Promise<AnalyzeResponse> {
  // 模拟网络延迟
  await sleep(1200);

  return {
    text: [
      "【作品标题】MONNA LISA（蒙娜丽莎）",
      "【艺术家】Leonardo da Vinci / 列奥纳多·达·芬奇",
      "【创作年份】约 1503–1506 年，文艺复兴盛期",
      "【艺术风格】意大利文艺复兴肖像画，强调写实光影与人物心理刻画。",
      "",
      "【历史背景】",
      "作品诞生于佛罗伦萨共和国向近代欧洲过渡的关键时期。",
      "当时人文主义思潮兴起，艺术家开始更加关注个体情绪与内心世界。",
      "",
      "【艺术意义】",
      "1. 神秘微笑：蒙娜丽莎的微笑介于“有”与“无”之间，被认为是人类表情最经典的捕捉之一。",
      "2. 光影塑形：达·芬奇使用“晕涂法（sfumato）”处理脸部与背景，使人物从阴影中自然浮现。",
      "3. 视线互动：无论观众站在何处，人物目光似乎都在注视你，增强了作品的参与感。",
      "4. 文化符号：从博物馆展陈到大众文化二次创作，蒙娜丽莎已成为“艺术”本身的象征之一。",
    ].join("\n"),
  };
}

export async function analyzeImage(
  uri: string,
  opts?: { locale?: string },
): Promise<AnalyzeResponse> {
  if (USE_FAKE_ANALYZE) {
    return fakeAnalyzeImage(uri);
  }

  const authToken = await AsyncStorage.getItem("museum_auth_token");

  const fileName = uri.split("/").pop() || "photo.jpg";
  const ext = fileName.split(".").pop()?.toLowerCase();
  const mimeType = ext === "png" ? "image/png" : "image/jpeg";

  const formData = new FormData();
  formData.append("image", {
    uri,
    name: fileName,
    type: mimeType,
  } as any);
  if (opts?.locale) {
    formData.append("locale", opts.locale);
  }

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: formData,
    headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
  });

  if (!response.ok) {
    // 429 这类“额度类”错误需要前端可本地化的 code
    if (response.status === 429) {
      try {
        const body = await response.json();
        const detail = body?.detail;
        const code =
          typeof detail === "object" && detail?.code
            ? String(detail.code)
            : "DAILY_SCAN_QUOTA_EXCEEDED";
        const msg =
          typeof detail === "object" && detail?.message
            ? String(detail.message)
            : typeof detail === "string"
              ? detail
              : "Scan quota exhausted.";
        const err = new Error(msg);
        (err as any).code = code;
        throw err;
      } catch {
        // fallback to text
      }
    }
    const errText = await response.text();
    throw new Error(`Analyze failed (${response.status}): ${errText}`);
  }

  return response.json();
}

export async function analyzeImageStream(
  uri: string,
  handlers: AnalyzeStreamHandlers,
  opts?: { authToken?: string | null; locale?: string },
): Promise<() => void> {
  if (USE_FAKE_ANALYZE) {
    const result = await fakeAnalyzeImage(uri);
    handlers.onText(result.text);
    handlers.onDone?.();
    return () => {};
  }

  const fileName = uri.split("/").pop() || "photo.jpg";
  const ext = fileName.split(".").pop()?.toLowerCase();
  const mimeType = ext === "png" ? "image/png" : "image/jpeg";

  const base64 = await FileSystem.readAsStringAsync(uri, {
    // 某些 SDK 版本不再导出 EncodingType 枚举，直接使用字符串更兼容
    encoding: "base64" as FileSystem.EncodingType,
  });

  // WebSocket 路径与后端 prefix=\"/analyze\" + websocket(\"\") 对应 => /analyze
  const wsUrl = API_BASE_URL.replace(/^http/, "ws") + "/analyze";
  const ws = new WebSocket(wsUrl);
  const authToken =
    opts?.authToken ?? (await AsyncStorage.getItem("museum_auth_token"));

  let closedManually = false;

  ws.onopen = () => {
    ws.send(
      JSON.stringify({
        type: "start",
        image_base64: base64,
        mime_type: mimeType,
        ...(opts?.locale ? { locale: opts.locale } : {}),
        ...(authToken ? { auth_token: authToken } : {}),
      }),
    );
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "delta") {
        handlers.onText(data.full ?? "");
      } else if (data.type === "done") {
        handlers.onDone?.(data.scan_id || undefined);
        ws.close();
      } else if (data.type === "error") {
        const err = new Error(data.message || "Analyze failed");
        if (data.code) {
          (err as any).code = data.code;
        }
        handlers.onError?.(err);
        ws.close();
      }
    } catch (e) {
      handlers.onError?.(
        e instanceof Error ? e : new Error("Invalid message from analyze stream"),
      );
      ws.close();
    }
  };

  ws.onerror = () => {
    handlers.onError?.(new Error("Analyze WebSocket error"));
  };

  ws.onclose = () => {
    if (!closedManually) {
      handlers.onDone?.();
    }
  };

  return () => {
    closedManually = true;
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}

export function getTtsStreamUrl(text: string): string {
  const url = new URL(`${API_BASE_URL}/tts`);
  url.searchParams.set("text", text);
  return url.toString();
}

export async function createSpeech(
  text: string,
  opts?: { scanId?: string },
): Promise<TTSResponse> {
  const response = await fetch(`${API_BASE_URL}/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      ...(opts?.scanId ? { scan_id: opts.scanId } : {}),
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`TTS failed (${response.status}): ${err}`);
  }

  return response.json();
}

export async function favoriteScanRecord(scanId: string, token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/scan_records/${scanId}/favorite`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Favorite failed (${response.status}): ${err}`);
  }
}

export async function unfavoriteScanRecord(scanId: string, token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/scan_records/${scanId}/favorite`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Unfavorite failed (${response.status}): ${err}`);
  }
}

export async function fetchMyFavorites(
  token: string,
  opts?: { pageToken?: string; pageSize?: number },
): Promise<ScanRecordCollection> {
  const pageToken = opts?.pageToken ?? "1";
  const pageSize = opts?.pageSize ?? 50;
  const url = new URL(`${API_BASE_URL}/users/me/favorites`);
  url.searchParams.set("page_token", pageToken);
  url.searchParams.set("page_size", String(pageSize));

  const response = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Fetch favorites failed (${response.status}): ${err}`);
  }

  return response.json();
}

export async function deleteMyAccount(token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/users/me`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Delete account failed (${response.status}): ${err}`);
  }
}

export async function fetchScanRecordById(scanId: string): Promise<ScanRecord> {
  const response = await fetch(`${API_BASE_URL}/scan-records/${scanId}`, {
    method: "GET",
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Fetch scan record failed (${response.status}): ${err}`);
  }

  return response.json();
}

export type SubscriptionCurrent = {
  plan: string;
  limit: number;
  used: number;
  remaining: number;
  pro_expires_at_ts?: number | null;
  scan_pack_total?: number | null;
  scan_pack_remaining?: number | null;
  daily_limit?: number | null;
  /** App Store：1=自动续费开启 0=已关闭（未过期前仍可用 Pro） */
  apple_auto_renew_status?: number | null;
  apple_original_transaction_id?: string | null;
  /** Pro：下一期 200 次额度重置时刻（UTC 次月同日 0:00），Unix 秒 */
  pro_next_quota_reset_ts?: number | null;
};

export async function fetchSubscriptionCurrent(token: string): Promise<SubscriptionCurrent> {
  const response = await fetch(`${API_BASE_URL}/subscription/current`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Fetch subscription failed (${response.status}): ${err}`);
  }
  return response.json();
}

export type SubscriptionPlanType = "free" | "scan_pack" | "pro_monthly" | "pro_yearly";

export async function activateSubscriptionPlan(
  token: string,
  plan_type: SubscriptionPlanType,
  opts?: {
    scan_pack_remaining?: number;
    apple_original_transaction_id?: string;
    apple_transaction_id?: string;
  },
): Promise<SubscriptionCurrent> {
  const response = await fetch(`${API_BASE_URL}/subscription/activate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      plan_type,
      ...(plan_type === "scan_pack" && opts?.scan_pack_remaining != null
        ? { scan_pack_remaining: opts.scan_pack_remaining }
        : {}),
      ...(opts?.apple_original_transaction_id != null
        ? { apple_original_transaction_id: opts.apple_original_transaction_id }
        : {}),
      ...(opts?.apple_transaction_id != null ? { apple_transaction_id: opts.apple_transaction_id } : {}),
    }),
  });
  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Activate subscription failed (${response.status}): ${err}`);
  }
  return response.json();
}

