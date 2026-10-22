// The ruled entry control for `ordered-value-sequence`'s ordered-integer-collection blanks
// (10a-builder-prompt.md, "RULING -- THE ENTRY CONTROL IS A DIGIT KEYPAD, NOT A STEPPER").
//
// A per-slot +/- stepper was the original plan and was overruled: NP-01 at difficulty 4 and NP-02
// at difficulty 5 both ask for two-digit answers in the 60s-70s range, and a stepper from zero
// needs dozens of taps for those -- tap count would scale with the magnitude of the number, and
// magnitude rises with difficulty, so effort would track difficulty. That is the SPEC section 10
// confound touch-target SIZE constancy alone does not catch: a stepper keeps every size constant
// while making the interaction cost track difficulty regardless.
//
// This is not a free-text field (section 5.2 still holds, and this is explicitly not
// free-entry.tsx's TextInput): the child can only ever compose a value from a fixed, constant-size
// key set. Tap count then equals the number of digits typed, which is mathematical demand, not
// motor demand -- and digit count does not itself track difficulty level in this archetype's data,
// only the values being entered do, which is exactly the axis SPEC section 10 permits to vary.
//
// One shared keypad drives whichever entry slot currently has focus; it holds no state of its own
// about which slot that is -- the caller passes `onDigit` / `onDelete` and decides what they mean.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import {
  GESTURE_LONG_PRESS_MS,
  HIT_SLOP,
  KEYPAD_KEY_MAX_SIZE,
  KEYPAD_KEY_SIZE,
  KEYPAD_KEY_SPACING,
} from '@/src/features/c-session/motor-constants';
import { colors, radius, typography } from '@/src/theme/tokens';

// Calculator order (7-8-9 on top, 1-2-3 on the bottom digit row), not phone-dialer order (1-2-3 on
// top) -- matches what "mobile calculator numbers" means. `null` is a same-size blank so the '0'
// and delete key land in their calculator seats (bottom row, left column empty) instead of drifting
// left under a flex-wrap that has no notion of a fixed 3-column grid.
const KEYPAD_ROWS: readonly (readonly (string | null)[])[] = [
  ['7', '8', '9'],
  ['4', '5', '6'],
  ['1', '2', '3'],
  [null, '0', 'delete'],
];

const KEYPAD_COLUMNS = 3;

// Caps the grid's own width at 3 keys' worth of KEYPAD_KEY_MAX_SIZE plus the gaps between them,
// so `key`'s `flex: 1` has no wider container to stretch into on a spacious panel. `aspectRatio: 1`
// (on `key`, below) then caps height the same way, since a capped width still forces a matching
// height -- this is the whole mechanism 2026-08-26's "reduce the keypad's height, keep keys square"
// request rests on, not a second, independent height rule.
const KEYPAD_GRID_MAX_WIDTH = KEYPAD_KEY_MAX_SIZE * KEYPAD_COLUMNS + KEYPAD_KEY_SPACING * (KEYPAD_COLUMNS - 1);

export type DigitKeypadProps = {
  disabled?: boolean;
  onDigit: (digit: string) => void;
  onDelete: () => void;
};

export function DigitKeypad({ disabled = false, onDelete, onDigit }: DigitKeypadProps) {
  return (
    <View accessibilityRole="none" style={styles.grid}>
      {KEYPAD_ROWS.map((row, rowIndex) => (
        <View key={rowIndex} style={styles.row}>
          {row.map((cell, cellIndex) => {
            if (cell === null) {
              // A distinct namespace from `cell`'s own keys below, not a bare `cellIndex`: row 4 is
              // `[null, '0', 'delete']` -- React string-coerces keys for comparison, so a spacer
              // keyed by its numeric index 0 collides with the very next cell's digit key '0'.
              return <View key={`spacer-${cellIndex}`} style={styles.keySpacer} />;
            }
            if (cell === 'delete') {
              return (
                <Pressable
                  accessibilityLabel="delete digit"
                  accessibilityRole="button"
                  accessibilityState={{ disabled }}
                  delayLongPress={GESTURE_LONG_PRESS_MS}
                  disabled={disabled}
                  hitSlop={HIT_SLOP}
                  key={cell}
                  onPress={onDelete}
                  style={({ pressed }) => [
                    styles.key,
                    styles.deleteKey,
                    disabled && styles.keyDisabled,
                    pressed && !disabled && styles.pressed,
                  ]}>
                  <Ionicons color={colors.textSecondary} name="backspace-outline" size={22} />
                </Pressable>
              );
            }
            return (
              <Pressable
                accessibilityLabel={`digit ${cell}`}
                accessibilityRole="button"
                accessibilityState={{ disabled }}
                delayLongPress={GESTURE_LONG_PRESS_MS}
                disabled={disabled}
                hitSlop={HIT_SLOP}
                key={cell}
                onPress={() => onDigit(cell)}
                style={({ pressed }) => [
                  styles.key,
                  disabled && styles.keyDisabled,
                  pressed && !disabled && styles.pressed,
                ]}>
                <AppText style={styles.keyText}>{cell}</AppText>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  deleteKey: { backgroundColor: colors.surface2 },
  grid: {
    alignSelf: 'center',
    gap: KEYPAD_KEY_SPACING,
    maxWidth: KEYPAD_GRID_MAX_WIDTH,
    width: '100%',
  },
  // Width is flexible up to KEYPAD_GRID_MAX_WIDTH (fills the row, which now fills the card's own
  // width, capped); `aspectRatio: 1` keeps height matched to whatever that width ends up being, so
  // the key stays square instead of a fixed height fighting a flexible width into a rectangle. The
  // touch-target constancy rule (motor-constants.ts) is about the key staying the same size across
  // difficulty levels, not about matching the screen's width -- KEYPAD_KEY_SIZE still sets the
  // floor via `minHeight`/`minWidth`, so a key is never smaller than that minimum, only ever equal
  // or larger (and, since the grid above, never larger than KEYPAD_KEY_MAX_SIZE either).
  key: {
    alignItems: 'center',
    aspectRatio: 1,
    backgroundColor: colors.surface1,
    borderBottomColor: colors.borderStrong,
    borderBottomWidth: 3,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    flex: 1,
    justifyContent: 'center',
    minHeight: KEYPAD_KEY_SIZE,
    minWidth: KEYPAD_KEY_SIZE,
  },
  keyDisabled: { opacity: 0.55 },
  keySpacer: { aspectRatio: 1, flex: 1, minHeight: KEYPAD_KEY_SIZE, minWidth: KEYPAD_KEY_SIZE },
  keyText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.lg,
  },
  pressed: { opacity: 0.72 },
  row: {
    flexDirection: 'row',
    gap: KEYPAD_KEY_SPACING,
  },
});
