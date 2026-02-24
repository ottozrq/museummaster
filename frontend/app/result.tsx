import AsyncStorage from "@react-native-async-storage/async-storage";
import { Audio } from "expo-av";
import * as FileSystem from "expo-file-system";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { Alert, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { createSpeech } from "../src/services/api";

type HistoryItem = {
  id: string;
  createdAt: string;
  imageUri?: string;
  text: string;
};

const HISTORY_KEY = "museum_guide_history";

async function appendHistory(item: HistoryItem) {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const list: HistoryItem[] = raw ? JSON.parse(raw) : [];
  list.unshift(item);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 30)));
}

export default function ResultScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ text?: string; imageUri?: string }>();
  const text = useMemo(() => params.text ?? "", [params.text]);
  const imageUri = useMemo(() => params.imageUri ?? "", [params.imageUri]);

  const [playing, setPlaying] = useState(false);

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

  const onSave = async () => {
    if (!text) return;

    const item: HistoryItem = {
      id: `${Date.now()}`,
      createdAt: new Date().toISOString(),
      imageUri,
      text,
    };

    await appendHistory(item);
    Alert.alert("已保存", "结果已加入历史记录");
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {imageUri ? <Image source={{ uri: imageUri }} style={styles.image} /> : null}

      <Text style={styles.heading}>识别结果</Text>
      <Text style={styles.body}>{text || "暂无结果"}</Text>

      <Pressable style={styles.primaryButton} onPress={onPlayTTS} disabled={playing || !text}>
        <Text style={styles.primaryButtonText}>{playing ? "生成中..." : "播放讲解"}</Text>
      </Pressable>

      <Pressable style={styles.secondaryButton} onPress={onSave}>
        <Text style={styles.secondaryButtonText}>保存到历史</Text>
      </Pressable>

      <Pressable style={styles.linkButton} onPress={() => router.push("/history")}>
        <Text style={styles.linkText}>去历史记录</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    gap: 12,
    backgroundColor: "#fff",
  },
  image: {
    width: "100%",
    height: 240,
    borderRadius: 12,
  },
  heading: {
    fontSize: 24,
    fontWeight: "700",
    color: "#102a43",
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    color: "#243b53",
  },
  primaryButton: {
    marginTop: 8,
    backgroundColor: "#0f766e",
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#fff",
    fontWeight: "600",
    fontSize: 16,
  },
  secondaryButton: {
    borderColor: "#0f766e",
    borderWidth: 1,
    paddingVertical: 12,
    borderRadius: 12,
    alignItems: "center",
  },
  secondaryButtonText: {
    color: "#0f766e",
    fontWeight: "600",
    fontSize: 15,
  },
  linkButton: {
    paddingVertical: 8,
    alignItems: "center",
  },
  linkText: {
    color: "#486581",
    textDecorationLine: "underline",
  },
});
