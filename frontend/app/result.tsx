import AsyncStorage from "@react-native-async-storage/async-storage";
import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { createSpeech } from "../src/services/api";
import {
  Back15Icon,
  Forward30Icon,
  PlayCircleIcon,
  Speed2Icon,
} from "../src/components/PlayerIcons";

type HistoryItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
};

type CollectionItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
  audioUri?: string;
};

const HISTORY_KEY = "museum_guide_history";
const COLLECTION_KEY = "museum_guide_collection";

async function appendHistory(item: HistoryItem) {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const list: HistoryItem[] = raw ? JSON.parse(raw) : [];
  list.unshift(item);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 30)));
}

async function appendToCollection(item: CollectionItem) {
  const raw = await AsyncStorage.getItem(COLLECTION_KEY);
  const list: CollectionItem[] = raw ? JSON.parse(raw) : [];
  list.unshift(item);
  await AsyncStorage.setItem(COLLECTION_KEY, JSON.stringify(list));
}

export default function ResultScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ text?: string; imageUri?: string }>();
  const text = useMemo(() => params.text ?? "", [params.text]);
  const imageUri = useMemo(() => params.imageUri ?? "", [params.imageUri]);

  const [playing, setPlaying] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCollectedToast, setShowCollectedToast] = useState(false);

  const onPlayTTS = async () => {
    if (!text) return;
    setPlaying(true);

    try {
      const speech = await createSpeech(text);
      const filename = `${FileSystem.cacheDirectory}guide-${Date.now()}.mp3`;
      await FileSystem.writeAsStringAsync(filename, speech.audio_base64, {
        encoding: FileSystem.EncodingType.Base64,
      });

      const { sound } = await Audio.Sound.createAsync({ uri: filename });
      await sound.playAsync();

      sound.setOnPlaybackStatusUpdate(async (status) => {
        if (status.isLoaded && status.didJustFinish) {
          await sound.unloadAsync();
        }
      });
    } catch (error) {
      Alert.alert("播放失败", error instanceof Error ? error.message : "未知错误");
    } finally {
      setPlaying(false);
    }
  };

  const onAddToCollection = async () => {
    if (!text) return;
    setSaving(true);
    try {
      const id = `${Date.now()}`;
      const createdAt = new Date().toISOString();

      // 生成讲解音频并保存到本地持久化目录
      let audioUri: string | undefined;
      try {
        const speech = await createSpeech(text);
        const filename = `${FileSystem.documentDirectory}collection-${id}.mp3`;
        await FileSystem.writeAsStringAsync(filename, speech.audio_base64, {
          encoding: FileSystem.EncodingType.Base64,
        });
        audioUri = filename;
      } catch (e) {
        // 音频生成失败仍保存图片和文字
        console.warn("Collection: TTS failed", e);
      }

      const item: CollectionItem = {
        id,
        createdAt,
        imageUri: imageUri || undefined,
        text,
        audioUri,
      };
      await appendToCollection(item);

      // 中间半透明 Toast 提示
      setShowCollectedToast(true);
      setTimeout(() => {
        setShowCollectedToast(false);
      }, 1500);
    } catch (error) {
      Alert.alert("收藏失败", error instanceof Error ? error.message : "未知错误");
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.screen}>
      <StatusBar barStyle="dark-content" />

      {/* Top artwork area */}
      <View style={styles.heroSection}>
        {imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.heroImage} />
        ) : (
          <View style={styles.heroPlaceholder} />
        )}

        <View style={styles.heroActions}>
          <Pressable style={styles.iconButton} onPress={() => router.back()}>
            <Text style={styles.iconText}>✕</Text>
          </Pressable>

          <Pressable
            style={styles.iconButton}
            onPress={onAddToCollection}
            disabled={saving || !text}
          >
            <Text style={styles.iconText}>★</Text>
          </Pressable>
        </View>
      </View>

      {/* Details & description */}
      <View style={styles.detailsSection}>
        <View style={styles.textCard}>
          <Text style={styles.title} numberOfLines={2}>
            识别结果
          </Text>
          <Text style={styles.subtitle} numberOfLines={2}>
            AI 为你讲解本次识别到的展品
          </Text>

          <ScrollView
            style={styles.descriptionScroll}
            contentContainerStyle={styles.descriptionContent}
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.body}>{text || "暂无结果"}</Text>
          </ScrollView>
        </View>

        {/* Bottom player bar */}
        <View style={styles.playerSection}>
          <View style={styles.progressRow}>
            <Text style={styles.timeText}>1:00</Text>
            <View style={styles.progressBar}>
              <View style={styles.progressFill} />
            </View>
            <Text style={styles.timeText}>2:00</Text>
          </View>

          <View style={styles.controlsRow}>
            <View style={styles.sideControlsLeft}>
              <Pressable style={styles.smallControl}>
                <Back15Icon width={30} height={30} />
              </Pressable>
            </View>

            <Pressable
              style={styles.playButton}
              onPress={onPlayTTS}
              disabled={playing || !text}
            >
              <PlayCircleIcon width={32} height={32} />
            </Pressable>

            <View style={styles.sideControlsRight}>
              <Pressable style={styles.smallControl}>
                <Forward30Icon width={30} height={30} />
              </Pressable>

              <View style={styles.speedBadge}>
                <Speed2Icon width={29} height={29} />
              </View>
            </View>
          </View>
        </View>
      </View>

      {showCollectedToast && (
        <View style={styles.toastOverlay}>
          <View style={styles.toastContent}>
            <Text style={styles.toastText}>作品已加入收藏夹</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#F6E7D7",
  },
  heroSection: {
    height: 260,
    backgroundColor: "#000",
  },
  heroImage: {
    width: "100%",
    height: "100%",
    resizeMode: "cover",
  },
  heroPlaceholder: {
    flex: 1,
    backgroundColor: "#333",
  },
  heroActions: {
    position: "absolute",
    top: 40,
    left: 0,
    right: 0,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  iconButton: {
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  iconText: {
    color: "#E2461B",
    fontSize: 24,
    fontWeight: "700",
  },
  detailsSection: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 0,
    justifyContent: "space-between",
  },
  textCard: {
    flex: 1,
  },
  title: {
    fontSize: 26,
    fontWeight: "900",
    color: "#E2461B",
  },
  subtitle: {
    marginTop: 4,
    fontSize: 14,
    fontWeight: "700",
    color: "#E2461B",
  },
  descriptionScroll: {
    marginTop: 12,
  },
  descriptionContent: {
    paddingBottom: 16,
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    color: "#4B3621",
  },
  playerSection: {
    backgroundColor: "#E2461B",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 14,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    borderBottomLeftRadius: 22,
    borderBottomRightRadius: 22,
    marginTop: 12,
    marginBottom: 16,
  },
  toastOverlay: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  toastContent: {
    backgroundColor: "rgba(0,0,0,0.55)",
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 999,
  },
  toastText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  progressRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 4,
  },
  timeText: {
    color: "#F6E7D7",
    fontSize: 11,
  },
  progressBar: {
    flex: 1,
    height: 4,
    backgroundColor: "rgba(246,231,215,0.4)",
    marginHorizontal: 8,
    borderRadius: 999,
    overflow: "hidden",
  },
  progressFill: {
    width: "40%",
    height: "100%",
    backgroundColor: "#F6E7D7",
  },
  controlsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  sideControlsLeft: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    paddingRight: 16,
  },
  sideControlsRight: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    columnGap: 8,
    paddingLeft: 16,
  },
  smallControl: {
    paddingHorizontal: 4,
    paddingVertical: 4,
  },
  playButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#F6E7D7",
    alignItems: "center",
    justifyContent: "center",
  },
  speedBadge: {
    minWidth: 44,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    alignItems: "center",
    justifyContent: "center",
  },
});
