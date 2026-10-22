import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ChoiceAnswerState, ChoiceRendererSpec } from '@/src/features/session/renderers/types';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The choice surface. It owns the tap affordance and nothing else: it reports which index the
// child selected and never interprets, reorders, relabels or judges the strings it renders.
//
// `spec.choices` is rendered in the exact order the server sent. No sort, no shuffle. The server
// sorts lexicographically, so a child may legitimately see 10, 3, 9 — a backend issue tracked
// separately, not something to paper over here.
//
// The reported state is an index into `spec.choices`, never the string itself. That is what makes
// an answer the server did not present structurally inexpressible by this surface.

type ChoiceGridProps = {
  spec: ChoiceRendererSpec;
  state: ChoiceAnswerState;
  disabled?: boolean;
  onChange: (next: ChoiceAnswerState) => void;
};

export function ChoiceGrid({ disabled = false, onChange, spec, state }: ChoiceGridProps) {
  return (
    <View style={styles.grid}>
      {spec.choices.map((choice, index) => {
        const selected = state.chosenIndex === index;
        return (
          <Pressable
            accessibilityLabel={choice}
            accessibilityRole="button"
            accessibilityState={{ disabled, selected }}
            disabled={disabled}
            // The index is the identity here; two choices could legitimately carry the same
            // string, so the key is position-based on purpose.
            key={`${index}-${choice}`}
            onPress={() => onChange({ kind: 'choice', chosenIndex: index })}
            style={({ pressed }) => [
              styles.choice,
              selected && styles.choiceSelected,
              disabled && styles.choiceDisabled,
              pressed && !disabled && styles.pressed,
            ]}>
            <AppText
              align="center"
              numberOfLines={2}
              style={[styles.choiceText, selected && styles.choiceTextSelected]}>
              {choice}
            </AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  choice: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderBottomColor: colors.borderStrong,
    borderBottomWidth: 3,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    flexGrow: 1,
    flexShrink: 1,
    justifyContent: 'center',
    minHeight: 68,
    minWidth: '44%',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.smPlus,
  },
  choiceDisabled: { opacity: 0.55 },
  choiceSelected: {
    backgroundColor: colors.primarySoft,
    borderBottomColor: colors.primaryShadow,
    borderColor: colors.primary,
  },
  choiceText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
    lineHeight: typography.lineHeight.lg,
  },
  choiceTextSelected: { color: colors.primaryShadow },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.smPlus,
  },
  pressed: { opacity: 0.72 },
});
