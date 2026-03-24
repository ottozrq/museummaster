import AsyncStorage from "@react-native-async-storage/async-storage";
import { useRouter } from "expo-router";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";
import * as AppleAuthentication from "expo-apple-authentication";
import { useState } from "react";

import { useI18n } from "../src/i18n";
import { deleteMyAccount } from "../src/services/api";

function getGoogleSignin() {
  try {
    return require("@react-native-google-signin/google-signin").GoogleSignin;
  } catch {
    return null;
  }
}

export default function SettingsScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [submitting, setSubmitting] = useState(false);

  const clearAuthAndBack = async () => {
    try {
      const googleSignin = getGoogleSignin();
      await googleSignin?.signOut?.();
    } catch {}
    try {
      await AppleAuthentication.signOutAsync();
    } catch {}
    await AsyncStorage.removeItem("museum_auth_token");
    router.replace("/collection");
  };

  const handleSignOut = async () => {
    if (submitting) return;
    await clearAuthAndBack();
  };

  const handleDeleteAccount = async () => {
    if (submitting) return;
    const token = await AsyncStorage.getItem("museum_auth_token");
    if (!token) {
      Alert.alert(t("settings.notLoggedInTitle"), t("settings.notLoggedInText"));
      return;
    }

    Alert.alert(
      t("settings.deleteConfirmTitle"),
      t("settings.deleteConfirmText"),
      [
        { text: t("settings.cancel"), style: "cancel" },
        {
          text: t("settings.confirmDelete"),
          style: "destructive",
          onPress: async () => {
            try {
              setSubmitting(true);
              await deleteMyAccount(token);
              await clearAuthAndBack();
              Alert.alert(t("settings.deleteSuccessTitle"), t("settings.deleteSuccessText"));
            } catch (e) {
              Alert.alert(
                t("settings.deleteFailedTitle"),
                e instanceof Error ? e.message : t("settings.unknownError"),
              );
            } finally {
              setSubmitting(false);
            }
          },
        },
      ],
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>{t("settings.title")}</Text>
      </View>

      <View style={styles.section}>
        <Pressable
          style={[styles.actionButton, submitting && styles.disabledButton]}
          onPress={handleSignOut}
          disabled={submitting}
        >
          <Text style={styles.actionText}>{t("settings.signOut")}</Text>
        </Pressable>

        <Pressable
          style={[styles.actionButton, styles.dangerButton, submitting && styles.disabledButton]}
          onPress={handleDeleteAccount}
          disabled={submitting}
        >
          <Text style={[styles.actionText, styles.dangerText]}>{t("settings.deleteAccount")}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F6E7D7",
    paddingHorizontal: 20,
    paddingTop: 80,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 34,
    fontWeight: "900",
    color: "#E2461B",
  },
  section: {
    gap: 12,
  },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#E2461B",
    backgroundColor: "#FFF5EC",
  },
  actionText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#E2461B",
    textAlign: "center",
  },
  dangerButton: {
    borderColor: "#B42318",
    backgroundColor: "#FFF1F1",
  },
  dangerText: {
    color: "#B42318",
  },
  disabledButton: {
    opacity: 0.55,
  },
});
