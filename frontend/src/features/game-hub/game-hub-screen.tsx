// The Play tab's landing screen: the eight Component C game families, laid out two-to-a-row inside
// one panel card.
//
// It is a MENU AND NOTHING MORE. It starts no session, holds no session state, reads no task,
// submits nothing, and computes no correctness -- every card is a navigation to
// `/(learner)/c-session`, which owns the whole loop exactly as it did before. Nothing in
// c-session-screen.tsx, c-session-logic.ts or archetype-surfaces.ts is touched or needs to be.
//
// VISUAL SOURCE. The container is home's "Your Session" panel and the cards inside it are that
// panel's stage cards, at half width (learner-home-screen.tsx's `pathPanel`, `pathStageNumber`,
// `pathStageCard`). The numbers below are that panel's numbers rather than new ones: panel radius
// `radius.lg` with a 3px `surface1` border and the 0/3/0.14/6 shadow; heading in `fonts.heavy`
// beside an accent icon; numbered circles `aspectRatio: 1`, pill radius, 3px `surface1` border and
// the 0/3/0.18/4 shadow; cards `radius.md`, 1px `border` and the 0/2/0.1/3 shadow.
//
// Two departures from home's rows, both forced by halving the width, both deliberate:
//   1. The circle sits INSIDE the card rather than overlapping its left edge. Home's `marginLeft:
//      -8` works because its rows have the path artwork to hang off; in a two-column grid the
//      overlap would collide with the neighbouring column's card.
//   2. The status word sits under the title rather than beside it, since half a row is not enough
//      width to keep both on one line without truncating the game's name.
//
// THIS SCREEN NEVER SCROLLS, structurally: it mounts no ScrollView, so nothing is capable of
// scrolling. The grid is four explicit rows, each `flex: 1` inside the panel, holding two `flex: 1`
// cards -- so a shorter viewport compresses every card evenly rather than pushing the last pair out
// of sight. Nothing is measured and no size is solved; flex already guarantees the fit. (A wrapping
// single row would NOT: wrapped rows in React Native do not stretch to share the container's
// height, which is exactly how a fourth row ends up clipped.)
//
// The per-game state is computed from the live surface table (game-catalogue.ts's `readinessOf`),
// never from a flag written down here, so it moves on its own as 10b..10h land. Today that means
// one Ready card and seven Coming soon ones -- and a Coming soon game is still tappable on purpose:
// it opens a session and renders the fail-closed frame, which is the behaviour section 2.2 of the
// build-steps doc calls "the design working". A hub that disabled those cards would hide the one
// path most worth being able to look at by hand.
//
// Grade note: C-GF-07 and C-GF-08 are the Grade-3 families, so their cards navigate with `grade=3`.
// That value comes from the catalogue entry, not from a literal here, and it is a preview
// affordance -- a real learner's grade comes from their classroom membership, which is still an
// open question the build-steps doc records under section 7 rather than one this screen settles.

import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { resolveArchetypeSurface } from '@/src/features/c-session/archetype-surfaces';
import {
  accentOf,
  listGameFamilies,
  readinessOf,
  sessionRouteFor,
  type GameFamilyEntry,
  type GameReadiness,
} from '@/src/features/game-hub/game-catalogue';
import { LearnerHeaderBar } from '@/src/features/navigation/learner-header-bar';
import { LearnerTabBar } from '@/src/features/navigation/learner-tab-bar';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';
import { firstNameOf } from '@/src/utils/display-name';

/** The panel's warm ground, standing in for home's path artwork so the white cards read as raised. */
const PANEL_BACKGROUND = '#fffdf6';
const CARDS_PER_ROW = 2;

const READINESS_SUBTITLE: Record<GameReadiness, string> = {
  playable: 'Ready to play',
  partial: 'Partly ready',
  'coming-soon': 'Coming soon',
};

/** Split the families into fixed rows of CARDS_PER_ROW, so each row can flex to an equal share of
 * the panel's height. Kept separate from the render for the same reason every other decision in
 * this feature is: it is checkable without a rendering library. */
function chunkIntoRows<T>(items: readonly T[], perRow: number): T[][] {
  const rows: T[][] = [];
  for (let index = 0; index < items.length; index += perRow) {
    rows.push(items.slice(index, index + perRow));
  }
  return rows;
}

/** Learner-facing menu of the eight Component C games. Fixed height, never scrollable. */
export function GameHubScreen() {
  const compact = useWindowDimensions().height < 760;
  const { me, profileName } = useAuth();
  // Resolved the same way home resolves it. The header itself takes a name rather than finding
  // one -- see learner-header-bar.tsx for why that is deliberate.
  const displayName = firstNameOf(me?.learnerProfile?.name.trim() || profileName || 'Math Explorer');

  const families = listGameFamilies();
  const rows = chunkIntoRows(families, CARDS_PER_ROW);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.mobileCanvas}>
        <LearnerHeaderBar compact={compact} displayName={displayName} />

        <View style={styles.panelArea}>
          <View style={styles.panel}>
            <View style={styles.panelHeading}>
              <Ionicons color={colors.accentGreen} name="game-controller" size={compact ? 22.5 : 27} />
              <AppText style={[styles.panelHeadingText, compact && styles.panelHeadingTextCompact]}>
                Your Games
              </AppText>
            </View>

            <View style={styles.grid}>
              {rows.map((row, rowIndex) => (
                <View key={rowIndex} style={styles.gridRow}>
                  {row.map((entry, columnIndex) => (
                    <GameCard
                      compact={compact}
                      entry={entry}
                      index={rowIndex * CARDS_PER_ROW + columnIndex}
                      key={entry.familyId}
                    />
                  ))}
                </View>
              ))}
            </View>
          </View>
        </View>

        <LearnerTabBar activeTab="play" playEnabled />
      </View>
    </SafeAreaView>
  );
}

