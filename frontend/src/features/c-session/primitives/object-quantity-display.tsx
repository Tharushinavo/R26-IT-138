// The shared read-only quantity-as-objects display (10e-0). Built to unblock `option-select`'s
// `integer-field` option source (10d refused it -- see `option-select-logic.ts`'s own header --
// because the only rendering that resolver could produce was a numeral token, and the payload
// number on that path IS the answer). This primitive exists so the quantity can be shown honestly,
// as a count of objects, never as a digit.
//
// WRAP, NOT SCROLL, AND NEVER AT A FIXED COUNT PER ROW. A single long scrolling row is the worst
// case for a child trying to take in a quantity -- it guarantees most of it is off-screen at any
// moment. `ordered-value-sequence-surface.tsx`'s own 10a fix (wrapping its entry-token row instead
// of scrolling it, after the entry slots ran off-screen) is the direct precedent this follows.
//
// The row length is NEVER a chosen number. `flexWrap: 'wrap'` with a fixed per-object size and
// spacing is what determines how many objects land on one line -- purely a function of the
// container's own rendered width, never a hardcoded column count. This matters beyond layout
// aesthetics: wrapping at exactly 10 per row would build a ten-frame (a base-ten representation);
// wrapping at 5 would do the same for subitizing groups of five. Both are scientific representation
// choices this primitive is not permitted to make on its own -- see `option-select-logic.ts`'s own
// header for the full escalation this exists inside of. DO NOT "tidy" this into a fixed
// `numColumns`-style layout; that would silently make the representation decision this file is
// deliberately not making.
//
// UNIFORM AND NEUTRAL. Every object is the same shape, size and colour -- no per-object variation
// that could imply grouping, ordering, category, or a subset (e.g. every 5th object styled
// differently). Any such variation is, again, the representation decision this batch escalates
// rather than resolves.
//
// THE ACCESSIBILITY LABEL CARRIES NO NUMBER, EVER. The quantity this primitive renders is the
// correct answer on its option-select path -- an accessibility label announcing "N objects" would
// hand that answer to a screen-reader user through a channel the visual rendering (deliberately
// numeral-free) does not. The whole block is one `accessible` element with a fixed, quantity-blind
// label ("a group of objects to count"), and every individual object view is hidden from the
// accessibility tree entirely (`accessibilityElementsHidden` / `importantForAccessibility`), so a
// screen reader cannot recover the count by counting stops either. Treat this the same as the
// numeral-rendering guard: a leak surface, not a separate concern.
//
// DEFENSE IN DEPTH: `RENDER_CAP` mirrors `unit-stepper.tsx`'s own `MAX_LINE_FORWARD_STEPS` doctrine
// -- an unconditional ceiling on how many object views this component will ever render, regardless
// of what `count` it is passed, so a caller bug can never force an unbounded render. It is
// numerically the same value as `option-select-logic.ts`'s own `MAX_QUANTITY` (100), for the same
// corruption-safety reason stated there -- comfortably above every real quantity either template
// this batch owns ever produces (66), never a considered judgement about how many objects a child
// can count. In the ordinary, non-corrupted case, the resolver already refuses anything past that
// bound before this component ever sees it; this is a second, independent line of defense, not the
// primary one.
//
// WHAT 10e SHOULD REUSE, AND WHAT IT SHOULD NOT (`value-token-row.tsx`'s own header is the model
// for writing this down explicitly rather than leaving it to be re-derived). 10e's interactive
// object pool (C-CC-01/C-CC-02) needs its own component, not this one -- its data model is
// fundamentally different (a set of distinct, individually addressable object IDs the child
// selects or places) from this primitive's (a bare count with no identity per object at all), so a
// shared component would end up with an object-id field that is sometimes absent, which is a worse
// shape than two components. What 10e SHOULD reuse: `OBJECT_TOKEN_SIZE` / `OBJECT_TOKEN_SPACING`
// (motor-constants.ts) unmodified, so a child sees the same visual "one object = one unit" language
// across both the passive counting task here and the interactive placement task there; the
// uniform-and-neutral doctrine above; and the wrap-never-a-fixed-count discipline, for the same
// representation-neutrality reason. What 10e should NOT reuse: this component itself.

import { StyleSheet, View } from 'react-native';

import { OBJECT_TOKEN_SIZE, OBJECT_TOKEN_SPACING } from '@/src/features/c-session/motor-constants';
import { AppText } from '@/src/components/app-text';
import { pickCountableEmoji } from '@/src/utils/countable-emoji';


// See the header's own "DEFENSE IN DEPTH" note -- kept numerically equal to, but independent of,
// option-select-logic.ts's MAX_QUANTITY.
const RENDER_CAP = 100;

const QUANTITY_BLIND_LABEL = 'A group of objects to count';

export type ObjectQuantityDisplayProps = {
  count: number;
};

export function ObjectQuantityDisplay({ count }: ObjectQuantityDisplayProps) {
  // Seeded from the quantity itself -- this display has no id of its own, and `count` is the only
  // stable thing it receives. Stable across re-renders, which is what matters; two questions that
  // happen to show the same quantity will show the same fruit, which is harmless.
  const emoji = pickCountableEmoji(`quantity-${count}`);
  const renderCount = Math.max(0, Math.min(count, RENDER_CAP));

  return (
    <View accessibilityLabel={QUANTITY_BLIND_LABEL} accessibilityRole="image" accessible style={styles.row}>
      {Array.from({ length: renderCount }, (_, index) => (
        <View
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
          key={index}
          style={styles.object}>
          {/* The emoji IS the object -- no disc behind it (owner request, 2026-10-18). The box
              keeps its size so the row's layout and the quantity-blind labelling above are both
              untouched. */}
          <AppText style={styles.glyphText}>{emoji}</AppText>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  glyphText: { fontSize: Math.round(OBJECT_TOKEN_SIZE * 0.72), lineHeight: Math.round(OBJECT_TOKEN_SIZE * 0.9) },
  // Sized box, no disc: it reserves the same space the filled circle did so the row wraps
  // identically, but draws nothing of its own.
  object: {
    alignItems: 'center',
    height: OBJECT_TOKEN_SIZE,
    justifyContent: 'center',
    width: OBJECT_TOKEN_SIZE,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: OBJECT_TOKEN_SPACING,
  },
});
