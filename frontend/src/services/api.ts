const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

type AnalyzeResponse = {
  text: string;
};

type TTSResponse = {
  audio_base64: string;
  mime_type: string;
  voice: string;
};

export async function analyzeImage(uri: string): Promise<AnalyzeResponse> {
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
