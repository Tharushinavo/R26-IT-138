// The shared discrete position control (10c), built once for both `line-traversal` (this
// sub-phase) and 10d's `line-position` to compose over unmodified (master work order §5A: "Build
// the stepping primitive once; `line-position` and `line-traversal` are two thin compositions over
// it, not two separate designs").
//
// RULING 6.3, not a builder's choice: discrete integer stepping, never continuous drag. One step is
// one unit at every difficulty; the per-step touch target is a constant (STEP_TOUCH_TARGET_SIZE /
// STEP_SPACING, motor-constants.ts); when a line has more ticks than fit on screen, it scrolls --
// it never compresses a tick to fit more of them. This mirrors `value-token-row.tsx`'s own
// `reorder` mode, which scrolls horizontally rather than shrinking a token, and
// `digit-keypad.tsx`'s stepper-vs-keypad ruling: interaction COST (here, step count) is allowed to
// track the task's own magnitude; interaction SIZE never is.
//
// Stateless: the caller (the archetype surface) owns `position`; this component only ever reports
// "step forward" / "step back" intents and renders whatever position it is given. It holds no
// state of its own about the line's origin or the child's progress, matching `DigitKeypad`'s own
// "holds no state of its own" doctrine.
//
// The line itself is DISPLAY ONLY -- individual ticks are not pressable. Making a tick itself the
// tap target would let a child jump straight to any position rather than making the successive
// unit jumps `jump-accumulator.tsx` needs to record one by one, and would reopen exactly the
// imprecise-placement question ruling 6.3 already closed for continuous drag.

