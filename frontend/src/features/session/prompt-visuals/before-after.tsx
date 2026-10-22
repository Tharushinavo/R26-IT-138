import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { BeforeAfterVisual } from '@/src/features/session/prompt-visuals/types';
import { labelForCountableEmoji, pickCountableEmoji } from '@/src/utils/countable-emoji';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// B-NS07 conservation — two panels, before and after.
//
// This visual could not exist until `delta` reached the wire (FE-3h Part 0). Before that the client
// knew the direction of the change but not its magnitude, so only the delta-0 case was drawable — and
// a visual that appeared for exactly one answer value would have been a perfect non-mathematical cue:
// a child would learn "picture ⇒ same" and score well without conserving anything.
//
// When `delta` is 0 the two panels are VISIBLY IDENTICAL — same count, same arrangement, same
// styling. Nothing is subtly altered to hint that something changed, and no rearrangement is invented:
// the payload does not describe one, so drawing one would be the client fabricating content.
//
// Neither panel carries a count, and nothing is labelled "added" or "removed". The child compares the
// two groups; that comparison is the task.

function Panel({ count, emoji, emojiLabel, label }: { count: number; emoji: string; emojiLabel: string; label: string }) {
  return (
    <View style={styles.panel}>
      <AppText align="center" style={styles.panelLabel}>
        {label}
      </AppText>
      <View accessibilityLabel={label} style={styles.panelObjects}>
        {count === 0 ? (
          <AppText style={styles.none}>empty</AppText>
        ) : (
          Array.from({ length: count }).map((_unused, index) => (
<View accessibilityLabel={emojiLabel} accessibilityRole="image" accessible key={index}>
              <AppText style={styles.glyph}>{emoji}</AppText>
            </View>
          ))
        )}
      </View>
    </View>
  );
}

export function BeforeAfter({ seed, visual }: { seed: string; visual: BeforeAfterVisual }) {
  // The SAME emoji before and after: the change being shown is the COUNT, so the objects must be
  // the one thing that does not change between the two panels.
  const emoji = pickCountableEmoji(seed);
  const emojiLabel = labelForCountableEmoji(emoji);
  return (
    <View accessibilityLabel="Two groups of objects, before and after" style={styles.row}>
      <Panel count={visual.before} emoji={emoji} emojiLabel={emojiLabel} label="Before" />
      <Ionicons color={colors.textMuted} name="arrow-forward" size={20} />
      <Panel count={visual.after} emoji={emoji} emojiLabel={emojiLabel} label="After" />
    </View>
  );
}

const OBJECT_SIZE = 18;

const styles = StyleSheet.create({
  glyph: { fontSize: OBJECT_SIZE, lineHeight: Math.round(OBJECT_SIZE * 1.25) },
  none: { color: colors.textMuted, fontSize: typography.fontSize.xs },
  panel: {
    // Both panels are identical in size and styling so that only the number of objects can differ —
    // a panel that looked different for any other reason would be a cue about the answer.
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    gap: spacing.xs,
    padding: spacing.sm,
  },
  panelLabel: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.xs,
    letterSpacing: typography.letterSpacing.label,
  },
  panelObjects: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    justifyContent: 'center',
    minHeight: 64,
  },
  row: {
    alignItems: 'center',
    backgroundColor: colors.secondarySoft,
    borderColor: colors.secondary,
    borderRadius: radius.lg,
    borderWidth: 2,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.sm,
  },
});
