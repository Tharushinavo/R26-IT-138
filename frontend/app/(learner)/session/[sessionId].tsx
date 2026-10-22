import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import { LiveSessionScreen } from '@/src/features/session/live-session-screen';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

/**
 * Thin route boundary. Its only job is to establish that an opaque session id actually arrived in
 * the route params; everything else belongs to LiveSessionScreen. A missing id is a navigation
 * fault rather than a session fault, so it is handled here instead of being passed down as an
 * empty string for the API layer to turn into a confusing 404.
 */
export default function LearningSessionDestinationRoute() {
  const { sessionId } = useLocalSearchParams<{ sessionId?: string }>();
  if (typeof sessionId === 'string' && sessionId.length > 0) {
    return <LiveSessionScreen sessionId={sessionId} />;
  }

  return (
    <ScreenShell centered>
      <View style={styles.content}>
        <View style={styles.iconCircle}><Ionicons color={colors.primary} name="book-outline" size={44} /></View>
        <AppText align="center" variant="title">Learning session</AppText>
        <AppText align="center" style={styles.message}>
          Return Home so MathMingo can prepare your session safely.
        </AppText>
        <Pressable accessibilityRole="button" onPress={() => router.replace('/(learner)/home')} style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
          <AppText style={styles.buttonText}>BACK TO HOME</AppText>
        </Pressable>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  button: { alignItems: 'center', alignSelf: 'stretch', backgroundColor: colors.surface1, borderBottomColor: colors.borderStrong, borderBottomWidth: 3, borderColor: colors.border, borderRadius: radius.md, borderWidth: 2, justifyContent: 'center', minHeight: 56, paddingHorizontal: spacing.lg },
  buttonText: { fontFamily: typography.fonts.bold, fontSize: 15, letterSpacing: typography.letterSpacing.button },
  content: { alignItems: 'center', gap: spacing.lg, maxWidth: 520, width: '100%' },
  iconCircle: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radius.xl, height: 88, justifyContent: 'center', width: 88 },
  message: { color: colors.textSecondary },
  pressed: { opacity: 0.72 },
});