import { useEffect, useRef } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { GESTURE_LONG_PRESS_MS, HIT_SLOP, STEP_SPACING, STEP_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { colors, radius, typography } from '@/src/theme/tokens';

const TICK_STRIDE = STEP_TOUCH_TARGET_SIZE + STEP_SPACING;

// A LAYOUT bound on how many forward ticks the line ever renders, not a catalogue constraint and
// never derived from any payload value (deriving it from the addends would make the line's own
// extent leak the answer -- see line-traversal-logic.ts's header). The generator's real maximum
// forward-jump count across every difficulty level of C-JB-02 is `min(addend_a, addend_b)`, which
// tops out at 18 (magnitude_a_by_level's own difficulty-5 bound in generation_config.py). 30 is
// comfortably above that while still catching a materially corrupted `position` before it renders
// an unbounded number of ticks.
const MAX_LINE_FORWARD_STEPS = 30;

export type UnitStepperProps = {
  /** Where the line begins. Rendered as the first tick, never itself steppable past backward. */
  originValue: number;
  /** How many forward unit steps have been taken so far -- the caller's own state, not derived. */
  forwardSteps: number;
  disabled?: boolean;
  onStepForward: () => void;
  onStepBack: () => void;
  /** Fires when the coarse "+N" button is pressed -- only rendered when `coarseStep` is set. The
   *  caller adds `coarseStep` to its own `forwardSteps` state; this component holds none of its
   *  own, matching every other callback here. */
  onCoarseForward?: () => void;
  /** Fires when the coarse "-N" button is pressed -- only rendered when `coarseStep` is set. */
  onCoarseBack?: () => void;
  /**
   * How many forward ticks the line renders. Defaults to `MAX_LINE_FORWARD_STEPS`, the corruption
   * bound `line-traversal` relies on (see its comment above -- there the extent MUST NOT come from
   * the payload, since deriving it from the addends would leak the answer). `line-position` (10d)
   * passes its own `interval_max` here instead, which is legitimate for THAT archetype because the
   * line's range is the task's own stated given, not a derived answer -- see
   * `line-position-logic.ts`'s header for why the two cases differ.
   */
  maxForwardSteps?: number;
  /**
   * When set, renders a second, LARGER step pair (+/- this many units) alongside the +/-1 pair.
   * Added for 10d's `line-position`, whose targets sit up to 34 units from the origin: unit-only
   * stepping there would cost 34 taps at difficulty 5 against 2 at difficulty 1, and unlike
   * `line-traversal` (where each unit jump IS the counting-on act being scored) those taps assess
   * nothing -- they are pure transit cost, which is exactly the SPEC section 10 interaction-cost
   * confound. See `line-position-surface.tsx`'s header for the full reasoning and the measured
   * tap counts. Omitted by `line-traversal`, which keeps unit-only stepping deliberately.
   *
   * This stays within ruling 6.3: still discrete integer stepping, still a constant per-step touch
   * target, still a line that scrolls rather than compresses. The coarse step is a fixed constant
   * chosen by the caller, never derived from `difficulty_level`.
   */
  coarseStep?: number;
  /**
   * A forward offset (from `originValue`, same units as `forwardSteps`) to mark with a distinct
   * FLAG tick, separate from the movable position marker. Added for 10d's `line-position`, whose
   * prompt ("Move the marker to the target spot on the line") is deictic and needs a visible
   * target -- omitted entirely by `line-traversal`, which has no such given position to show.
   *
   * This does not newly expose `target_position`'s own numeral: every tick already renders its own
   * value (`tickLabel`, below) regardless of this prop, the same way every other position on the
   * line is labelled -- the flag only marks WHICH of those already-visible ticks is the one to
   * reach, exactly the way a marked destination on a paper number line would. There is no separate
   * digit token anywhere that would let a child bypass the line and read the target off a numeral
   * printed next to the prompt instead.
   */
  targetForwardOffset?: number;
};

export function UnitStepper({
  coarseStep,
  disabled = false,
  forwardSteps,
  maxForwardSteps = MAX_LINE_FORWARD_STEPS,
  onCoarseBack,
  onCoarseForward,
  onStepBack,
  onStepForward,
  originValue,
  targetForwardOffset,
}: UnitStepperProps) {
  const scrollRef = useRef<ScrollView>(null);
  const position = originValue + forwardSteps;

  // Keeps the marker on screen as it advances -- the direct lesson of the entry-slot-off-screen
  // finding this project already hit once (10a, difficulty 5): a control that can grow past the
  // visible area must actively keep its own moving part in view, not rely on the child to notice
  // and scroll manually.
  useEffect(() => {
    const targetX = Math.max(0, forwardSteps * TICK_STRIDE - TICK_STRIDE);
    scrollRef.current?.scrollTo({ x: targetX, animated: true });
  }, [forwardSteps]);

  const canStepBack = forwardSteps > 0 && !disabled;
  const canStepForward = forwardSteps < maxForwardSteps && !disabled;
  // A coarse step is only offered when it would land within range -- pressing it never overshoots
  // past 0 or `maxForwardSteps` and needs no clamping on the caller's side.
  const canCoarseBack = coarseStep !== undefined && forwardSteps - coarseStep >= 0 && !disabled;
  const canCoarseForward =
    coarseStep !== undefined && forwardSteps + coarseStep <= maxForwardSteps && !disabled;

  return (
    <View>
      <ScrollView
        horizontal
        ref={scrollRef}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.line}>
        {Array.from({ length: maxForwardSteps + 1 }, (_, tickIndex) => {
          const tickValue = originValue + tickIndex;
          const isMarker = tickIndex === forwardSteps;
          const isTarget = tickIndex === targetForwardOffset;
          return (
            <View key={tickIndex} style={styles.tickColumn}>
              <View style={[styles.tick, isTarget && styles.tickTarget, isMarker && styles.tickMarked]}>
                {isMarker ? <View style={styles.marker} /> : isTarget ? <View style={styles.targetDot} /> : null}
              </View>
              <AppText style={styles.tickLabel}>{tickValue}</AppText>
            </View>
          );
        })}
      </ScrollView>
      <View style={styles.controls}>
        {/* Coarse row above fine row, forward on the outside of both -- so the two "+" buttons sit
            adjacent (top-right area) and the two "-" buttons sit adjacent (bottom-left area), a
            layout a child can learn once ("bigger jump" vs "small jump", each direction grouped)
            rather than four buttons in an arbitrary order. Coarse buttons render ONLY when
            `coarseStep` is set -- `line-traversal` never passes it, so its own two-button shape is
            unchanged. */}
        {coarseStep !== undefined && (
          <Pressable
            accessibilityLabel={`jump forward ${coarseStep}`}
            accessibilityRole="button"
            accessibilityState={{ disabled: !canCoarseForward }}
            delayLongPress={GESTURE_LONG_PRESS_MS}
            disabled={!canCoarseForward}
            hitSlop={HIT_SLOP}
            onPress={onCoarseForward}
            style={({ pressed }) => [
              styles.controlButton,
              !canCoarseForward && styles.controlButtonDisabled,
              pressed && canCoarseForward && styles.pressed,
            ]}>
            <AppText style={styles.controlButtonText}>{`▲▲ jump +${coarseStep}`}</AppText>
          </Pressable>
        )}
        <Pressable
          accessibilityLabel="jump forward one"
          accessibilityRole="button"
          accessibilityState={{ disabled: !canStepForward }}
          delayLongPress={GESTURE_LONG_PRESS_MS}
          disabled={!canStepForward}
          hitSlop={HIT_SLOP}
          onPress={onStepForward}
          style={({ pressed }) => [
            styles.controlButton,
            !canStepForward && styles.controlButtonDisabled,
            pressed && canStepForward && styles.pressed,
          ]}>
          <AppText style={styles.controlButtonText}>▲ jump +1</AppText>
        </Pressable>
        <Pressable
          accessibilityLabel="step back one"
          accessibilityRole="button"
          accessibilityState={{ disabled: !canStepBack }}
          delayLongPress={GESTURE_LONG_PRESS_MS}
          disabled={!canStepBack}
          hitSlop={HIT_SLOP}
          onPress={onStepBack}
          style={({ pressed }) => [
            styles.controlButton,
            !canStepBack && styles.controlButtonDisabled,
            pressed && canStepBack && styles.pressed,
          ]}>
          <AppText style={styles.controlButtonText}>▼ back</AppText>
        </Pressable>
        {coarseStep !== undefined && (
          <Pressable
            accessibilityLabel={`step back ${coarseStep}`}
            accessibilityRole="button"
            accessibilityState={{ disabled: !canCoarseBack }}
            delayLongPress={GESTURE_LONG_PRESS_MS}
            disabled={!canCoarseBack}
            hitSlop={HIT_SLOP}
            onPress={onCoarseBack}
            style={({ pressed }) => [
              styles.controlButton,
              !canCoarseBack && styles.controlButtonDisabled,
              pressed && canCoarseBack && styles.pressed,
            ]}>
            <AppText style={styles.controlButtonText}>{`▼▼ back ${coarseStep}`}</AppText>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  controlButton: {
    alignItems: 'center',
    backgroundColor: colors.accentGreen,
    borderColor: colors.accentGreen,
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: STEP_TOUCH_TARGET_SIZE,
  },
  controlButtonDisabled: { opacity: 0.5 },
  controlButtonText: {
    color: colors.surface1,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.body,
  },
  // Stacked vertically -- jump forward above, back below (2026-08-26 request) -- rather than
  // side-by-side, with up/down arrows matching that stacking direction.
  controls: {
    flexDirection: 'column',
    gap: STEP_SPACING,
    marginTop: STEP_SPACING,
  },
  line: {
    alignItems: 'center',
    gap: STEP_SPACING,
    paddingVertical: STEP_SPACING,
  },
  // The dot's own fill is back to solid colors.primary (2026-08-26: the faded-green fill this file
  // briefly used was reverted -- the OUTER RING (tickMarked, below) is where accentGreen belongs
  // instead, so the dot stays red and the ring around it is what turned green).
  marker: {
    backgroundColor: colors.primary,
    borderRadius: radius.pill,
    height: STEP_TOUCH_TARGET_SIZE * 0.5,
    width: STEP_TOUCH_TARGET_SIZE * 0.5,
  },
  pressed: { opacity: 0.72 },
  tick: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 2,
    height: STEP_TOUCH_TARGET_SIZE,
    justifyContent: 'center',
    width: STEP_TOUCH_TARGET_SIZE,
  },
  tickColumn: {
    alignItems: 'center',
    gap: 4,
  },
  tickLabel: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: typography.fontSize.xs,
  },
  // Back to colors.primary (2026-08-26 correction): the ring around the current-position tick
  // matches the dot inside it (`marker`, above) -- both red, not a red dot inside a green ring.
  tickMarked: {
    borderColor: colors.primary,
  },
  // The GIVEN target tick (line-position only) -- accentGreen, distinct from `tickMarked`'s own red,
  // so the two are never confused. `tickMarked` still wins over `tickTarget` when both coincide
  // (style array order below), since the child's own position is the more useful thing to see once
  // they have actually reached the target.
  tickTarget: {
    borderColor: colors.accentGreen,
  },
  // A SOLID green CIRCLE (2026-08-26 correction: an earlier draft made this hollow -- border only,
  // no fill -- the user asked for it filled), not the flag glyph an even earlier draft used (the
  // emoji did not render consistently and showed as a placeholder box).
  targetDot: {
    backgroundColor: colors.accentGreen,
    borderRadius: radius.pill,
    height: STEP_TOUCH_TARGET_SIZE * 0.5,
    width: STEP_TOUCH_TARGET_SIZE * 0.5,
  },
});
