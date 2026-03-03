import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import {
  FlatList,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

type CollectionItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
  audioUri?: string;
};

const COLLECTION_KEY = "museum_guide_collection";

export default function CollectionScreen() {
  const router = useRouter();
  const [items, setItems] = useState<CollectionItem[]>([]);

  const load = useCallback(async () => {
    const raw = await AsyncStorage.getItem(COLLECTION_KEY);
    const parsed: CollectionItem[] = raw ? JSON.parse(raw) : [];
    setItems(parsed);
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const sections = useMemo(() => {
    const byDate: Record<string, CollectionItem[]> = {};
    for (const item of items) {
      const d = new Date(item.createdAt);
      const key = d.toISOString().slice(0, 10); // yyyy-mm-dd
      if (!byDate[key]) byDate[key] = [];
      byDate[key].push(item);
    }

    return Object.entries(byDate)
      .sort((a, b) => b[0].localeCompare(a[0])) // 最新日期在上
      .map(([key, group]) => {
        const d = new Date(key);
        const label = `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1)
          .toString()
          .padStart(2, "0")}/${d.getFullYear()}`;
        return { dateKey: key, label, items: group };
      });
  }, [items]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitleLine1}>MY</Text>
          <Text style={styles.headerTitleLine2}>ARTIOU</Text>
        </View>

        <Pressable
          style={styles.headerScan}
          onPress={() => router.push("/")}
        >
          <View style={styles.scanFrame}>
            <View style={[styles.scanCorner, styles.scanTopLeft]} />
            <View style={[styles.scanCorner, styles.scanTopRight]} />
            <View style={[styles.scanCorner, styles.scanBottomLeft]} />
            <View style={[styles.scanCorner, styles.scanBottomRight]} />
            <Text style={styles.scanText}>SCAN</Text>
          </View>
        </Pressable>
      </View>

      <FlatList
        data={sections}
        keyExtractor={(section) => section.dateKey}
        contentContainerStyle={styles.content}
        ListEmptyComponent={<Text style={styles.empty}>暂无收藏</Text>}
        renderItem={({ item: section }) => (
          <View style={styles.section}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.thumbScrollContent}
            >
              {section.items.map((item) => (
                <Pressable
                  key={item.id}
                  style={styles.thumbWrapper}
                  onPress={() =>
                    router.push({
                      pathname: "/result",
                      params: { text: item.text, imageUri: item.imageUri ?? "" },
                    })
                  }
                >
                  {item.imageUri ? (
                    <Image source={{ uri: item.imageUri }} style={styles.thumb} />
                  ) : (
                    <View style={[styles.thumb, styles.thumbPlaceholder]} />
                  )}
                </Pressable>
              ))}
            </ScrollView>
            <View style={styles.sectionFooter}>
              <Text style={styles.dateLabel}>{section.label}</Text>
            </View>
            <View style={styles.sectionDivider} />
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6E7D7",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 32,
    paddingBottom: 12,
  },
  headerTitleLine1: {
    fontSize: 44,
    fontWeight: "900",
    color: "#E2461B",
  },
  headerTitleLine2: {
    fontSize: 44,
    fontWeight: "900",
    color: "#E2461B",
  },
  headerScan: {
    alignItems: "center",
  },
  scanText: {
    color: "#E2461B",
    fontSize: 22,
    fontWeight: "700",
  },
  scanFrame: {
    width: 88,
    aspectRatio: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  scanCorner: {
    position: "absolute",
    width: 30,
    height: 30,
    borderColor: "#E2461B",
  },
  scanTopLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  scanTopRight: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
  },
  scanBottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
  },
  scanBottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 3,
    borderRightWidth: 3,
  },
  content: {
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  empty: {
    marginTop: 40,
    textAlign: "center",
    color: "#B07557",
  },
  section: {
    marginBottom: 16,
  },
  thumbScrollContent: {
    paddingRight: 16,
    marginBottom: 6,
  },
  thumbWrapper: {
    width: 100,
    marginRight: 12,
  },
  thumb: {
    width: "100%",
    aspectRatio: 1,
    borderRadius: 10,
  },
  thumbPlaceholder: {
    backgroundColor: "#e5d5c4",
  },
  sectionFooter: {
    alignItems: "flex-end",
    marginTop: 4,
  },
  dateLabel: {
    color: "#E2461B",
    fontSize: 14,
    fontWeight: "700",
    textDecorationLine: "underline",
  },
  sectionDivider: {
    marginTop: 6,
    height: 2,
    backgroundColor: "#E2461B",
  },
});
