// The shared presentational primitive behind fail-closed-frame.tsx and technical-block-screen.tsx.
// Mirrors live-session-screen.tsx's inline "unrenderable"/"failure" block (Component B's own
// precedent for this exact situation), reusing ScreenShell/AppText/theme tokens rather than a
// parallel styling approach.
//
// Its prop type is the structural half of "carries no diagnostic distinction whatsoever": there is
// no `reason`, `cause`, or `kind` prop anywhere on this component, so no caller -- including
// technical-block-screen.tsx -- has a channel through which a 409's cause could reach what is
// rendered. `title` and `detail` are supplied as fixed literal strings by each caller, never
// derived from an error's message or envelope.
//
// No input surface of any kind is rendered here, ever. c-neutral-screens-no-input-surface.test.ts
// asserts this structurally by scanning this file's (and its two callers') source text for
// TextInput / an `editable` prop / any import from an archetypes or renderer module. That guard
// strips comments before matching (regex-shaped, not a real tokenizer) and its stated blind spots
// mirror the committed node-builtins guard: no constructed/dynamic import detection, and a string
// literal containing a literal "//" on the same line as real code could be mishandled. No file
// here does that.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

export type NeutralMessageScreenProps = {
  title: string;
  detail: string;
  supportCode: string | null;
  onExit: () => void;
  exitLabel?: string;
};

export function NeutralMessageScreen({
  detail,
  exitLabel = 'BACK TO HOME',
  onExit,
  supportCode,
  title,
}: NeutralMessageScreenProps) {
  return (
    <ScreenShell centered>
      <View style={styles.iconCircle}>
        <Ionicons color={colors.primary} name="alert-circle-outline" size={44} />
      </View>
      <AppText align="center" variant="title">
        {title}
      </AppText>
      <AppText align="center" style={styles.muted}>
        {detail}
      </AppText>
      {supportCode ? (
        <AppText align="center" style={styles.supportCode}>
          Support code: {supportCode}
        </AppText>
      ) : null}
      <Pressable
        accessibilityRole="button"
        onPress={onExit}
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
        <AppText style={styles.buttonText}>{exitLabel}</AppText>
      </Pressable>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    alignSelf: 'stretch',
    backgroundColor: colors.primary,
    borderColor: colors.surface1,
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 62,
    paddingHorizontal: spacing.lg,
  },
  buttonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 17,
    letterSpacing: typography.letterSpacing.button,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderRadius: radius.xl,
    height: 88,
    justifyContent: 'center',
    width: 88,
  },
  muted: { color: colors.textSecondary },
  pressed: { opacity: 0.85 },
  supportCode: { color: colors.textMuted, fontSize: typography.fontSize.xs },
});
