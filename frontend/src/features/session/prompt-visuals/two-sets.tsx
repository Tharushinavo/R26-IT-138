import { StyleSheet, View } from 'react-native';

import type { TwoSetsVisual } from '@/src/features/session/prompt-visuals/types';
import { AppText } from '@/src/components/app-text';
import { labelForCountableEmoji, pickCountableEmoji } from '@/src/utils/countable-emoji';
import { colors, radius, spacing } from '@/src/theme/tokens';

// Two groups to compare at a glance — the `dot_sets` representation B-NS03 asks for.
//
// The two panels are deliberately IDENTICAL in size, shape, colour and object size. The only thing
// that differs is how many objects each holds, because that is the only thing the child is being
// asked to compare. A panel styled to look "bigger" or "first" would be a cue about the answer.
// They are laid out side by side in the order the payload gave (set_a then set_b) and nothing
// implies an ordering beyond that; neither is labelled "more" or "less", and neither carries a
// count.
//
// No grouping, no ten-frames, no alignment of one set against the other for easy pairing: matching
// the two groups is the comparison skill being measured.

const OBJECT_SIZE = 22;

function SetPanel({ count, emoji, emojiLabel, label }: { count: number; emoji: string; emojiLabel: string; label: string }) {
  return (
    <View accessibilityLabel={label} style={styles.panel}>
      {Array.from({ length: count }).map((_, index) => (
        <View accessibilityLabel={emojiLabel} accessibilityRole="image" accessible key={index}>
          <AppText style={styles.glyph}>{emoji}</AppText>
        </View>
      ))}
    </View>
  );
}

// Counts are deliberately absent from every label here. On "compare the two sets", announcing
// "3 stars" and "5 stars" states which group is larger — that is the answer, read aloud. The
// objects are individually focusable and unnumbered instead, so a screen-reader user compares by
// traversing each group, as a sighted child compares by looking. See object-set.tsx for the
// broader limitation: a visual comparison construct may not be fully accessible by any labelling,
// which is a study-design question rather than an implementation one.
export function TwoSets({ seed, visual }: { seed: string; visual: TwoSetsVisual }) {
  // BOTH panels get the SAME emoji. Different objects per side would turn "which group has more?"
  // into a comparison of unlike things, which is a different question from the one being asked.
  const emoji = pickCountableEmoji(seed);
  const emojiLabel = labelForCountableEmoji(emoji);
  return (
    <View accessibilityLabel="Two groups of objects to compare" style={styles.row}>
      <SetPanel count={visual.setA} emoji={emoji} emojiLabel={emojiLabel} label="First group" />
      <View style={styles.divider} />
      <SetPanel count={visual.setB} emoji={emoji} emojiLabel={emojiLabel} label="Second group" />
    </View>
  );
}

const styles = StyleSheet.create({
  glyph: { fontSize: OBJECT_SIZE, lineHeight: Math.round(OBJECT_SIZE * 1.25) },
  divider: { backgroundColor: colors.border, width: 2 },
  panel: {
    alignContent: 'center',
    alignItems: 'center',
    // flex: 1 on both panels is what makes them the same size regardless of how many objects each
    // holds — the container must not shrink to its content, or the emptier set would look smaller
    // for a reason that has nothing to do with quantity.
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
    minHeight: 96,
    padding: spacing.sm,
  },
  row: {
    alignItems: 'stretch',
    backgroundColor: colors.secondarySoft,
    borderColor: colors.secondary,
    borderRadius: radius.lg,
    borderWidth: 2,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
});
