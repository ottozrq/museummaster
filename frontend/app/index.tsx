import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type { GestureResponderEvent } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import LottieView from "lottie-react-native";

import { analyzeImage } from "../src/services/api";
import { useI18n } from "../src/i18n";

export default function CameraScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [permission, requestPermission] = useCameraPermissions();
  const [loading, setLoading] = useState(false);
  const [zoom, setZoom] = useState(0);
  const [splashState, setSplashState] = useState<"checking" | "show" | "done">("checking");
  const [showSplash, setShowSplash] = useState(false);
  const permissionRequestedRef = useRef(false);
  const cameraRef = useRef<CameraView>(null);
  const pinchRef = useRef<{ baseDistance: number; baseZoom: number } | null>(null);
  const splashStartedAtRef = useRef<number | null>(null);

  const SPLASH_KEY = "mm_has_seen_splash_v2";

  const getPinchDistance = (touches: { pageX: number; pageY: number }[]) => {
    if (touches.length < 2) return 0;
    const [a, b] = touches;
    return Math.hypot(b.pageX - a.pageX, b.pageY - a.pageY);
  };

  const PINCH_SENSITIVITY = 0.002; // 手指距离变化量 -> zoom 变化

  const handlePinchGrant = (e: GestureResponderEvent) => {
    const touches = Array.from(e.nativeEvent.touches);
    if (touches.length >= 2) {
      const baseDistance = getPinchDistance(touches);
      setZoom((prev) => {
        pinchRef.current = { baseDistance, baseZoom: prev };
        return prev;
      });
    }
  };

  const handlePinchMove = (e: GestureResponderEvent) => {
    if (!pinchRef.current) return;
    const touches = e.nativeEvent.touches;
    if (touches.length < 2) return;
    const currentDistance = getPinchDistance(Array.from(touches));
    const { baseDistance, baseZoom } = pinchRef.current;
    const delta = (currentDistance - baseDistance) * PINCH_SENSITIVITY;
    setZoom((prev) => {
      const next = baseZoom + delta;
      if (next < 0) return 0;
      if (next > 1) return 1;
      return next;
    });
  };

  const handlePinchEnd = () => {
    pinchRef.current = null;
  };

  useEffect(() => {
    // 等开机动画结束后再请求相机权限，避免“启动即弹窗”破坏开机体验
    if (splashState !== "done") return;
    if (permissionRequestedRef.current) return;
    if (permission?.granted) return;
    permissionRequestedRef.current = true;
    requestPermission();
  }, [permission?.granted, requestPermission, splashState]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const seen = await AsyncStorage.getItem(SPLASH_KEY);
        if (cancelled) return;
        if (seen) {
          setSplashState("done");
          setShowSplash(false);
        } else {
          setSplashState("show");
          setShowSplash(true);
          splashStartedAtRef.current = Date.now();
        }
      } catch {
        if (!cancelled) {
          setSplashState("show");
          setShowSplash(true);
          splashStartedAtRef.current = Date.now();
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const finishSplash = async () => {
    setSplashState("done");
    setShowSplash(false);
    try {
      await AsyncStorage.setItem(SPLASH_KEY, "1");
    } catch {
      // ignore
    }
  };

  // 保留：4 秒后自动关闭开机动画（只在 showSplash=true 时触发）
  useEffect(() => {
    if (!showSplash) return;
    const timer = setTimeout(() => setShowSplash(false), 4000);
    return () => clearTimeout(timer);
  }, [showSplash]);

  // showSplash 被关掉后，若本次属于首次展示，则落盘标记，确保以后永不再显示
  useEffect(() => {
    if (splashState !== "show") return;
    if (showSplash) return;
    void finishSplash();
  }, [showSplash, splashState]);

  // 避免二次启动闪一下 splash 底色：先等 AsyncStorage 判断完
  if (splashState === "checking") {
    return <View style={styles.preloadContainer} />;
  }

  if (splashState === "show" && showSplash) {
    return (
      <View style={styles.splashContainer}>
        <LottieView
          source={require("../assets/animation01.json")}
          autoPlay
          loop={false}
          onAnimationFinish={() => {
            const startedAt = splashStartedAtRef.current;
            if (startedAt && Date.now() - startedAt < 500) return;
            setShowSplash(false);
          }}
          resizeMode="contain"
          style={styles.splashAnimation}
        />
      </View>
    );
  }

  const analyzeAndNavigate = async (uri: string) => {
    // 现在由结果页自己发起流式识别，这里只负责导航并传递图片
    try {
      router.push({
        pathname: "/result",
        params: {
          imageUri: uri,
        },
      });
    } catch (error) {
      Alert.alert(
        t("camera.analyzeFailedTitle"),
        error instanceof Error ? error.message : t("camera.unknownError"),
      );
    }
  };

  const handleTakePhoto = async () => {
    if (!cameraRef.current) return;

    const photo = await cameraRef.current.takePictureAsync({
      quality: 0.8,
    });

    if (!photo?.uri) return;
    await analyzeAndNavigate(photo.uri);
  };

  const handlePickFromGallery = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(t("camera.needPhotoLibraryTitle"), t("camera.needPhotoLibraryText"));
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      allowsEditing: true,
      quality: 0.8,
    });

    if (result.canceled || !result.assets?.[0]?.uri) return;
    await analyzeAndNavigate(result.assets[0].uri);
  };

  if (!permission) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#E2461B" />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionTitle}>{t("camera.permissionTitle")}</Text>
        <Text style={styles.permissionText}>
          {t("camera.permissionText")}
        </Text>
        <Pressable style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.permissionButtonText}>{t("camera.enableCamera")}</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Camera with pinch-to-zoom */}
      <View
        style={StyleSheet.absoluteFill}
        onStartShouldSetResponder={() => false}
        onMoveShouldSetResponder={(e) => e.nativeEvent.touches.length === 2}
        onResponderGrant={handlePinchGrant}
        onResponderMove={handlePinchMove}
        onResponderRelease={handlePinchEnd}
        onResponderTerminate={handlePinchEnd}
      >
        <CameraView
          ref={cameraRef}
          style={styles.camera}
          facing="back"
          zoom={zoom}
        />
      </View>

      {/* Top hint text */}
      <View style={styles.topSection}>
        <Text style={styles.topHint}>{t("camera.topHint")}</Text>
      </View>

      {/* Focus frame */}
      <View style={styles.focusGuide}>
        <View style={styles.focusBox}>
          <View style={[styles.corner, styles.topLeft]} />
          <View style={[styles.corner, styles.topRight]} />
          <View style={[styles.corner, styles.bottomLeft]} />
          <View style={[styles.corner, styles.bottomRight]} />
        </View>
      </View>

      {/* Bottom controls: gallery / big scan button / artiou */}
      <View style={styles.bottomSection}>
        <View style={styles.bottomButtonsRow}>
          <Pressable
            style={styles.pillButton}
            onPress={handlePickFromGallery}
            disabled={loading}
          >
            <Text style={styles.pillButtonText}>{t("camera.gallery").toUpperCase()}</Text>
          </Pressable>

          <Pressable
            style={styles.captureButton}
            onPress={handleTakePhoto}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <View style={styles.captureInner} />
            )}
          </Pressable>

          <Pressable
            style={styles.pillButton}
            onPress={() => router.push("/collection")}
            disabled={loading}
          >
            <Text style={styles.pillButtonText}>{t("camera.artiou").toUpperCase()}</Text>
          </Pressable>
        </View>

        <Text style={styles.bottomHint}>
          {loading ? t("camera.recognizing") : t("camera.takeOrChoose")}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  preloadContainer: {
    flex: 1,
    backgroundColor: "#000",
  },
  splashContainer: {
    flex: 1,
    backgroundColor: "#E2461B",
    justifyContent: "center",
    alignItems: "center",
  },
  splashAnimation: {
    width: "80%",
    aspectRatio: 1224 / 1424,
  },
  splashText: {
    fontSize: 40,
    fontWeight: "800",
    letterSpacing: 4,
    color: "#E2461B",
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: "#000",
    justifyContent: "center",
    alignItems: "center",
  },
  permissionContainer: {
    flex: 1,
    backgroundColor: "#000",
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  permissionTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#E2461B",
    marginBottom: 12,
    textAlign: "center",
  },
  permissionText: {
    fontSize: 16,
    color: "#B07557",
    textAlign: "center",
    marginBottom: 24,
  },
  permissionButton: {
    paddingHorizontal: 32,
    paddingVertical: 12,
    borderRadius: 26,
    borderWidth: 2,
    borderColor: "#E2461B",
  },
  permissionButtonText: {
    color: "#E2461B",
    fontSize: 16,
    fontWeight: "700",
  },
  topSection: {
    position: "absolute",
    top: 60,
    left: 0,
    right: 0,
    alignItems: "center",
    paddingHorizontal: 32,
  },
  topHint: {
    textAlign: "center",
    color: "#fff",
    fontSize: 14,
  },
  camera: {
    ...StyleSheet.absoluteFillObject,
  },
  focusGuide: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  focusBox: {
    width: "70%",
    aspectRatio: 1, // 正方形取景框
  },
  corner: {
    position: "absolute",
    width: 32,
    height: 32,
    borderColor: "#E2461B",
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 3,
    borderRightWidth: 3,
  },
  bottomSection: {
    position: "absolute",
    bottom: 40,
    left: 0,
    right: 0,
    paddingHorizontal: 32,
    alignItems: "center",
  },
  bottomButtonsRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
  },
  pillButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 999,
    borderWidth: 2,
    borderColor: "#E2461B",
    minWidth: 120,
    alignItems: "center",
    justifyContent: "center",
  },
  pillButtonText: {
    color: "#E2461B",
    fontSize: 14,
    fontWeight: "700",
  },
  captureButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: "#E2461B",
    alignItems: "center",
    justifyContent: "center",
  },
  captureInner: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#E2461B",
  },
  bottomHint: {
    marginTop: 16,
    fontSize: 13,
    color: "#E2461B",
  },
});
