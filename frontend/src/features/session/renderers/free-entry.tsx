import { StyleSheet, TextInput, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type {
  FreeEntryAnswerState,
  FreeEntryRendererSpec,
} from '@/src/features/session/renderers/types';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The free-entry surface (expanded_form only, reached solely because the registry resolved that
// format — never as a fallback for a format it could not resolve).
//
// It reports the raw input exactly as typed. It does not trim as you type, strip characters,
// uppercase, collapse spaces, or reject anything: `encodeSubmittedValue` trims once at submit and
// the server owns normalization and correctness. Keeping the field untouched while typing means a
// child never sees their own input rewritten under them mid-keystroke.
//
// `keyboardType` is left at the platform default. expanded_form answers contain digits, spaces and
// "+", which a numeric-only keypad cannot type.

type FreeEntryProps = {
  spec: FreeEntryRendererSpec;
  state: FreeEntryAnswerState;
  disabled?: boolean;
  onChange: (next: FreeEntryAnswerState) => void;
};

export function FreeEntry({ disabled = false, onChange, state }: FreeEntryProps) {
  return (
    <View style={styles.wrapper}>
      <AppText style={styles.label}>Type your answer</AppText>
      <TextInput
        accessibilityLabel="Your answer"
        autoCapitalize="none"
        autoCorrect={false}
        editable={!disabled}
        onChangeText={(rawInput) => onChange({ kind: 'free-entry', rawInput })}
        placeholder="Your answer"
        placeholderTextColor={colors.textMuted}
        style={[styles.input, disabled && styles.inputDisabled]}
        value={state.rawInput}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  input: {
    backgroundColor: colors.inputBackground,
    borderBottomColor: colors.borderStrong,
    borderBottomWidth: 3,
    borderColor: colors.inputBorder,
    borderRadius: radius.md,
    borderWidth: 2,
    color: colors.textPrimary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
    minHeight: 68,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.smPlus,
  },
  inputDisabled: { opacity: 0.55 },
  label: {
    color: colors.textSecondary,
    fontSize: typography.fontSize.sm,
    lineHeight: typography.lineHeight.sm,
  },
  wrapper: { gap: spacing.sm },
});
