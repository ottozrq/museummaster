import { useEffect } from "react";
import { Stack } from "expo-router";
import { setAudioModeAsync } from "expo-audio";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { useI18n } from "../src/i18n";

export default function RootLayout() {
  const { t } = useI18n();
  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
    }).catch((e) => console.warn("Audio mode setup failed", e));
  }, []);

  return (
    <SafeAreaProvider>
    <Stack>
      <Stack.Screen
        name="index"
        options={{ title: t("nav.camera"), headerShown: false }}
      />
      <Stack.Screen
        name="result"
        options={{ title: t("nav.result"), headerShown: false }}
      />
      <Stack.Screen name="history" options={{ title: t("nav.history") }} />
      <Stack.Screen
        name="collection"
        options={{ title: t("nav.collection"), headerShown: false }}
      />
      <Stack.Screen
        name="settings"
        options={{ title: t("nav.settings"), headerShown: false }}
      />
      <Stack.Screen
        name="subscription"
        options={{ title: t("nav.subscription"), headerShown: false }}
      />
      <Stack.Screen
        name="privacy"
        options={{ title: t("nav.privacy"), headerShown: false }}
      />
      <Stack.Screen
        name="terms"
        options={{ title: t("nav.terms"), headerShown: false }}
      />
    </Stack>
    </SafeAreaProvider>
  );
}
