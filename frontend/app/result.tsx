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
import {
  AnalyzeStreamHandlers,
  analyzeImageStream,
  createSpeech,
  favoriteScanRecord,
  fetchScanRecordById,
  getTtsStreamUrl,
  unfavoriteScanRecord,
} from "../src/services/api";
import { useI18n } from "../src/i18n";
import {
  Back15Icon,
  Forward30Icon,
  PlayCircleIcon,
  PauseCircleIcon,
  Speed2Icon,
} from "../src/components/PlayerIcons";

const HISTORY_KEY = "museum_guide_history";

type HistoryItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
};

async function appendHistory(item: HistoryItem) {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const list: HistoryItem[] = raw ? JSON.parse(raw) : [];
  list.unshift(item);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 30)));
}

export default function ResultScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const params = useLocalSearchParams<{
    text?: string;
    imageUri?: string;
    scanId?: string;
    authToken?: string;
  }>();
  const initialText = useMemo(() => params.text ?? "", [params.text]);
  const [imageUri, setImageUri] = useState(() => params.imageUri ?? "");

  const [text, setText] = useState(initialText);
  const [scanId, setScanId] = useState<string | null>(() => params.scanId ?? null);
  const [streaming, setStreaming] = useState(false);
  const [requestingSpeech, setRequestingSpeech] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCollectedToast, setShowCollectedToast] = useState(false);
  const [isFavorite, setIsFavorite] = useState(() => !!params.scanId);
  const [isFastSpeed, setIsFastSpeed] = useState(false);
  const [progressBarWidth, setProgressBarWidth] = useState(0);
  const [downloadedAudioUri, setDownloadedAudioUri] = useState<string | null>(null);
  const [preloadingSpeech, setPreloadingSpeech] = useState(false);
  const [streamLoading, setStreamLoading] = useState(false);
  const isPlayingStreamRef = useRef(false);
  const player = useAudioPlayer(null);
  const status = useAudioPlayerStatus(player);

  // 流式播放已发起但尚未开始出声时，保持播放按钮显示加载
  useEffect(() => {
    if (streamLoading && status?.playing) {
      setStreamLoading(false);
    }
  }, [streamLoading, status?.playing]);

  const hasAudio = Number.isFinite(status?.duration) && (status?.duration ?? 0) > 0;

  // 有 scanId（来自收藏列表）但没有文本时，从后端加载该扫描记录
  useEffect(() => {
    if (text || !scanId) return;
    let cancelled = false;
    (async () => {
      try {
        const rec = await fetchScanRecordById(scanId);
        if (cancelled) return;
        setText(rec.text);
        if (rec.image_path) {
          setImageUri(`${process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || "https://museumapi.ottozhang.com"}${rec.image_path}`);
        }
      } catch (e) {
        if (!cancelled) {
          Alert.alert(
            t("result.loadFailedTitle"),
            e instanceof Error ? e.message : t("result.loadFailedFallback"),
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [scanId, text]);

  // 当没有直接传入讲解文本但有图片时，在结果页发起流式识别
  useEffect(() => {
    if (initialText || !imageUri || scanId) return;

    setStreaming(true);

    const handlers: AnalyzeStreamHandlers = {
      onText: (fullText) => {
        setText(fullText);
      },
      onError: (error) => {
        setStreaming(false);
        const anyErr = error as any;
        if (anyErr?.code === "DAILY_SCAN_QUOTA_EXCEEDED") {
          Alert.alert(t("result.dailyQuotaExceededTitle"), t("result.dailyQuotaExceededText"));
          return;
        }
        Alert.alert(
          t("result.recognizeFailedTitle"),
          error.message || t("camera.unknownError"),
        );
      },
      onDone: (id) => {
        setStreaming(false);
        if (id) {
          setScanId(id);
        }
      },
    };

    let cleanup: (() => void) | undefined;

    analyzeImageStream(imageUri, handlers, { authToken: params.authToken ?? null })
      .then((stop) => {
        cleanup = stop;
      })
      .catch((error) => {
        setStreaming(false);
        Alert.alert(
          t("result.recognizeFailedTitle"),
          error instanceof Error ? error.message : t("camera.unknownError"),
        );
      });

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, [initialText, imageUri]);

  // 后台完整音频下载完成后，若当前正在播流式，自动切到本地文件以显示总时长并保持进度
  useEffect(() => {
    if (!downloadedAudioUri || !isPlayingStreamRef.current) return;
    const currentTime = status?.currentTime ?? 0;
    const wasPlaying = status?.playing ?? false;
    isPlayingStreamRef.current = false;
    setStreamLoading(false);
    player.replace(downloadedAudioUri);
    player.seekTo(currentTime);
    if (wasPlaying) player.play();
  }, [downloadedAudioUri]);

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
      activateLockScreen();
      player.play();
      return;
    }

    // 如果已经在后台预下载完成，则优先使用本地完整音频
    if (downloadedAudioUri) {
      isPlayingStreamRef.current = false;
      setRequestingSpeech(true);
      try {
        await setAudioModeAsync({
          playsInSilentMode: true,
          shouldPlayInBackground: true,
        });

        activateLockScreen();
        player.replace(downloadedAudioUri);
        player.play();
      } catch (error) {
        Alert.alert(
          t("result.playFailedTitle"),
          error instanceof Error ? error.message : t("camera.unknownError"),
        );
      } finally {
        setRequestingSpeech(false);
      }
      return;
    }

    // 首次点击：使用 /tts 的流式 URL，边生成边播放
    setRequestingSpeech(true);
    setStreamLoading(true);
    try {
      await setAudioModeAsync({
        playsInSilentMode: true,
        shouldPlayInBackground: true,
      });

      const url = getTtsStreamUrl(text);
      player.replace(url);
      activateLockScreen();
      player.play();
      isPlayingStreamRef.current = true;
    } catch (error) {
      setStreamLoading(false);
      Alert.alert(
        t("result.playFailedTitle"),
        error instanceof Error ? error.message : t("camera.unknownError"),
      );
    } finally {
      setRequestingSpeech(false);
    }

    // 并行在后台预下载完整音频，下载完成后会自动切到本地以显示总时长
    if (!preloadingSpeech && !downloadedAudioUri) {
      setPreloadingSpeech(true);
      createSpeech(text, { scanId: scanId || undefined })
        .then(async (speech) => {
          const preloadFile = new File(Paths.cache, `tts-preload-${Date.now()}.mp3`);
          await preloadFile.write(speech.audio_base64, { encoding: "base64" });
          setDownloadedAudioUri(preloadFile.uri);
        })
        .catch((e) => {
          console.warn("TTS preload failed", e);
        })
        .finally(() => {
          setPreloadingSpeech(false);
        });
    }
  };

  const onAddToCollection = async () => {
    if (!text) return;

    // 未登录时先引导登录（当前使用 Apple 登录，token 保存在 AsyncStorage）
    const authToken = await AsyncStorage.getItem("museum_auth_token");
    if (!authToken) {
      Alert.alert(t("result.needLoginTitle"), t("result.needLoginText"), [
        { text: t("result.cancel"), style: "cancel" },
        {
          text: t("result.goSignIn"),
          onPress: () => {
            // 跳转到收藏页，在顶部使用 Apple 登录
            router.push("/collection");
          },
        },
      ]);
      return;
    }

    setSaving(true);
    try {
      if (!scanId) {
        Alert.alert(t("result.notReadyTitle"), t("result.notReadyText"));
        return;
      }

      if (!isFavorite) {
        await favoriteScanRecord(scanId, authToken);
        setIsFavorite(true);
        setShowCollectedToast(true);
        setTimeout(() => {
          setShowCollectedToast(false);
        }, 1500);
      } else {
        await unfavoriteScanRecord(scanId, authToken);
        setIsFavorite(false);
      }
    } catch (error) {
      Alert.alert(
        isFavorite ? t("result.unfavoriteFailed") : t("result.favoriteFailed"),
        error instanceof Error ? error.message : t("camera.unknownError"),
      );
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
  const hasDuration = Number.isFinite(duration) && duration > 0;
  const isTextReady = !!text && !streaming;
  const isAudioFullyReady = !!downloadedAudioUri;
  const playButtonDisabled = !isTextReady || requestingSpeech || streamLoading;
  const sideControlsDisabled = !isAudioFullyReady || requestingSpeech;
  const progressInteractable = isAudioFullyReady;

  const formatTime = (value: number) => {
    if (!Number.isFinite(value) || value <= 0) return "0:00";
    const total = Math.floor(value);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  // 锁屏/控制中心「正在播放」：开始播放时激活，离开页面时清除
  const lockScreenMetadata = useMemo(
    () => ({
      title: t("result.lockscreenTitle"),
      artist: t("result.lockscreenArtist"),
      ...(imageUri ? { artworkUrl: imageUri } : {}),
    }),
    [imageUri, t]
  );
  const lockScreenOptions = { showSeekBackward: true, showSeekForward: true };

  useEffect(() => {
    return () => {
      try {
        player.setActiveForLockScreen(false);
      } catch (_) {}
    };
  }, [player]);

  const activateLockScreen = () => {
    try {
      player.setActiveForLockScreen(true, lockScreenMetadata, lockScreenOptions);
    } catch (e) {
      console.warn("setActiveForLockScreen failed", e);
    }
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
            <Text style={styles.iconText}>{isFavorite ? "★" : "☆"}</Text>
          </Pressable>
        </View>
      </View>

      {/* Details & description */}
      <View style={styles.detailsSection}>
        <View style={styles.textCard}>
          <Text style={styles.title} numberOfLines={2}>
            {t("result.title")}
          </Text>
          <Text style={styles.subtitle} numberOfLines={2}>
            {streaming ? t("result.subtitleStreaming") : t("result.subtitleDone")}
          </Text>

          <ScrollView
            style={styles.descriptionScroll}
            contentContainerStyle={styles.descriptionContent}
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.body}>
              {text || (streaming ? t("result.bodyStreaming") : t("result.bodyEmpty"))}
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
              onStartShouldSetResponder={() => progressInteractable}
              onMoveShouldSetResponder={() => progressInteractable}
              onResponderGrant={(e) => {
                if (progressInteractable) {
                  handleSeekBarPosition(e.nativeEvent.locationX);
                }
              }}
              onResponderMove={(e) => {
                if (progressInteractable) {
                  handleSeekBarPosition(e.nativeEvent.locationX);
                }
              }}
              onResponderRelease={(e) => {
                if (progressInteractable) {
                  handleSeekBarPosition(e.nativeEvent.locationX);
                }
              }}
            >
              <View
                style={[
                  styles.progressFill,
                  { width: `${progress * 100}%` },
                ]}
              />
            </View>
            {hasDuration ? (
              <Text style={styles.timeText}>{formatTime(duration)}</Text>
            ) : (
              <ActivityIndicator size="small" color="#F6E7D7" />
            )}
          </View>

          <View style={styles.controlsRow}>
            <View style={styles.sideControlsLeft}>
              <Pressable
                style={[
                  styles.smallControl,
                  sideControlsDisabled && styles.controlDisabled,
                ]}
                disabled={sideControlsDisabled}
                onPress={() => handleSeek(-15)}
              >
                <Back15Icon width={30} height={30} />
              </Pressable>
            </View>

            <Pressable
              style={[
                styles.playButton,
                playButtonDisabled && styles.controlDisabled,
              ]}
              onPress={onPlayTTS}
              disabled={playButtonDisabled}
            >
              {requestingSpeech || streamLoading ? (
                <ActivityIndicator size="small" color="#E2461B" />
              ) : status?.playing ? (
                <PauseCircleIcon width={32} height={32} />
              ) : (
                <PlayCircleIcon width={32} height={32} />
              )}
            </Pressable>

            <View style={styles.sideControlsRight}>
              <Pressable
                style={[
                  styles.smallControl,
                  sideControlsDisabled && styles.controlDisabled,
                ]}
                disabled={sideControlsDisabled}
                onPress={() => handleSeek(30)}
              >
                <Forward30Icon width={30} height={30} />
              </Pressable>

              <Pressable
                style={[
                  styles.speedBadge,
                  sideControlsDisabled && styles.controlDisabled,
                ]}
                disabled={sideControlsDisabled}
                onPress={toggleSpeed}
              >
                <Speed2Icon width={29} height={29} />
              </Pressable>
            </View>
          </View>
        </View>
      </View>

      {showCollectedToast && (
        <View style={styles.toastOverlay}>
          <View style={styles.toastContent}>
            <Text style={styles.toastText}>{t("result.collectedToast")}</Text>
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
  controlDisabled: {
    opacity: 0.4,
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
