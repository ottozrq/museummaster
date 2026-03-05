import AsyncStorage from "@react-native-async-storage/async-storage";
import { File, Paths } from "expo-file-system";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
} from "expo-audio";
import { AnalyzeStreamHandlers, analyzeImageStream, createSpeech } from "../src/services/api";
import {
  Back15Icon,
  Forward30Icon,
  PlayCircleIcon,
  PauseCircleIcon,
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
  const initialText = useMemo(() => params.text ?? "", [params.text]);
  const imageUri = useMemo(() => params.imageUri ?? "", [params.imageUri]);

  const [text, setText] = useState(initialText);
  const [streaming, setStreaming] = useState(false);
  const [requestingSpeech, setRequestingSpeech] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCollectedToast, setShowCollectedToast] = useState(false);
  const [isFastSpeed, setIsFastSpeed] = useState(false);
  const [progressBarWidth, setProgressBarWidth] = useState(0);
  const player = useAudioPlayer(null);
  const status = useAudioPlayerStatus(player);

  const hasAudio = Number.isFinite(status?.duration) && (status?.duration ?? 0) > 0;

  // 当没有直接传入讲解文本但有图片时，在结果页发起流式识别
  useEffect(() => {
    if (initialText || !imageUri) return;

    setStreaming(true);

    const handlers: AnalyzeStreamHandlers = {
      onText: (fullText) => {
        setText(fullText);
      },
      onError: (error) => {
        setStreaming(false);
        Alert.alert("识别失败", error.message || "未知错误");
      },
      onDone: () => {
        setStreaming(false);
      },
    };

    let cleanup: (() => void) | undefined;

    analyzeImageStream(imageUri, handlers)
      .then((stop) => {
        cleanup = stop;
      })
      .catch((error) => {
        setStreaming(false);
        Alert.alert("识别失败", error instanceof Error ? error.message : "未知错误");
      });

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, [initialText, imageUri]);

  const onPlayTTS = async () => {
    if (!text) return;

    // 正在请求音频时，直接忽略点击
    if (requestingSpeech) return;

    // 已在播放时，点击即暂停
    if (status?.playing) {
      player.pause();
      return;
    }

    // 已有音频但没在播，直接播放
    if (hasAudio) {
      player.play();
      return;
    }

    // 首次点击，需要向后端请求 TTS
    setRequestingSpeech(true);
    try {
      await setAudioModeAsync({
        playsInSilentMode: true,
      });

      const speech = await createSpeech(text);
      const playFile = new File(Paths.cache, `guide-${Date.now()}.mp3`);
      await playFile.write(speech.audio_base64, { encoding: "base64" });

      player.replace(playFile.uri);
      player.play();
    } catch (error) {
      Alert.alert("播放失败", error instanceof Error ? error.message : "未知错误");
    } finally {
      setRequestingSpeech(false);
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
        const collectionFile = new File(Paths.document, `collection-${id}.mp3`);
        await collectionFile.write(speech.audio_base64, { encoding: "base64" });
        audioUri = collectionFile.uri;
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

  const duration = status?.duration ?? 0;
  const currentTime = status?.currentTime ?? 0;
  const progress =
    duration > 0 && Number.isFinite(duration) && Number.isFinite(currentTime)
      ? Math.min(1, Math.max(0, currentTime / duration))
      : 0;

  const formatTime = (value: number) => {
    if (!Number.isFinite(value) || value <= 0) return "0:00";
    const total = Math.floor(value);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const handleSeek = async (offset: number) => {
    if (!Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0) {
      return;
    }
    const target = Math.min(duration, Math.max(0, currentTime + offset));
    try {
      await player.seekTo(target);
    } catch (e) {
      console.warn("seek failed", e);
    }
  };

  const seekToRatio = (ratio: number) => {
    if (!Number.isFinite(duration) || duration <= 0) return;
    const clamped = Math.min(1, Math.max(0, ratio));
    const target = clamped * duration;
    player.seekTo(target).catch((e) => console.warn("seek failed", e));
  };

  const handleSeekBarPosition = (x: number) => {
    if (progressBarWidth <= 0) return;
    seekToRatio(x / progressBarWidth);
  };

  const toggleSpeed = () => {
    try {
      const next = !isFastSpeed;
      setIsFastSpeed(next);
      player.setPlaybackRate(next ? 1.5 : 1.0);
    } catch (e) {
      console.warn("set playback rate failed", e);
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
            {streaming ? "AI 正在为你讲解本次识别到的展品…" : "AI 为你讲解本次识别到的展品"}
          </Text>

          <ScrollView
            style={styles.descriptionScroll}
            contentContainerStyle={styles.descriptionContent}
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.body}>
              {text || (streaming ? "AI 正在分析这件艺术品，请稍候…" : "暂无结果")}
            </Text>
          </ScrollView>
        </View>

        {/* Bottom player bar */}
        <View style={styles.playerSection}>
          <View style={styles.progressRow}>
            <Text style={styles.timeText}>{formatTime(currentTime)}</Text>
            <View
              style={styles.progressBar}
              onLayout={(e) => setProgressBarWidth(e.nativeEvent.layout.width)}
              onStartShouldSetResponder={() => true}
              onMoveShouldSetResponder={() => true}
              onResponderGrant={(e) =>
                handleSeekBarPosition(e.nativeEvent.locationX)
              }
              onResponderMove={(e) =>
                handleSeekBarPosition(e.nativeEvent.locationX)
              }
              onResponderRelease={(e) =>
                handleSeekBarPosition(e.nativeEvent.locationX)
              }
            >
              <View
                style={[
                  styles.progressFill,
                  { width: `${progress * 100}%` },
                ]}
              />
            </View>
            <Text style={styles.timeText}>{formatTime(duration)}</Text>
          </View>

          <View style={styles.controlsRow}>
            <View style={styles.sideControlsLeft}>
              <Pressable
                style={styles.smallControl}
                onPress={() => handleSeek(-15)}
              >
                <Back15Icon width={30} height={30} />
              </Pressable>
            </View>

            <Pressable
              style={styles.playButton}
              onPress={onPlayTTS}
              disabled={requestingSpeech || !text}
            >
              {requestingSpeech ? (
                <ActivityIndicator size="small" color="#E2461B" />
              ) : status?.playing ? (
                <PauseCircleIcon width={32} height={32} />
              ) : (
                <PlayCircleIcon width={32} height={32} />
              )}
            </Pressable>

            <View style={styles.sideControlsRight}>
              <Pressable
                style={styles.smallControl}
                onPress={() => handleSeek(30)}
              >
                <Forward30Icon width={30} height={30} />
              </Pressable>

              <Pressable style={styles.speedBadge} onPress={toggleSpeed}>
                <Speed2Icon width={29} height={29} />
              </Pressable>
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
