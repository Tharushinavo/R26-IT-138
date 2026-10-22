import { StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { ObjectSetVisual } from '@/src/features/session/prompt-visuals/types';
import { labelForCountableEmoji, pickCountableEmoji } from '@/src/utils/countable-emoji';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// A set of discrete countable objects — the `pictorial_objects` / `dot_sets` representation the
// governed catalogue asks for on B-CNT02, B-CNT03 and B-NS02.
//
// WHAT THIS MUST NOT DO. It draws `count` objects because the payload says `count`. It never counts
// them back, never compares them to anything, and never checks the child — correctness is the
// server's alone. And there is deliberately **no client-side scaffolding**: the objects are not
// grouped into fives, not arranged in a ten-frame, not numbered, and not pre-counted. Any of those
// would hand over the exact skill the item measures. A plain wrapped row of identical shapes is the
// point, not a shortcut.

const OBJECT_SIZE = 30;

export function ObjectSet({ seed, visual }: { seed: string; visual: ObjectSetVisual }) {
  const objects = Array.from({ length: visual.count });
  // One emoji for the whole set -- see utils/countable-emoji.ts. Identical objects are what keeps
  // this a counting item rather than a sorting one.
  const emoji = pickCountableEmoji(seed);
  const emojiLabel = labelForCountableEmoji(emoji);

  return (
    <View
      // NOT one accessible node with a count. An earlier revision labelled the group
      // "12 circles" — on a "how many objects are there?" item that reads the answer aloud, which
      // is the same false-mastery defect this batch exists to remove, just routed through the one
      // channel nobody looks at. The objects are therefore individually focusable and deliberately
      // unnumbered: a screen-reader user counts by traversing them, exactly as a sighted child
      // counts by looking. Numbering them would be the pre-counting forbidden above.
      //
      // Honest limitation, recorded rather than papered over: counting visually-presented objects
      // may be inherently inaccessible to some screen-reader users, and no labelling scheme fixes
      // that — the construct itself is visual. Whether those learners are in scope is a
      // study-design question for the research protocol owner, not something a label string can
      // settle.
      accessibilityLabel="A group of objects to count"
      style={styles.tray}>
      {visual.count === 0 ? (
        <AppText style={styles.empty}>No objects</AppText>
      ) : (
        objects.map((_, index) => (
          <View accessibilityLabel={emojiLabel} accessibilityRole="image" accessible key={index}>
            <AppText style={styles.glyph}>{emoji}</AppText>
          </View>
        ))
      )}
    </View>
  );
}

export const objectSetStyles = { OBJECT_SIZE };

const styles = StyleSheet.create({
  glyph: { fontSize: OBJECT_SIZE, lineHeight: Math.round(OBJECT_SIZE * 1.25) },
  empty: { color: colors.textSecondary, fontFamily: typography.fonts.bold },

  tray: {
    alignItems: 'center',
    backgroundColor: colors.secondarySoft,
    borderColor: colors.secondary,
    borderRadius: radius.lg,
    borderWidth: 2,
    // flexWrap plus gap is what keeps 20 objects from overflowing or collapsing at the top of the
    // range: they wrap onto as many rows as the width needs.
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.smPlus,
    justifyContent: 'center',
    padding: spacing.md,
  },
});
