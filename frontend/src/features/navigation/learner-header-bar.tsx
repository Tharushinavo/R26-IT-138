// The learner header bar: the adventure-charge battery on the left, "Hi, <name>!" on the right.
// Extracted verbatim from learner-home-screen.tsx, which is now one of its two callers (the game
// hub is the other) rather than the sole owner of the markup.
//
// It is deliberately a PRESENTATION component: `displayName` comes in as a prop, and this file
// resolves no name of its own. Home and the session-preparation screen already resolve theirs from
// different sources (`me.learnerProfile.name` vs `learner.displayName`), so a header that picked
// one would silently change the other screen's greeting. Whether those two should agree is a real
// question, but it is not this extraction's to answer, and it is not answered here.
//
// The brand wordmark that used to sit here is gone; the battery reads `level`/`maxLevel` from
// AdventureChargeProvider (the (learner) layout wraps every screen that renders this bar). The
// "Play Adventure" pill also used to render here, from the same provider's `pillVisible`; it moved
// to learner-tab-bar.tsx on 2026-09-27 so it appears next to the Play button that raises it,
// rather than at the opposite end of the screen from it. The shared context is still what makes
// that work: the button setting the flag and the pill reading it are different components.
//
// The two height constants below are the ones home measures its viewport against
// (`fixedHeaderHeight = compact ? 63 : 88`). They live here, next to the styles that produce them,
// so a change to the padding and a change to the number a caller subtracts cannot drift apart.
// The game hub sizes its grid against the same pair.

import { router } from 'expo-router';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import {
  LEARNER_HEADER_HEIGHT,
  LEARNER_HEADER_HEIGHT_COMPACT,
} from '@/src/features/navigation/chrome-metrics';
import { useAdventureCharge } from '@/src/features/navigation/adventure-charge-context';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// Re-exported so this bar's existing callers keep importing them from the component that draws
// them; the values themselves live in chrome-metrics.ts, which imports nothing and therefore
// cannot be part of a require cycle. See that file for the cycle this broke.
export { LEARNER_HEADER_HEIGHT, LEARNER_HEADER_HEIGHT_COMPACT };

function AdventureBattery({ compact, level, maxLevel }: { compact: boolean; level: number; maxLevel: number }) {
  return (
    <View
      accessibilityLabel={`Adventure charge: ${level} of ${maxLevel} bars`}
      accessibilityRole="progressbar"
      accessibilityValue={{ max: maxLevel, min: 0, now: level }}
      style={[styles.battery, compact && styles.batteryCompact]}>
      <View style={styles.batteryCells}>
        {Array.from({ length: maxLevel }, (_, index) => (
          <View
            key={index}
            style={[styles.batteryCell, index < level ? styles.batteryCellFilled : styles.batteryCellEmpty]}
          />
        ))}
      </View>
      <View style={styles.batteryNub} />
    </View>
  );
}

export function LearnerHeaderBar({
  compact = false,
  displayName,
  showBattery = false,
}: {
  compact?: boolean;
  displayName: string;
  /** The adventure-charge battery belongs to Home only (owner request, 2026-10-21); the game hub,
   * the profile and compD show the greeting alone. The header keeps its height either way. */
  showBattery?: boolean;
}) {
  const { level, maxLevel } = useAdventureCharge();

  return (
    <View style={[styles.headerGreetingSection, compact && styles.sectionCompact]}>
      <View style={styles.header}>
        {showBattery ? (
          <View style={styles.brand}>
            <AdventureBattery compact={compact} level={level} maxLevel={maxLevel} />
          </View>
        ) : null}

        {/* The "Play Adventure" pill used to sit here, centred between the battery and the
            greeting. It now renders above the tab bar (learner-tab-bar.tsx), next to the Play
            button that raises it, on owner instruction (2026-09-27). What stays is the spacer:
            it is what pushes the greeting to the right edge, so removing it as well would have
            slid the name back against the battery. */}
        <View style={styles.headerSpacer} />

        {/* THE GREETING IS THE WAY TO THE PROFILE (owner request). A child's own name is the most
            recognisable thing on this screen, and tapping yourself to get to your own page is a
            shorter path than finding it in the tab bar -- which matters more now that the tab is
            no longer labelled "Profile".

            `replace`, not `push`, so it behaves EXACTLY as pressing the profile tab does. A
            `push` here would stack home underneath profile, and the two routes to the same screen
            would then leave the back gesture doing different things depending on which one the
            child happened to take.

            This file's header calls it a presentation component, and that is about NAME
            RESOLUTION -- it resolves no name of its own, and still does not. It already reads
            AdventureChargeProvider, so it is not markup-only. Navigating is hardcoded rather than
            taken as a prop because both callers (home and the game hub) want the same
            destination; a prop would be two call sites of ceremony for one behaviour. */}
        <Pressable
          accessibilityHint="Opens your profile"
          accessibilityLabel={`Hi, ${displayName}`}
          accessibilityRole="button"
          hitSlop={8}
          onPress={() => router.replace('/(learner)/profile')}
          style={({ pressed }) => [styles.greeting, pressed && styles.greetingPressed]}>
          <AppText style={[styles.greetingTitle, compact && styles.greetingTitleCompact]}>
            Hi,{' '}
            <AppText style={[styles.greetingName, compact && styles.greetingNameCompact]}>
              {displayName}!
            </AppText>
          </AppText>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  battery: { alignItems: 'center', flexDirection: 'row', height: 32 },
  batteryCell: { borderRadius: 2, flex: 1, height: '100%' },
  batteryCellEmpty: { backgroundColor: colors.surface2 },
  batteryCellFilled: { backgroundColor: colors.accentGreen },
  batteryCells: {
    borderColor: '#F4F4F6',
    borderRadius: radius.sm,
    borderWidth: 2,
    flexDirection: 'row',
    gap: 2,
    height: '100%',
    padding: 2,
    width: 58,
  },
  batteryCompact: { height: 26 },
  batteryNub: { backgroundColor: '#F4F4F6', borderRadius: 1, height: 12, width: 4 },
  brand: { alignItems: 'center', flexDirection: 'row', flexShrink: 1, gap: 3 },
  greeting: { alignItems: 'flex-end', flexShrink: 1, justifyContent: 'center' },
  greetingPressed: { opacity: 0.6 },
  greetingName: { color: '#26A5FD', fontFamily: typography.fonts.heavy, fontSize: 33.75, lineHeight: 40.5 },
  greetingNameCompact: { fontSize: 28.35, lineHeight: 33.75 },
  greetingTitle: { fontFamily: typography.fonts.body, fontSize: 25, lineHeight: 30 },
  greetingTitleCompact: { fontSize: 21, lineHeight: 25 },
  header: { alignItems: 'center', flexDirection: 'row', gap: 4 },
  headerGreetingSection: {
    backgroundColor: colors.background,
    flexShrink: 0,
    height: LEARNER_HEADER_HEIGHT,
    justifyContent: 'center',
    paddingHorizontal: spacing.smPlus,
    zIndex: 10,
  },
  headerSpacer: { flex: 1 },
  sectionCompact: { height: LEARNER_HEADER_HEIGHT_COMPACT },
});
