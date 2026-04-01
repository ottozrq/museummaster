import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, FlatList, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";

import { API_BASE_URL, ScanRecord, fetchMyFavorites } from "../src/services/api";
import { useI18n } from "../src/i18n";

const GOOGLE_IOS_CLIENT_ID =
  "577788424612-d3gutf0ru81i1tdrfdm5m21c27rvp27k.apps.googleusercontent.com";

function getGoogleSignin() {
  try {
    return require("@react-native-google-signin/google-signin").GoogleSignin;
  } catch {
    return null;
  }
}

export default function CollectionScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [items, setItems] = useState<ScanRecord[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [appleAvailable, setAppleAvailable] = useState(false);
  const [scanRemaining, setScanRemaining] = useState<number | null>(null);

  useEffect(() => {
    const googleSignin = getGoogleSignin();
    googleSignin?.configure?.({
      iosClientId: GOOGLE_IOS_CLIENT_ID,
    });

    let cancelled = false;
    (async () => {
      try {
        const [available, token] = await Promise.all([
          AppleAuthentication.isAvailableAsync(),
          AsyncStorage.getItem("museum_auth_token"),
        ]);
        if (cancelled) return;
        setAppleAvailable(available);
        setAuthToken(token);
      } catch {
        if (!cancelled) {
          setAppleAvailable(false);
        }
      } finally {
        if (!cancelled) {
          setCheckingAuth(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const load = useCallback(
    async (token: string | null) => {
      if (!token) {
        setItems([]);
        return;
      }
      try {
        const coll = await fetchMyFavorites(token, { pageToken: "1", pageSize: 100 });
        setItems(coll.items ?? []);
        console.log(coll);
      } catch (e) {
        console.warn("Fetch favorites failed", e);
      }
    },
    [],
  );

  const loadQuota = useCallback(async (token: string | null) => {
    if (!token) {
      setScanRemaining(null);
      return;
    }
    try {
      const resp = await fetch(`${API_BASE_URL}/scan-quota/remaining`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!resp.ok) {
        throw new Error(`Quota fetch failed (${resp.status})`);
      }
      const data = await resp.json();
      setScanRemaining(typeof data?.remaining === "number" ? data.remaining : null);
    } catch (e) {
      console.warn("Load quota failed", e);
      setScanRemaining(null);
    }
  }, []);

  const handleAppleSignIn = async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (!credential.identityToken) {
        Alert.alert(t("collection.loginFailedTitle"), t("collection.noAppleCredential"));
        return;
      }

      const firstName = credential.fullName?.givenName ?? "";
      const lastName = credential.fullName?.familyName ?? "";

      const response = await fetch(`${API_BASE_URL}/auth/apple`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          identity_token: credential.identityToken,
          first_name: firstName,
          last_name: lastName,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        Alert.alert(t("collection.loginFailedTitle"), errText || `状态码 ${response.status}`);
        return;
      }

      const data = await response.json();
      if (!data?.access_token) {
        Alert.alert(t("collection.loginFailedTitle"), t("collection.serverNoToken"));
        return;
      }

      await AsyncStorage.setItem("museum_auth_token", data.access_token);
      setAuthToken(data.access_token);
    } catch (e: any) {
      if (e?.code === "ERR_CANCELED") {
        return;
      }
      Alert.alert(t("collection.loginFailedTitle"), e instanceof Error ? e.message : t("camera.unknownError"));
    }
  };

  const handleGoogleSignIn = async () => {
    const googleSignin = getGoogleSignin();
    if (!googleSignin) {
      Alert.alert(t("collection.loginFailedTitle"), t("collection.googleUnavailable"));
      return;
    }

    try {
      const signInResult = await googleSignin.signIn();
      const idToken = (signInResult as any)?.data?.idToken ?? (signInResult as any)?.idToken;
      if (!idToken) {
        Alert.alert(t("collection.loginFailedTitle"), t("collection.noGoogleCredential"));
        return;
      }

      const response = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id_token: idToken,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        Alert.alert(t("collection.loginFailedTitle"), errText || `状态码 ${response.status}`);
        return;
      }

      const tokenResp = await response.json();
      if (!tokenResp?.access_token) {
        Alert.alert(t("collection.loginFailedTitle"), t("collection.serverNoToken"));
        return;
      }

      await AsyncStorage.setItem("museum_auth_token", tokenResp.access_token);
      setAuthToken(tokenResp.access_token);
    } catch (e: any) {
      if (e?.code === "SIGN_IN_CANCELLED") {
        return;
      }
      Alert.alert(t("collection.loginFailedTitle"), e instanceof Error ? e.message : t("camera.unknownError"));
    }
  };

  useFocusEffect(
    useCallback(() => {
      load(authToken);
      void loadQuota(authToken);
    }, [authToken, load, loadQuota]),
  );

  const sections = useMemo(() => {
    const byDate: Record<string, ScanRecord[]> = {};
    for (const item of items) {
      const d = new Date(item.inserted_at ?? Date.now());
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

  // 未登录状态：展示「My Artiou」登录引导页
  if (!checkingAuth && appleAvailable && !authToken) {
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
              <Text style={styles.scanText}>{t("collection.scan").toUpperCase()}</Text>
            </View>
          </Pressable>
        </View>

        {/* 中间 Apple 登录按钮与文案 */}
        <View style={styles.loginCenter}>
          <Text style={styles.loginTitle}>{t("collection.saveFavoritesTitle")}</Text>
          <Text style={styles.loginSubtitle}>
            {t("collection.saveFavoritesSubtitle")}
          </Text>

          <AppleAuthentication.AppleAuthenticationButton
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={10}
            style={styles.loginAppleButton}
            onPress={handleAppleSignIn}
          />

          <Pressable style={styles.loginGoogleButton} onPress={handleGoogleSignIn}>
            <View style={styles.loginGoogleContent}>
              <View style={styles.loginGoogleIconCircle}>
                <Text style={styles.loginGoogleIconG}>G</Text>
              </View>
              <Text style={styles.loginGoogleButtonText}>{t("collection.continueWithGoogle")}</Text>
            </View>
          </Pressable>
        </View>

        {/* 底部条款 */}
        <View style={styles.loginBottom}>
          <Text style={styles.loginLegalText}>
            {t("collection.legalPrefix")}{" "}
            <Text
              style={styles.loginLegalLink}
              onPress={() => router.push("/privacy")}
            >
              {t("collection.privacyPolicy")}
            </Text>
            {" "}{t("collection.and")}{" "}
            <Text
              style={styles.loginLegalLink}
              onPress={() => router.push("/terms")}
            >
              {t("collection.termsOfService")}
            </Text>
          </Text>
        </View>
      </View>
    );
  }

  // 已登录或 Apple 登录不可用：展示原有收藏列表
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
          <Text style={styles.scanText}>{t("collection.scan").toUpperCase()}</Text>
          </View>
        </Pressable>
      </View>

      {!checkingAuth && authToken && (
        <View style={styles.authSection}>
          <View style={styles.authRow}>
            <Text style={styles.authText}>
              {scanRemaining !== null
                ? t("collection.remainingScans", { count: scanRemaining })
                : t("collection.signedInWithApple")}
            </Text>
            <View style={styles.authActions}>
              <Pressable
                style={styles.authAction}
                onPress={() => router.push("/settings" as any)}
              >
                <Text style={styles.authActionText}>{t("collection.settings")}</Text>
              </Pressable>
              <Pressable style={styles.authAction} onPress={() => router.push("/subscription")}>
                <Text style={styles.authActionText}>{t("nav.subscription")}</Text>
              </Pressable>
            </View>
          </View>
        </View>
      )}

      <FlatList
        data={sections}
        keyExtractor={(section) => section.dateKey}
        contentContainerStyle={styles.content}
        ListEmptyComponent={<Text style={styles.empty}>{t("collection.empty")}</Text>}
        renderItem={({ item: section }) => (
          <View style={styles.section}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.thumbScrollContent}
            >
              {section.items.map((item, index) => (
                <Pressable
                  key={`${section.dateKey}-${item.scan_id ?? index}`}
                  style={styles.thumbWrapper}
                  onPress={() =>
                    router.push({
                      pathname: "/result",
                      params: {
                        scanId: item.scan_id,
                      },
                    })
                  }
                >
                  {item.image_path ? (
                    <Image
                      source={{ uri: `${API_BASE_URL}${item.image_path}` }}
                      style={styles.thumb}
                    />
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
    paddingTop: 52,
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
  // 未登录状态 UI
  loginCenter: {
    flex: 1,
    paddingHorizontal: 32,
    justifyContent: "center",
    alignItems: "center",
  },
  loginTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#E2461B",
    textAlign: "center",
    marginBottom: 8,
  },
  loginSubtitle: {
    fontSize: 14,
    color: "#B07557",
    textAlign: "center",
    marginBottom: 24,
  },
  loginAppleButton: {
    width: "80%",
    maxWidth: 320,
    height: 50,
    marginTop: 8,
  },
  loginGoogleButton: {
    width: "80%",
    maxWidth: 320,
    height: 48,
    marginTop: 12,
    borderRadius: 10,
    borderWidth: 1.2,
    borderColor: "#D0D0D0",
    backgroundColor: "#fff",
  },
  loginGoogleContent: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  loginGoogleIconCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "#fff",
    borderWidth: 1.2,
    borderColor: "#DB4437",
    alignItems: "center",
    justifyContent: "center",
  },
  loginGoogleIconG: {
    fontSize: 14,
    fontWeight: "800",
    color: "#DB4437",
  },
  loginGoogleButtonText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#3C4043",
  },
  loginBottom: {
    paddingHorizontal: 32,
    paddingBottom: 36,
    alignItems: "center",
    gap: 16,
  },
  loginLegalText: {
    fontSize: 13,
    color: "#7A5C3A",
    textAlign: "center",
  },
  loginLegalLink: {
    fontWeight: "700",
    textDecorationLine: "underline",
  },
  authSection: {
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  appleButton: {
    width: "100%",
    height: 44,
    marginBottom: 8,
  },
  authRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  authText: {
    fontSize: 14,
    color: "#B07557",
  },
  authAction: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E2461B",
  },
  authActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  authActionText: {
    fontSize: 13,
    color: "#E2461B",
    fontWeight: "700",
  },
});
