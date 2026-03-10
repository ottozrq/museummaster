import AsyncStorage from "@react-native-async-storage/async-storage";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  FlatList,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";

import { API_BASE_URL, ScanRecord, fetchMyFavorites } from "../src/services/api";

export default function CollectionScreen() {
  const router = useRouter();
  const [items, setItems] = useState<ScanRecord[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [appleAvailable, setAppleAvailable] = useState(false);

  useEffect(() => {
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

  const handleAppleSignIn = async () => {
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });

      if (!credential.identityToken) {
        Alert.alert("登录失败", "未能获取 Apple 身份凭证");
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
        Alert.alert("登录失败", errText || `状态码 ${response.status}`);
        return;
      }

      const data = await response.json();
      if (!data?.access_token) {
        Alert.alert("登录失败", "服务器未返回访问令牌");
        return;
      }

      await AsyncStorage.setItem("museum_auth_token", data.access_token);
      setAuthToken(data.access_token);
    } catch (e: any) {
      if (e?.code === "ERR_CANCELED") {
        return;
      }
      Alert.alert("登录失败", e instanceof Error ? e.message : "未知错误");
    }
  };

  const handleSignOut = async () => {
    await AsyncStorage.removeItem("museum_auth_token");
    setAuthToken(null);
  };

  useFocusEffect(
    useCallback(() => {
      load(authToken);
    }, [authToken, load]),
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
              <Text style={styles.scanText}>SCAN</Text>
            </View>
          </Pressable>
        </View>

        {/* 中间 Apple 登录按钮与文案 */}
        <View style={styles.loginCenter}>
          <Text style={styles.loginTitle}>Save your favorite pieces</Text>
          <Text style={styles.loginSubtitle}>
            Sign in to keep your art journey across visits and devices.
          </Text>

          <AppleAuthentication.AppleAuthenticationButton
            buttonType={AppleAuthentication.AppleAuthenticationButtonType.SIGN_IN}
            buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
            cornerRadius={10}
            style={styles.loginAppleButton}
            onPress={handleAppleSignIn}
          />
        </View>

        {/* 底部条款 */}
        <View style={styles.loginBottom}>
          <Text style={styles.loginLegalText}>
            By entering, you agree to our{" "}
            <Text
              style={styles.loginLegalLink}
              onPress={() => router.push("/privacy")}
            >
              privacy policy
            </Text>
            {" & "}
            <Text
              style={styles.loginLegalLink}
              onPress={() => router.push("/terms")}
            >
              terms of service
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
            <Text style={styles.scanText}>SCAN</Text>
          </View>
        </Pressable>
      </View>

      {!checkingAuth && appleAvailable && authToken && (
        <View style={styles.authSection}>
          <View style={styles.authRow}>
            <Text style={styles.authText}>已使用 Apple 登录</Text>
            <Pressable style={styles.authAction} onPress={handleSignOut}>
              <Text style={styles.authActionText}>退出</Text>
            </Pressable>
          </View>
        </View>
      )}

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
  authActionText: {
    fontSize: 13,
    color: "#E2461B",
    fontWeight: "700",
  },
});
