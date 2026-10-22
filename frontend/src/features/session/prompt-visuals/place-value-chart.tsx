import { StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { PlaceValueChartVisual } from '@/src/features/session/prompt-visuals/types';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The `place_value_chart` representation for B-PV01 / B-PV03 — labelled columns with the digits of
// the number sitting in them.
//
// NOTHING IS HIGHLIGHTED. `askedPlace` is on the spec so the chart can be described accurately, and
// is deliberately not used to emphasise a column: which place the question asks about is already in
// the stem, and marking that column would answer the question instead of presenting it. The chart's
// job is to make the *structure* of the number visible — which digit sits in which place — not to
// point at one of them.
//
// The digits are the digits of the number the server sent. Splitting 342 into 3/4/2 is presentation;
// deciding whether the child's answer is right is the server's job alone.

export function PlaceValueChart({ visual }: { visual: PlaceValueChartVisual }) {
  const digits = String(visual.value).padStart(visual.places.length, '0').split('');

  return (
    <View accessibilityLabel="A place value chart" style={styles.chart}>
      {visual.places.map((place, index) => (
        <View key={place} style={styles.column}>
          <View style={styles.headerCell}>
            <AppText align="center" style={styles.headerText}>
              {place}
            </AppText>
          </View>
          <View
            // Each cell is focusable and named by its place, which is the structure a screen-reader
            // user needs — it is the same information a sighted child reads off the chart, and it
            // does not state which place was asked about.
            accessibilityLabel={`${place}: ${digits[index]}`}
            accessibilityRole="text"
            accessible
            style={styles.digitCell}>
            <AppText align="center" style={styles.digitText}>
              {digits[index]}
            </AppText>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  chart: {
    alignSelf: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.secondary,
    borderRadius: radius.md,
    borderWidth: 2,
    flexDirection: 'row',
    overflow: 'hidden',
  },
  column: {
    borderColor: colors.border,
    borderLeftWidth: 1,
    minWidth: 78,
  },
  digitCell: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.md,
  },
  digitText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 34,
    lineHeight: 42,
  },
  headerCell: {
    backgroundColor: colors.secondarySoft,
    borderBottomColor: colors.secondary,
    borderBottomWidth: 2,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  headerText: {
    color: colors.secondaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: typography.fontSize.sm,
    letterSpacing: typography.letterSpacing.label,
  },
});
