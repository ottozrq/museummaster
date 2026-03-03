const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || "https://museumapi.ottozhang.com";
const USE_FAKE_ANALYZE = process.env.EXPO_PUBLIC_USE_FAKE_ANALYZE === "true";

type AnalyzeResponse = {
  text: string;
};

type TTSResponse = {
  audio_base64: string;
  mime_type: string;
  voice: string;
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

export async function analyzeImage(uri: string): Promise<AnalyzeResponse> {
  if (USE_FAKE_ANALYZE) {
    return fakeAnalyzeImage(uri);
  }

  const fileName = uri.split("/").pop() || "photo.jpg";
  const ext = fileName.split(".").pop()?.toLowerCase();
  const mimeType = ext === "png" ? "image/png" : "image/jpeg";

  const formData = new FormData();
  formData.append("image", {
    uri,
    name: fileName,
    type: mimeType,
  } as any);

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Analyze failed (${response.status}): ${err}`);
  }

  return response.json();
}

export async function createSpeech(text: string): Promise<TTSResponse> {
  const response = await fetch(`${API_BASE_URL}/tts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`TTS failed (${response.status}): ${err}`);
  }

  return response.json();
}
