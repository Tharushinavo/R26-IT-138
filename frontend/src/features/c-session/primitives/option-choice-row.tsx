// The shared single-select choice row for `option-select` (10d), generalizing the shape
// `GenericExtraField`'s `exact-choice-control` branch already established in
// `ordered-value-sequence-surface.tsx` (10a) -- there it renders one EXTRA field alongside a
// different primary scene; here it IS the primary scene. Promoted to `primitives/` so neither call
// site (`C-MCL-02`'s `left|right|equal`, `C-MCL-03`'s `<|>|=`) reproduces its own copy, matching
// `boolean-toggle.tsx`'s own extraction precedent: a second consumer of a shape is a reason to
// generalize it, never a reason to fork it.
//
// Stateless and generic over `T extends string | number`: the caller owns `value`; this component
// only ever reports which option was pressed and renders whatever value it is given, matching
// `UnitStepper`'s own "holds no state of its own" doctrine. Reports back the ORIGINAL array element
// on selection (never a stringified label) so a caller submitting a `number` (a future numeral
// option, once approved -- see option-select-logic.ts's own header for why that path is refused
// this batch) round-trips as a `number`, and a caller submitting a pipe-string alternative
// round-trips as the exact `string` `isValidForKind`'s `exact-choice-control` check expects.
//
// Geometry is `TOKEN_TOUCH_TARGET_SIZE` / `TOKEN_SPACING` (motor-constants.ts) -- the same token
// family `value-report-surface.tsx`'s read-only payload tokens use -- never a bare literal, and
// never `GenericExtraField`'s own private `minHeight: 48` (that value predates motor-constants.ts's
// extraction and happens to equal `TOUCH_TARGET_MIN_SIZE`, but is not derived from it). The row
// wraps (`flexWrap`) rather than compressing an option to fit more of them on one line -- both real
// call sites today declare exactly three fixed alternatives at every difficulty level, so wrapping
// is never actually exercised against real data yet, but the property is real, not aspirational,
// the same status `ordered-value-sequence-surface.tsx`'s own `GenericExtraField` extra-field path
// had at 10a.

import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

export type OptionChoiceRowProps<T extends string | number> = {
  options: readonly T[];
  value: T | null;
  onSelect: (value: T) => void;
  disabled?: boolean;
};

export function OptionChoiceRow<T extends string | number>({
  disabled = false,
  onSelect,
  options,
  value,
}: OptionChoiceRowProps<T>) {
  return (
    <View style={styles.row}>
      {options.map((option) => {
        const selected = value === option;
        return (
          <Pressable
            accessibilityLabel={String(option)}
            accessibilityRole="button"
            accessibilityState={{ disabled, selected }}
            disabled={disabled}
            hitSlop={HIT_SLOP}
            key={String(option)}
            onPress={() => onSelect(option)}
            style={({ pressed }) => [
              styles.option,
              selected && styles.optionSelected,
              disabled && styles.optionDisabled,
              pressed && !disabled && styles.pressed,
            ]}>
            <AppText style={styles.optionText}>{String(option)}</AppText>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  option: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: TOKEN_TOUCH_TARGET_SIZE,
    minWidth: TOKEN_TOUCH_TARGET_SIZE,
    paddingHorizontal: spacing.md,
  },
  optionDisabled: { opacity: 0.5 },
  optionSelected: {
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
  },
  optionText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  pressed: { opacity: 0.72 },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: TOKEN_SPACING,
    justifyContent: 'center',
  },
});