function GameCard({
  compact,
  entry,
  index,
}: {
  compact: boolean;
  entry: GameFamilyEntry;
  index: number;
}) {
  // The live surface table, injected here rather than imported by the catalogue -- see that
  // module's header for why it must stay free of anything that reaches React Native.
  const readiness = readinessOf(entry, (archetypeId) => resolveArchetypeSurface(archetypeId) !== null);
  const isReady = readiness === 'playable';
  const accent = accentOf(entry);

  return (
    <Pressable
      accessibilityHint={
        isReady ? `Starts a ${entry.title} game` : `Opens ${entry.title}. This game is not finished yet.`
      }
      accessibilityLabel={`Game ${index + 1}, ${entry.title}. ${READINESS_SUBTITLE[readiness]}.`}
      accessibilityRole="button"
      onPress={() => router.push(sessionRouteFor(entry))}
      style={({ pressed }) => [styles.card, isReady && styles.cardActive, pressed && styles.cardPressed]}>
      <View
        style={[styles.cardNumber, { backgroundColor: accent }, isReady && styles.cardNumberActive]}>
        <AppText style={[styles.cardNumberText, compact && styles.cardNumberTextCompact]}>
          {index + 1}
        </AppText>
      </View>

      <View style={styles.cardCopy}>
        <AppText numberOfLines={2} style={[styles.cardTitle, compact && styles.cardTitleCompact]}>
          {entry.title}
        </AppText>
        <AppText
          numberOfLines={1}
          style={[
            styles.cardSubtitle,
            compact && styles.cardSubtitleCompact,
            isReady && { color: accent },
          ]}>
          {READINESS_SUBTITLE[readiness]}
        </AppText>
      </View>

      <Ionicons
        color={isReady ? colors.primary : accent}
        name={isReady ? 'play' : 'ellipse-outline'}
        size={isReady ? (compact ? 17.6 : 20.8) : compact ? 14 : 16.5}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    elevation: 2,
    flex: 1,
    flexDirection: 'row',
    gap: 7,
    minHeight: 0,
    paddingLeft: 7,
    paddingRight: 7,
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  cardActive: { borderColor: colors.primarySoft },
  cardCopy: { flex: 1, gap: 1, justifyContent: 'center', minWidth: 0 },
  cardNumber: {
    alignItems: 'center',
    aspectRatio: 1,
    borderColor: colors.surface1,
    borderRadius: radius.pill,
    borderWidth: 3,
    elevation: 4,
    height: '62%',
    justifyContent: 'center',
    maxHeight: 42,
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 4,
  },
  cardNumberActive: { borderColor: colors.accentYellow },
  cardNumberText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.display,
    fontSize: 15,
    lineHeight: 18,
  },
  cardNumberTextCompact: { fontSize: 12.5, lineHeight: 15 },
  cardPressed: { opacity: 0.86, transform: [{ scale: 0.985 }] },
  cardSubtitle: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: 8.5,
    lineHeight: 10.5,
  },
  cardSubtitleCompact: { fontSize: 7.5, lineHeight: 9.5 },
  cardTitle: { fontFamily: typography.fonts.heavy, fontSize: 12, lineHeight: 14.5 },
  cardTitleCompact: { fontSize: 10.5, lineHeight: 12.5 },
  grid: { flex: 1, gap: spacing.sm, minHeight: 0 },
  gridRow: { flex: 1, flexDirection: 'row', gap: spacing.sm, minHeight: 0 },
  mobileCanvas: {
    alignSelf: 'center',
    backgroundColor: colors.background,
    flex: 1,
    maxWidth: 500,
    width: '100%',
  },
  panel: {
    backgroundColor: PANEL_BACKGROUND,
    borderColor: colors.surface1,
    borderRadius: radius.lg,
    borderWidth: 3,
    elevation: 4,
    flex: 1,
    gap: spacing.sm,
    paddingBottom: spacing.smPlus,
    paddingHorizontal: spacing.smPlus,
    paddingTop: spacing.smPlus,
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.14,
    shadowRadius: 6,
  },
  panelArea: { flex: 1, paddingBottom: spacing.sm, paddingHorizontal: spacing.sm },
  panelHeading: { alignItems: 'center', flexDirection: 'row', flexShrink: 0, gap: 4 },
  panelHeadingText: { fontFamily: typography.fonts.heavy, fontSize: 18, lineHeight: 22.5 },
  panelHeadingTextCompact: { fontSize: 15, lineHeight: 18 },
  safeArea: { backgroundColor: colors.background, flex: 1 },
});
