import { useEffect, useMemo, useRef } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { Image } from 'expo-image';
import {
  Animated,
  Easing,
  Pressable,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/src/components/app-text';
import {
  formatDuration,
  totalDurationMs,
  type ChallengeRunResult,
} from '@/src/features/c-session/challenge-length';
import { artwork } from '@/src/utils/artwork';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The end of a fixed-length Component C run: the child chose "10 Game Challenge" and reached ten.
//
// IT IS THE PREP CARD, AT THE OTHER END OF THE RUN (owner request). Same garden artwork, same
// portrait ratio, same cream panel, same entrance. The child opens a run through that card and
// closes it through this one. What replaces the seven skill bars is the run itself: every game
// they played, in order, with a mark.
//
// WHY IT LISTS TIME AND NOT RIGHT-OR-WRONG -- read this before changing the column. Component C
// lets a child RETRY a wrong answer on the same task, and the session advances only once the
// answer matches. Every finished task is therefore eventually correct: a correct/incorrect column
// would be a tick on all ten, every run, for every child, and would carry no information at all.
// This was first built with ticks and crosses and that is exactly how it came out.
//
// Time is what actually varies. Each row runs from the question appearing to the answer being
// accepted, so the wrong attempts are INSIDE the number -- a question that took three goes shows
// as the time all three took. The total is summed from the rows, never timed separately.
//
// IT IS STILL EVALUATIVE, AND THAT IS STILL A REVERSAL. `resultsView` in live-session-logic.ts
// says a child is shown no score and that "a child who got everything wrong and a child who got
// everything right see the identical screen". A per-question time is softer than a tick, but it
// ranks the child's own questions against each other and invites comparison with other children.
// It is here by owner decision -- the second such reversal after the results-screen mastery bars
// (buildLog2.md, 2026-10-20) -- and is not licence for a third somewhere else.

const CARD_ASPECT_RATIO = 941 / 1672;
const ARTWORK_PANEL_TOP = 0.155;

type ChallengeCompleteScreenProps = {
  /** How many games the run was. Rendered as the child's own choice, never as a score. */
  taskCount: number;
  /** One row per game played, in play order. */
  results: readonly ChallengeRunResult[];
  onExit: () => void;
};

export function ChallengeCompleteScreen({ onExit, results, taskCount }: ChallengeCompleteScreenProps) {
  const { height, width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const cardIn = useRef(new Animated.Value(0)).current;

  const availableHeight = height - insets.top - insets.bottom - spacing.xl * 2;
  const availableWidth = Math.min(width - spacing.lg * 2, 380);
  let cardHeight = Math.min(availableHeight, 600);
  let cardWidth = cardHeight * CARD_ASPECT_RATIO;
  if (cardWidth > availableWidth) {
    cardWidth = availableWidth;
    cardHeight = cardWidth / CARD_ASPECT_RATIO;
  }

  useEffect(() => {
    Animated.timing(cardIn, {
      duration: 240,
      easing: Easing.out(Easing.quad),
      toValue: 1,
      useNativeDriver: true,
    }).start();
  }, [cardIn]);

  const cardStyle = useMemo(
    () => ({
      height: cardHeight,
      opacity: cardIn,
      transform: [{ scale: cardIn.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1] }) }],
      width: cardWidth,
    }),
    [cardHeight, cardIn, cardWidth],
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* The same blurred-garden ground the results screen uses, so a finished run lands on a
          backdrop rather than on flat white. */}
      <View pointerEvents="none" style={styles.backdrop}>
        <Image contentFit="cover" source={artwork.heroSection} style={styles.backdropHero} />
      </View>
      {/* Blurred, at the prep card's own intensity and tint, so the card in front reads as the
          thing in focus and the artwork behind it stays scenery. It is a sibling LAYER rather
          than a wrapper: the blur must sit over the backdrop and under the card, and a BlurView
          wrapping the card would blur the card itself. The scrim then sits on top of the blur,
          since blurring a flat wash would do nothing but cost a layer. */}
      <BlurView intensity={40} style={StyleSheet.absoluteFill} tint="light" />
      <View style={styles.scrim} />

      <View style={styles.centered}>
        <Animated.View style={[styles.card, cardStyle]}>
          <Image
            accessibilityLabel="A sunny garden framing your adventure"
            contentFit="cover"
            source={artwork.startGame}
            style={StyleSheet.absoluteFill}
          />
          <View style={[styles.cardInner, { paddingTop: cardHeight * ARTWORK_PANEL_TOP + spacing.sm }]}>
            <View style={styles.heading}>
              <Ionicons color={colors.accentGreen} name="trophy" size={22} style={styles.headingIcon} />
              <AppText style={styles.headingText}>Challenge complete!</AppText>
            </View>
            <AppText style={styles.subheading}>{`You played all ${taskCount} games.`}</AppText>

            {/* Scrollable, because ten rows on the shortest supported card is taller than the
                panel between the subheading and the button. The list is the content here -- it
                must not be clipped to whatever happens to fit. */}
            <ScrollView
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
              style={styles.list}>
              {results.map((result, index) => (
                <View key={`${index}-${result.name}`} style={styles.row}>
                  <AppText style={styles.rowIndex}>{`${index + 1}.`}</AppText>
                  <AppText numberOfLines={1} style={styles.rowName}>
                    {result.name}
                  </AppText>
                  <AppText style={styles.rowTime}>{formatDuration(result.ms)}</AppText>
                </View>
              ))}
            </ScrollView>

            {/* The total, summed from the rows above rather than timed separately, so the two can
                never disagree. Separated by a rule because it is a different KIND of number from
                the ten above it -- a sum, not another question. */}
            <View style={styles.totalRow}>
              {/* A frosted panel of its own, because this row sits over the artwork's garden band
                  where the cream panel has already ended -- dark text on leaves and flowers is
                  the one unreadable spot on the card.

                  BLUR *AND* A WHITE WASH, not blur alone. expo-blur couples tint strength to
                  intensity on web (the tint resolves to roughly intensity/100 * 0.30 alpha), so a
                  readable panel would need an intensity that blurs far too hard on native. The
                  explicit wash sets the legibility floor and the blur does the softening, which
                  keeps the two independent across platforms. */}
              <BlurView intensity={28} style={StyleSheet.absoluteFill} tint="light" />
              <View pointerEvents="none" style={styles.totalWash} />
              <AppText style={styles.totalLabel}>Total time</AppText>
              <AppText style={styles.totalValue}>{formatDuration(totalDurationMs(results))}</AppText>
            </View>

            <Pressable
              accessibilityRole="button"
              onPress={onExit}
              style={({ pressed }) => [styles.homeButton, pressed && styles.homeButtonPressed]}>
              <AppText style={styles.homeButtonText}>Back to Home</AppText>
              <Ionicons color={colors.primaryForeground} name="chevron-forward" size={20} />
            </Pressable>
          </View>
        </Animated.View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: colors.background },
  backdropHero: { height: '42%', width: '100%' },
  card: {
    borderRadius: radius.lg,
    elevation: 8,
    overflow: 'hidden',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.22,
    shadowRadius: 14,
  },
  cardInner: {
    flex: 1,
    gap: spacing.sm,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.md,
  },
  centered: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  heading: { alignItems: 'center', flexDirection: 'row', gap: 6, justifyContent: 'center' },
  headingIcon: { includeFontPadding: false, lineHeight: 22, textAlign: 'center' },
  headingText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 18,
    lineHeight: 22.5,
  },
  homeButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderColor: colors.surface1,
    borderRadius: 14.88,
    borderWidth: 2,
    elevation: 4,
    flexDirection: 'row',
    gap: 5,
    justifyContent: 'center',
    minHeight: 49.6,
    paddingHorizontal: 14.88,
    shadowColor: colors.primaryShadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
  },
  homeButtonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  homeButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 13.64,
    lineHeight: 22.32,
    textAlign: 'center',
  },
  // `marginTop` opens the gap between "You played all N games." and the first row, which read as
  // one block before. The list SCROLLS, so taller rows and a wider gap cost nothing -- they push
  // rows below the fold rather than off the card.
  list: { flex: 1, marginTop: spacing.sm },
  listContent: { gap: 10, paddingBottom: spacing.xs },
  row: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  rowIndex: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: 15,
    lineHeight: 21,
    minWidth: 24,
  },
  rowTime: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.bold,
    fontSize: 15,
    lineHeight: 21,
    // Fixed width so every time sits in the same column and the list reads as one, rather than
    // ragged against names of different lengths.
    minWidth: 38,
    textAlign: 'right',
  },
  rowName: {
    flex: 1,
    fontFamily: typography.fonts.bold,
    fontSize: 15,
    lineHeight: 21,
  },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  totalLabel: {
    flex: 1,
    fontFamily: typography.fonts.heavy,
    fontSize: 15,
    lineHeight: 21,
  },
  // Its own rounded, frosted strip. The top rule it used to carry is gone: a hairline made sense
  // when the row sat on the cream panel and needed separating from the list, but on a panel of
  // its own it was just a line floating across the garden.
  totalRow: {
    alignItems: 'center',
    borderRadius: radius.md,
    flexDirection: 'row',
    marginBottom: spacing.sm,
    marginTop: spacing.xs,
    overflow: 'hidden',
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  totalWash: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(255,255,255,0.72)' },
  totalValue: {
    fontFamily: typography.fonts.heavy,
    fontSize: 16,
    lineHeight: 21,
    minWidth: 38,
    textAlign: 'right',
  },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(22,22,28,0.3)' },
  subheading: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: 12,
    lineHeight: 16,
    marginTop: -2,
    textAlign: 'center',
  },
});
