// The shared boolean YES/NO control for any archetype's `boolean-control`-kind extra field.
// Extracted 2026-08-26 -- before this, `ordered-value-sequence-surface.tsx` and
// `value-report-surface.tsx` each defined their own version, and the two had drifted: 10a's was a
// single switch that flips between "YES" and "NO" text, defaulting to showing "NO" before the
// child had touched it at all -- which reads as an answer already given, not an open question,
// even though the surrounding SUBMIT-disabled logic correctly still treated the field as unset.
// 10b's version (two independent buttons, neither selected until `onChange` fires once) fixes
// that: `isYes`/`isNo` are both false until the child actually picks one, so the control's visual
// state never claims an answer that was not given. This file is that fixed version, promoted to
// `primitives/` so no third archetype reproduces either shape independently -- matching
// `digit-keypad.tsx`'s own precedent as a shared, callback-only control with no archetype-specific
// type in its props.
//
// Takes only a field key (for accessibility labels) and value/onChange callbacks -- no dependency
// on any single archetype's extra-field type, so any future archetype's boolean-control key can
// use this directly without a new local reproduction.

import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { HIT_SLOP } from '@/src/features/c-session/motor-constants';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

export type BooleanToggleProps = {
  fieldKey: string;
  value: unknown;
  onChange: (value: boolean) => void;
};

export function BooleanToggle({ fieldKey, onChange, value }: BooleanToggleProps) {
  const isYes = value === true;
  const isNo = value === false;
  return (
    <View style={styles.booleanRow}>
      <Pressable
        accessibilityLabel={`${fieldKey} yes`}
        accessibilityRole="button"
        accessibilityState={{ selected: isYes }}
        hitSlop={HIT_SLOP}
        onPress={() => onChange(true)}
        style={[styles.toggle, styles.booleanChoice, isYes && styles.toggleOn]}>
        <AppText style={styles.toggleText}>YES</AppText>
      </Pressable>
      <Pressable
        accessibilityLabel={`${fieldKey} no`}
        accessibilityRole="button"
        accessibilityState={{ selected: isNo }}
        hitSlop={HIT_SLOP}
        onPress={() => onChange(false)}
        style={[styles.toggle, styles.booleanChoice, isNo && styles.toggleOn]}>
        <AppText style={styles.toggleText}>NO</AppText>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  booleanChoice: { flex: 1 },
  booleanRow: {
    flexDirection: 'row',
    gap: spacing.smPlus,
  },
  toggle: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: spacing.md,
  },
  toggleOn: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  toggleText: {
    fontFamily: typography.fonts.bold,
  },
});
