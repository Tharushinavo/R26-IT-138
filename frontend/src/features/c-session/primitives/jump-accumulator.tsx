// The read-only record of jumps a child has actually made (10c), bound to `list[int]` the same way
// `value-token-row.tsx` is -- but the ARCHETYPE chooses which of the two primitives a `list[int]`
// key renders through, because the scene decides whether the list is entered or accumulated
// (sequence doc §3.2). `line-traversal`'s `jumps` is accumulated: one entry appended per step the
// child actually takes on the `UnitStepper` above it, never typed in directly. `ValueTokenRow` is
// deliberately not reused here -- its own header commits it to `ordered-value-sequence` and
// `partition-allocation`, and gaining a third caller with a different value-origin story (accumulated
// vs entered/reordered) is exactly the drift `line-traversal`'s own separation from
// `ordered-value-sequence` exists to avoid (see `line-traversal-logic.ts`'s header).
//
// BOUNDED HEIGHT, INTERNAL SCROLL (2026-08-26 finding, found by the user hand-testing at a high jump
// count). A child who reaches, say, difficulty 5's real maximum of 18 jumps wraps this list across
// many rows -- and an unbounded list pushes SUBMIT further down the screen with every jump, exactly
// the "control grows past the visible area" failure this project already hit once (10a's entry
// slots at difficulty 5). The fix here is the same shape as that one: a fixed maximum height with
// its own internal scroll, so SUBMIT's position never moves regardless of jump count, and the list
// auto-scrolls to keep the most recent jump in view -- the same doctrine `unit-stepper.tsx`'s own
// marker auto-scroll already follows.
//
// Purely a display otherwise: it takes the jumps array and renders it, holding no state of its own
// about how the array got that way -- the surface owns `jumps` and passes the current value down,
// the same discipline `UnitStepper` follows for `position`.

import { useEffect, useRef } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import { TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { colors, radius, typography } from '@/src/theme/tokens';

const CHIP_SIZE = Math.round(TOKEN_TOUCH_TARGET_SIZE * 0.7);
const ROW_GAP = Math.round(TOKEN_SPACING * 0.5);

// A LAYOUT bound on how many rows of jumps are visible at once before the list scrolls internally,
// not a catalogue constraint -- the same "bound the display, not the data" doctrine
// `unit-stepper.tsx`'s own `MAX_LINE_FORWARD_STEPS` follows. Two rows keeps the most recent jumps
// visible without SUBMIT's position ever depending on how many jumps exist.
const VISIBLE_ROWS = 2;
const JUMP_LIST_MAX_HEIGHT = CHIP_SIZE * VISIBLE_ROWS + ROW_GAP * (VISIBLE_ROWS - 1);

export type JumpAccumulatorProps = {
  jumps: readonly number[];
};

export function JumpAccumulator({ jumps }: JumpAccumulatorProps) {
  const scrollRef = useRef<ScrollView>(null);

  // Keeps the most recent jump visible as the list grows past what fits -- the direct lesson of
  // the entry-slot-off-screen finding this project already hit once, applied here to a list rather
  // than to UnitStepper's own marker.
  useEffect(() => {
    scrollRef.current?.scrollToEnd({ animated: true });
  }, [jumps.length]);

  if (jumps.length === 0) return null;

  return (
    <ScrollView ref={scrollRef} style={styles.scrollBound}>
      <View style={styles.row}>
        {jumps.map((jump, index) => (
          <View key={index} style={styles.chip}>
            <AppText style={styles.chipText}>{jump}</AppText>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignItems: 'center',
    backgroundColor: colors.primarySoft,
    borderColor: colors.primary,
    borderRadius: radius.pill,
    borderWidth: 2,
    height: CHIP_SIZE,
    justifyContent: 'center',
    width: CHIP_SIZE,
  },
  chipText: {
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: ROW_GAP,
  },
  scrollBound: {
    maxHeight: JUMP_LIST_MAX_HEIGHT,
  },
});
