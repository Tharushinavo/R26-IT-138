import { Pressable, StyleSheet, View } from 'react-native';

import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import { colors, radius, spacing } from '@/src/theme/tokens';

/** Temporary Page 1 destination. The learner Home screen belongs to Page 2. */
export function AuthorizedPlaceholderScreen() {
  const palette = colors;
  const { me, profileName, signOut } = useAuth();
  const displayName = me?.learnerProfile?.name.trim() || profileName;

  return (
    <ScreenShell centered>
      <View style={styles.content}>
        <AppText align="center" variant="title">
          {displayName ? `Welcome back, ${displayName}` : 'Welcome back'}
        </AppText>
        <AppText align="center" style={{ color: palette.textSecondary }}>
          Your learner access has been verified.
        </AppText>
        <AppText align="center">
          This is a temporary Page 1 destination. The learner Home screen is the next approved page.
        </AppText>
        <Pressable
          accessibilityRole="button"
          onPress={() => void signOut()}
          style={[styles.button, { borderColor: palette.border }]}>
          <AppText>Sign out</AppText>
        </Pressable>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
  },
  content: { alignItems: 'center', gap: spacing.lg, maxWidth: 520 },
});
