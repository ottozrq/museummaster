import { useEffect } from "react";
import { Stack } from "expo-router";
import { setAudioModeAsync } from "expo-audio";

export default function RootLayout() {
  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
    }).catch((e) => console.warn("Audio mode setup failed", e));
  }, []);

  return (
    <Stack>
      <Stack.Screen
        name="index"
        options={{ title: "艺游", headerShown: false }}
      />
      <Stack.Screen
        name="result"
        options={{ title: "讲解结果", headerShown: false }}
      />
      <Stack.Screen name="history" options={{ title: "历史记录" }} />
      <Stack.Screen
        name="collection"
        options={{ title: "我的收藏夹", headerShown: false }}
      />
      <Stack.Screen
        name="privacy"
        options={{ title: "Privacy Policy", headerShown: false }}
      />
      <Stack.Screen
        name="terms"
        options={{ title: "Terms of Service", headerShown: false }}
      />
    </Stack>
  );
}
