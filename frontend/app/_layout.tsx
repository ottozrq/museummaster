import { Stack } from "expo-router";

export default function RootLayout() {
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
    </Stack>
  );
}
