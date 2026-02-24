import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, Image, StyleSheet, Text, View } from "react-native";

type HistoryItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
};

const HISTORY_KEY = "museum_guide_history";

export default function HistoryScreen() {
  const [items, setItems] = useState<HistoryItem[]>([]);

  const load = useCallback(async () => {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    const parsed: HistoryItem[] = raw ? JSON.parse(raw) : [];
    setItems(parsed);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.content}
        ListEmptyComponent={<Text style={styles.empty}>暂无历史记录</Text>}
        renderItem={({ item }) => (
          <View style={styles.card}>
            {item.imageUri ? <Image source={{ uri: item.imageUri }} style={styles.thumb} /> : null}
            <Text style={styles.date}>{new Date(item.createdAt).toLocaleString()}</Text>
            <Text numberOfLines={4} style={styles.text}>
              {item.text}
            </Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f7fb",
  },
  content: {
    padding: 16,
    gap: 12,
  },
  empty: {
    marginTop: 40,
    textAlign: "center",
    color: "#627d98",
  },
  card: {
    backgroundColor: "#fff",
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d9e2ec",
    gap: 8,
  },
  thumb: {
    width: "100%",
    height: 140,
    borderRadius: 8,
  },
  date: {
    color: "#486581",
    fontSize: 12,
  },
  text: {
    color: "#102a43",
    lineHeight: 20,
  },
});
