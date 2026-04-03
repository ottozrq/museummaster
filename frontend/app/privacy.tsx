import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { WebView } from "react-native-webview";

import { getArtiouPrivacyPolicyUrl } from "../src/legal/policyUrls";
import { useI18n } from "../src/i18n";

export default function PrivacyScreen() {
  const router = useRouter();
  const { t, locale } = useI18n();
  const insets = useSafeAreaInsets();
  const uri = getArtiouPrivacyPolicyUrl(locale);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const openInBrowser = useCallback(() => {
    void Linking.openURL(uri);
  }, [uri]);

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>
      <View style={[styles.header, { paddingTop: Math.max(insets.top, 12) + 44 }]}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backText}>{t("legal.back")}</Text>
        </Pressable>
        <Text style={styles.title}>{t("legal.privacyTitle")}</Text>
      </View>

      {error ? (
        <View style={styles.centerBox}>
          <Text style={styles.errorText}>{t("legal.privacyLoadError")}</Text>
          <Pressable style={styles.externalBtn} onPress={openInBrowser}>
            <Text style={styles.externalBtnText}>{t("legal.openInBrowser")}</Text>
          </Pressable>
        </View>
      ) : Platform.OS === "web" ? (
        <View style={styles.centerBox}>
          <Text style={styles.errorText}>{t("legal.privacyWebHint")}</Text>
          <Pressable style={styles.externalBtn} onPress={openInBrowser}>
            <Text style={styles.externalBtnText}>{t("legal.openInBrowser")}</Text>
          </Pressable>
        </View>
      ) : (
        <View style={styles.webWrap}>
          {loading ? (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color="#E2461B" />
            </View>
          ) : null}
          <WebView
            source={{ uri }}
            style={styles.webview}
            onLoadStart={() => {
              setLoading(true);
              setError(false);
            }}
            onLoadEnd={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setError(true);
            }}
            onHttpError={() => {
              setLoading(false);
              setError(true);
            }}
            startInLoadingState
            setBuiltInZoomControls={false}
            showsVerticalScrollIndicator
          />
        </View>
      )}
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
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#E2461B",
  },
  backBtn: {
    marginRight: 12,
    paddingVertical: 8,
    paddingRight: 8,
  },
  backText: {
    fontSize: 16,
    color: "#E2461B",
    fontWeight: "700",
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#E2461B",
    flex: 1,
  },
  webWrap: {
    flex: 1,
    position: "relative",
  },
  webview: {
    flex: 1,
    backgroundColor: "#F6E7D7",
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(246, 231, 215, 0.85)",
    zIndex: 1,
  },
  centerBox: {
    flex: 1,
    padding: 24,
    justifyContent: "center",
    alignItems: "center",
    gap: 16,
  },
  errorText: {
    fontSize: 15,
    lineHeight: 22,
    color: "#4B3621",
    textAlign: "center",
  },
  externalBtn: {
    backgroundColor: "#E2461B",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 999,
  },
  externalBtnText: {
    color: "#FFFFFF",
    fontWeight: "800",
    fontSize: 15,
  },
});
