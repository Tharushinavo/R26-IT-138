// A read-only r x c grid of squares (10g, C-EG-02). Built for the `named-integer-fields` archetype's
// grid extension -- see that archetype's own `-logic.ts` header for why C-EG-02 needs a visual at
// all: both real prompts ("Tell how many rows, columns, and squares the array has", "Build the
// array shown") are deictic, and `interactive_assets` is `{}` on every real exemplar, so this
// primitive is the only place the array is ever shown.
//
// NEVER RENDERS A NUMERAL, ANYWHERE. `rows` and `cols` are simultaneously GIVEN and part of the
// answer (`valid_action_space` declares `rows: int` and `cols: int` alongside `submitted_product`),
// so printing either as a digit would hand the child two of the three answers outright -- the exact
// leak `named-integer-fields-logic.ts`'s own header documents excluding them from `payloadValues`
// to avoid. This component receives `rows`/`cols` only to decide how many squares to draw; it never
// puts either number on screen as text, and its `accessibilityLabel` is DIMENSION-BLIND for the
// identical reason `object-pool.tsx`'s own per-object labels are quantity-blind -- announcing
// "5 rows by 5 columns" to a screen reader leaks the answer just as surely as printing it.
// `c-named-integer-fields-no-dimension-leak.test.ts` holds this line.
//
// Passive and never pressed, so SPEC section 10's 48px interactive-touch-target floor does not
// govern it -- sized from its own named constants (`GRID_CELL_SIZE`/`GRID_CELL_SPACING`,
// motor-constants.ts), following `object-quantity-display.tsx`'s own stated precedent. Constant
// regardless of `difficulty_level`; the caller (`named-integer-fields-logic.ts`) enforces
// `MAX_GRID_DIMENSION` before this component ever sees a dimension, so nothing here needs its own
// corruption bound.

import { StyleSheet, View } from 'react-native';

import { GRID_CELL_SIZE, GRID_CELL_SPACING } from '@/src/features/c-session/motor-constants';
import { colors, radius } from '@/src/theme/tokens';

export type ArrayGridProps = {
  rows: number;
  cols: number;
  accent: string;
};

export function ArrayGrid({ accent, cols, rows }: ArrayGridProps) {
  return (
    <View accessibilityLabel="array" accessibilityRole="image" style={styles.grid}>
      {Array.from({ length: rows }, (_, rowIndex) => (
        <View key={rowIndex} style={styles.row}>
          {Array.from({ length: cols }, (_, colIndex) => (
            <View key={colIndex} style={[styles.cell, { borderColor: accent }]} />
          ))}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  cell: {
    backgroundColor: colors.surface1,
    borderRadius: radius.sm,
    borderWidth: 2,
    height: GRID_CELL_SIZE,
    width: GRID_CELL_SIZE,
  },
  grid: {
    alignItems: 'center',
    gap: GRID_CELL_SPACING,
  },
  row: {
    flexDirection: 'row',
    gap: GRID_CELL_SPACING,
  },
});
