import { Ionicons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type {
  CountSelectionAnswerState,
  CountSelectionRendererSpec,
} from '@/src/features/session/renderers/types';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The count-selection surface (interactive_set_selection). The child builds a count; the encoder
// turns it into `String(count)`.
//
// No maximum is imposed. A ceiling would be a client-side rule about what counts are legitimate
// for an item — the server owns that — and the prompt keys that describe the underlying set are
// out of scope this batch (only `prompt.stem` is rendered). The floor is 0 because a count cannot
// be negative; 0 itself is a real, submittable answer.
//
// A count of -1 is the "not chosen yet" seed from `initialAnswerState`, which the encoder already
// rejects, so submit stays unavailable until the child actually interacts. It renders as a dash,
// and the first "+" tap lands on 0 so that zero stays reachable in one tap.
//
// FE-3g — `poolSize` turns this into a real set-selection surface (B-CNT04-MAKE-SET).
//
// Without it the item produced FALSE MASTERY, which is worse than noise: the stem says "Select
// exactly 7 objects", the surface asked for a number, so the child read 7, entered 7, and was
// marked correct without doing the thing being measured. With a pool, the count comes from the
// objects the child actually selected. `encodeSubmittedValue` is untouched and the submitted value
// is still `String(count)` — FE-3a's contract is unchanged; only where the count comes from changes.
//
// The pool deliberately carries no progress cue: no "3 of 7 selected", no target readout, no
// grouping, no numbering of the objects. Counting the selection is the skill, and a running
// comparison against the target would hand it over. The plain count of what is selected is shown
// because the child needs to know what they are about to submit — that is the answer they built,
// not a hint about whether it is right.

type CountSelectionProps = {
  spec: CountSelectionRendererSpec;
  state: CountSelectionAnswerState;
  disabled?: boolean;
  onChange: (next: CountSelectionAnswerState) => void;
  /** When present, the child selects from a pool of this many objects instead of using the stepper. */
  poolSize?: number;
};

export function CountSelection({
  disabled = false,
  onChange,
  poolSize,
  state,
}: CountSelectionProps) {
  if (poolSize !== undefined) {
    return (
      <SelectablePool
        disabled={disabled}
        onChange={onChange}
        poolSize={poolSize}
        state={state}
      />
    );
  }
  return <CountStepper disabled={disabled} onChange={onChange} state={state} />;
}

function SelectablePool({
  disabled,
  onChange,
  poolSize,
  state,
}: {
  disabled: boolean;
  onChange: (next: CountSelectionAnswerState) => void;
  poolSize: number;
  state: CountSelectionAnswerState;
}) {
  const [selected, setSelected] = useState<ReadonlySet<number>>(() => new Set());

  // The selection set lives here rather than in AnswerState, because AnswerState carries a count
  // and only a count (FE-3a). Keeping *which* objects are selected local is what lets the child
  // deselect the specific object they tapped instead of an arbitrary one.
  //
  // This effect is the one link back: when the screen reseeds the answer to the not-chosen sentinel
  // — "Try again" does exactly that, without changing the opportunity — the highlighted objects must
  // clear too, or the child would see a stale selection that no longer matches the count.
  useEffect(() => {
    if (state.count < 0) setSelected((current) => (current.size === 0 ? current : new Set()));
  }, [state.count]);

  const toggle = (index: number) => {
    const next = new Set(selected);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelected(next);
    onChange({ kind: 'count-selection', count: next.size });
  };

  return (
    <View style={styles.wrapper}>
      <AppText style={styles.label}>Tap the objects you want</AppText>
      <View style={styles.pool}>
        {Array.from({ length: poolSize }).map((_, index) => {
          const isSelected = selected.has(index);
          return (
            <Pressable
              accessibilityLabel={isSelected ? 'Selected object' : 'Object'}
              accessibilityRole="button"
              accessibilityState={{ disabled, selected: isSelected }}
              disabled={disabled}
              key={index}
              onPress={() => toggle(index)}
              style={({ pressed }) => [
                styles.poolObject,
                isSelected && styles.poolObjectSelected,
                disabled && styles.stepButtonDisabled,
                pressed && !disabled && styles.pressed,
              ]}
            />
          );
        })}
      </View>
      <AppText
        accessibilityLabel={
          selected.size === 1 ? '1 object selected' : `${selected.size} objects selected`
        }
        style={styles.poolCount}>
        {selected.size === 1 ? '1 object selected' : `${selected.size} objects selected`}
      </AppText>
    </View>
  );
}

function CountStepper({
  disabled,
  onChange,
  state,
}: {
  disabled: boolean;
  onChange: (next: CountSelectionAnswerState) => void;
  state: CountSelectionAnswerState;
}) {
  const chosen = state.count >= 0;
  const canDecrement = !disabled && state.count > 0;

  return (
    <View style={styles.wrapper}>
      <AppText style={styles.label}>Choose how many</AppText>
      <View style={styles.stepper}>
        <Pressable
          accessibilityLabel="One fewer"
          accessibilityRole="button"
          accessibilityState={{ disabled: !canDecrement }}
          disabled={!canDecrement}
          onPress={() => onChange({ kind: 'count-selection', count: Math.max(0, state.count - 1) })}
          style={({ pressed }) => [
            styles.stepButton,
            !canDecrement && styles.stepButtonDisabled,
            pressed && canDecrement && styles.pressed,
          ]}>
          <Ionicons color={colors.primaryShadow} name="remove" size={30} />
        </Pressable>

        <View accessibilityRole="text" style={styles.readout}>
          <AppText align="center" style={styles.readoutText}>
            {chosen ? String(state.count) : '—'}
          </AppText>
        </View>

        <Pressable
          accessibilityLabel="One more"
          accessibilityRole="button"
          accessibilityState={{ disabled }}
          disabled={disabled}
          onPress={() => onChange({ kind: 'count-selection', count: chosen ? state.count + 1 : 0 })}
          style={({ pressed }) => [
            styles.stepButton,
            disabled && styles.stepButtonDisabled,
            pressed && !disabled && styles.pressed,
          ]}>
          <Ionicons color={colors.primaryShadow} name="add" size={30} />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    color: colors.textSecondary,
    fontSize: typography.fontSize.sm,
    lineHeight: typography.lineHeight.sm,
  },
  pool: {
    alignItems: 'center',
    backgroundColor: colors.secondarySoft,
    borderColor: colors.secondary,
    borderRadius: radius.lg,
    borderWidth: 2,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.smPlus,
    justifyContent: 'center',
    padding: spacing.md,
  },
  poolCount: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
  },
  poolObject: {
    backgroundColor: colors.surface1,
    borderColor: colors.borderStrong,
    borderRadius: 17,
    borderWidth: 2,
    height: 34,
    width: 34,
  },
  poolObjectSelected: {
    backgroundColor: colors.accentBlue,
    borderColor: colors.secondaryForeground,
  },
  pressed: { opacity: 0.72 },
  readout: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 2,
    flex: 1,
    justifyContent: 'center',
    minHeight: 68,
  },
  readoutText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 34,
    lineHeight: 42,
  },
  stepButton: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderBottomColor: colors.primaryShadow,
    borderBottomWidth: 3,
    borderColor: colors.primary,
    borderRadius: radius.md,
    borderWidth: 2,
    height: 68,
    justifyContent: 'center',
    width: 68,
  },
  stepButtonDisabled: { opacity: 0.45 },
  stepper: { alignItems: 'center', flexDirection: 'row', gap: spacing.smPlus },
  wrapper: { gap: spacing.sm },
});
