import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="index" options={{ title: "博物通" }} />
      <Stack.Screen name="result" options={{ title: "讲解结果" }} />
      <Stack.Screen name="history" options={{ title: "历史记录" }} />
    </Stack>
  );
}
