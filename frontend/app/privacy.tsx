import { useRouter } from "expo-router";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

const TITLE = "Privacy Policy";

const BODY = `
Last updated: March 2025

Artiou ("we", "our", or "the app") is a museum guide application that helps you discover and save information about artworks. This Privacy Policy explains how we collect, use, and protect your information when you use Artiou.

1. Information We Collect

1.1 Information you provide
• Account: When you sign in with Apple, we receive a unique identifier from Apple. We do not receive your Apple email or name unless you choose to share them, and we do not store them beyond what is needed to provide your account.
• Favorites: If you are logged in, we may store your saved artworks (images, descriptions, and audio) in association with your account so you can access them across devices.

1.2 Information collected automatically
• Photos: When you take or select a photo of an exhibit, that image is sent to our servers to generate an AI-generated description and audio guide. We do not use these images for advertising or to identify you personally beyond providing the service.
• Usage: We may collect anonymous usage data (e.g., feature usage, errors) to improve the app. We do not sell this data.

1.3 Device and permissions
• Camera: Used only to capture photos of artworks for recognition and analysis.
• Storage: Used to save your collection and cached audio on your device.
• Microphone: Not used for voice recognition; the app only plays audio guides.

2. How We Use Your Information

We use the information we collect to:
• Provide artwork recognition and AI-generated descriptions and audio guides.
• Save and sync your collection when you are logged in.
• Operate, secure, and improve the app and our services.
• Comply with applicable law and protect our rights.

We do not sell your personal information. We do not use your photos or data to train third-party AI models for purposes unrelated to providing the service to you.

3. Data Sharing and Third Parties

• Service providers: We use trusted providers (e.g., cloud hosting, AI and voice services) to run the app. They process data only on our instructions and in line with this policy.
• Apple: Sign in with Apple is subject to Apple’s privacy policy. We only receive the identifier and optional contact info you approve.
• Legal: We may disclose information if required by law or to protect our users, staff, or the public.

4. Data Retention and Security

• We retain your data only as long as needed to provide the service and as required by law.
• We use industry-standard measures to protect your data in transit and at rest. No system is completely secure; we encourage you to use a strong Apple account and keep your device secure.

5. Your Rights and Choices

• Access and deletion: You can request access to or deletion of your data by contacting us (see below). If you delete your account or the app, we will delete or anonymize your personal data in line with our retention policy.
• Sign out: You can sign out from your account in the app; we will stop associating new activity with your account.
• Withdraw consent: Where we rely on your consent, you may withdraw it at any time without affecting the lawfulness of processing before withdrawal.

6. Children

Artiou is not directed at children under 13. We do not knowingly collect personal information from children under 13. If you believe we have collected such information, please contact us and we will delete it.

7. International Use

Your data may be processed in the country where our servers or service providers are located. By using Artiou, you consent to such transfer and processing in accordance with this policy.

8. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes by posting the new policy in the app or by other reasonable means. Your continued use of Artiou after changes take effect means you accept the updated policy.

9. Contact Us

If you have questions about this Privacy Policy or your data, please contact us at:
Email: privacy@example.com
(Replace with your actual contact email or support URL.)
`.trim();

export default function PrivacyScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backText}>← Back</Text>
        </Pressable>
        <Text style={styles.title}>{TITLE}</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={true}
      >
        <Text style={styles.body}>{BODY}</Text>
      </ScrollView>
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
    paddingTop: 56,
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
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  body: {
    fontSize: 14,
    lineHeight: 22,
    color: "#4B3621",
  },
});
