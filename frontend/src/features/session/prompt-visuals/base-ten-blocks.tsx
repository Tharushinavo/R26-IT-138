import { StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type {
  BaseTenBlocksVisual,
  PlaceName,
} from '@/src/features/session/prompt-visuals/types';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The `base_ten_blocks` representation for B-PV02 / B-PV04 — hundreds flats, tens rods and ones
// cubes, one group per place the payload names.
//
// THIS VISUAL SHOWS STRUCTURE, AND THAT IS CORRECT HERE. Elsewhere in this directory, grouping
// objects would be forbidden client-side scaffolding — it would hand over the counting the item
// measures. Base-ten blocks are different: the grouping *is* the representation the catalogue
// specifies for these templates, and decomposition is the thing the child is being asked to read.
// Drawing 342 as three flats, four rods and two cubes is the intended scaffold, not a leak.
//
// No digit labels, no per-group counts, no total. The blocks are countable; naming their quantities
// would turn "write 342 in expanded form" into a transcription exercise.

const PLACE_MULTIPLIER: Record<PlaceName, number> = { hundreds: 100, ones: 1, tens: 10 };

function digitFor(value: number, place: PlaceName): number {
  return Math.floor(value / PLACE_MULTIPLIER[place]) % 10;
}

function BlockGroup({ count, place }: { count: number; place: PlaceName }) {
  const blockStyle =
    place === 'hundreds' ? styles.flat : place === 'tens' ? styles.rod : styles.cube;

  return (
    <View style={styles.group}>
      <View accessibilityLabel={`${place} blocks`} style={styles.groupBlocks}>
        {count === 0 ? (
          <AppText style={styles.none}>none</AppText>
        ) : (
          Array.from({ length: count }).map((_unused, index) => (
            <View
              // Individually focusable and unnumbered, as everywhere else here: a screen-reader user
              // counts the blocks by traversing them rather than being told how many there are.
              accessibilityLabel={`${place} block`}
              accessibilityRole="image"
              accessible
              key={index}
              style={blockStyle}
            />
          ))
        )}
      </View>
      <AppText align="center" style={styles.groupLabel}>
        {place}
      </AppText>
    </View>
  );
}

export function BaseTenBlocks({ visual }: { visual: BaseTenBlocksVisual }) {
  return (
    <View accessibilityLabel="Base ten blocks" style={styles.row}>
      {visual.places.map((place) => (
        <BlockGroup count={digitFor(visual.value, place)} key={place} place={place} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  cube: {
    backgroundColor: colors.accentGreen,
    borderColor: colors.surface1,
    borderRadius: 3,
    borderWidth: 1,
    height: 14,
    width: 14,
  },
  flat: {
    backgroundColor: colors.accentBlue,
    borderColor: colors.surface1,
    borderRadius: 3,
    borderWidth: 1,
    height: 34,
    width: 34,
  },
  group: { alignItems: 'center', flex: 1, gap: spacing.xs },
  groupBlocks: {
    alignItems: 'flex-end',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 3,
    justifyContent: 'center',
    minHeight: 38,
  },
  groupLabel: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.xs,
    letterSpacing: typography.letterSpacing.label,
  },
  none: { color: colors.textMuted, fontSize: typography.fontSize.xs },
  rod: {
    backgroundColor: '#ffb51f',
    borderColor: colors.surface1,
    borderRadius: 3,
    borderWidth: 1,
    height: 34,
    width: 11,
  },
  row: {
    backgroundColor: colors.secondarySoft,
    borderColor: colors.secondary,
    borderRadius: radius.lg,
    borderWidth: 2,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
});
