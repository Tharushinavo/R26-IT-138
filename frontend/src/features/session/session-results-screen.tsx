import { useEffect, useMemo, useRef } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { Image } from 'expo-image';
import { Animated, Easing, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/src/components/app-text';
import { resultsView, type SessionProgress } from '@/src/features/session/live-session-logic';
import { SessionMasteryBars } from '@/src/features/session/session-mastery-bars';
import type { SkillBarChange } from '@/src/features/session/session-mastery-change';
import { artwork } from '@/src/utils/artwork';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// FE-3f -- the end of a session.
//
// IT IS THE PREP CARD, AT THE OTHER END OF THE SESSION (owner request, 2026-10-20). Same garden
// artwork, same portrait aspect ratio, same cream panel, same seven rows, same hero button. The
// child opens a session through that card and closes it through this one, so the two read as one
// object rather than two screens that happen to list the same skills. Only the words and the
// bar behaviour differ: "Ready to Play / Warming up your skills..." becomes the completion
// headline and the question count, and Start Game becomes Play Again.
//
// There is still no score, no percentage, no stars and no "you got 3 right". None of that is
// missing; all of it is excluded.
//
// PER-SKILL MASTERY BARS ARE THE ONE EXCEPTION, added 2026-10-20 by owner decision, reversing this
// file's original "no per-skill breakdown, no mastery figure" rule. They are drawn from the
// server's own `p_l` values (GET /b/learner/skill-states), never from responses this client saw,
// and they print no number -- the bar's length is the whole message. A skill that moved sweeps at
// full colour; a skill that did not is dulled and still (see session-mastery-bars.tsx). The two
// known costs are recorded in buildLog2.md: the BKT parameters driving those bars are
// TEST_FIXTURE_ONLY, and a child who did not progress watches every bar stay still.
//
// The client does observe every `response_matched` as a session runs, and it must never accumulate
// them into a score or any other derived summary: the backend deliberately withholds an evaluative
// summary from the child-facing surface, so a client that assembled one out of responses it
// happened to see would be synthesising precisely the thing that was withheld -- a governance
// violation wearing the costume of a helpful UI feature. The full reasoning, and the test that
// locks the COPY to be identical for every outcome, live on `resultsView` in live-session-logic.ts.
//
// The counts come from the completion response the session screen already holds. `GET /summary` is
// not called: it would add a round trip for numbers already in hand, and would import that
// endpoint's abandoned/expired/technical_failed-all-report-as-"active" behaviour
// (session_completion.py:550) for no benefit.
//
// Results are not deep-linkable and do not survive a reload. That is deliberate, not a gap -- the
// app keeps no learner-facing record of performance, so there is nothing to return to. A child who
// reopens the app lands on preparation and starts fresh.

// Geometry copied from play-prep-card.tsx, deliberately and exactly: the artwork is authored at
// this ratio, and the cream panel it paints starts this far down. Both are load-bearing -- a
// different ratio crops the garden, a different top inset drops the heading onto the sky.
const CARD_ASPECT_RATIO = 941 / 1672;
const ARTWORK_PANEL_TOP = 0.155;

type SessionResultsScreenProps = {
  progress: SessionProgress;
  onExit: () => void;
  /** Start another session. */
  onPlayAgain: () => void;
  /** Empty until the current skill states arrive; the bars animate when it fills. */
  changes: readonly SkillBarChange[];
};

export function SessionResultsScreen({ changes, onExit, onPlayAgain, progress }: SessionResultsScreenProps) {
  const view = resultsView(progress);
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
      {/* THE SAME BACKDROP THE PREP CARD HAS (owner request): the child's own home screen, blurred,
          with the prep card's exact BlurView intensity/tint and scrim. The card then reads as
          something that opened ON TOP of home rather than as a separate place they were taken to.

          It is built from home's OWN artwork (`heroSection` + `learningPath`), not from a live
          `LearnerHomeScreen` mounted behind this one. Rendering the real screen here would fire its
          profile, classroom and skill-state fetches a second time just to be blurred out of
          legibility, and would put a second copy of an interactive screen in the tree. Both images
          are already preloaded at splash, so this costs nothing to draw.

          If a LIVE home is ever wanted behind it, the way to get it is the navigator, not this
          file: present the session route as a transparent modal so the real home stays mounted
          underneath. That changes the route's presentation for every phase, not just this one, so
          it was not done on the way past. */}
      <View pointerEvents="none" style={styles.backdrop}>
        <Image contentFit="cover" source={artwork.heroSection} style={styles.backdropHero} />
        <Image contentFit="cover" source={artwork.learningPath} style={styles.backdropPath} />
      </View>
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
              <Ionicons color={colors.accentGreen} name="ribbon" size={22} />
              <AppText style={styles.headingText}>{view.headline}</AppText>
            </View>
            <AppText style={styles.subheading}>{view.detail}</AppText>

            <View style={styles.rowsWrap}>
              <SessionMasteryBars changes={changes} />
            </View>

            <Pressable
              accessibilityHint="Starts another math game"
              accessibilityRole="button"
              onPress={onPlayAgain}
              style={({ pressed }) => [styles.playButton, pressed && styles.playButtonPressed]}>
              <AppText style={styles.playButtonText}>Play Again</AppText>
              <Ionicons color={colors.primaryForeground} name="chevron-forward" size={20} />
            </Pressable>
          </View>
        </Animated.View>
      </View>

      {/* Home as an ICON (owner request), so the hero action is PLAY AGAIN -- leaving is always one
          tap away but is no longer the thing being offered.

          ON THE SCREEN, NOT ON THE CARD. It used to sit in the card's own top-left, which put it on
          top of the artwork's sky: a dark glyph on a mid-blue photo, with no chip behind it, at the
          one size the prep card uses for its close button. Out here it has the blurred backdrop
          behind it instead, so it gets a surface chip and a larger target -- and it stops competing
          with the card's heading for the same corner.

          Rendered last so it paints above the card, and anchored to the safe-area inset rather than
          a fixed offset, so it clears a notch or a rounded corner on a real device. */}
      <Pressable
        accessibilityLabel="Back to home"
        accessibilityRole="button"
        hitSlop={12}
        onPress={onExit}
        style={({ pressed }) => [
          styles.homeButton,
          { left: insets.left + spacing.md, top: insets.top + spacing.md },
          pressed && styles.pressed,
        ]}>
        <Ionicons color={colors.textSecondary} name="home" size={26} style={styles.homeIcon} />
      </Pressable>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.lg,
    elevation: 8,
    overflow: 'hidden',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.22,
    shadowRadius: 14,
  },
  // The artwork itself paints the cream panel this content sits on -- no tint needed here, only
  // the padding (paddingTop is overridden inline to clear the panel's own top edge).
  cardInner: {
    flex: 1,
    gap: spacing.sm,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.md,
  },
  // Home's two big images stacked the way home stacks them, so the blur has the right shapes and
  // colours underneath it rather than a flat wash.
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: colors.background },
  backdropHero: { height: '42%', width: '100%' },
  backdropPath: { height: '38%', marginTop: '4%', width: '100%' },
  centered: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  heading: { alignItems: 'center', flexDirection: 'row', gap: 6, justifyContent: 'center' },
  headingText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 18,
    lineHeight: 22.5,
  },
  // An icon font renders as TEXT, so the glyph sits inside a line box with the font's own leading
  // above it and its descender space below -- which pushes it off the optical centre of a circle
  // that is itself perfectly centred. Pinning lineHeight to the glyph size collapses that extra
  // space, and dropping the Android font padding removes the rest. Without this the house sits
  // visibly low and left of middle.
  homeIcon: { includeFontPadding: false, lineHeight: 26, textAlign: 'center' },
  // A proper tap target against the blurred backdrop: a surface chip, bordered so it stays legible
  // over whichever part of the artwork happens to sit behind it. 48pt square, comfortably past the
  // 44pt minimum, with hitSlop on top of that.
  homeButton: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    elevation: 3,
    height: 48,
    justifyContent: 'center',
    position: 'absolute',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.18,
    shadowRadius: 5,
    width: 48,
    zIndex: 3,
  },
  playButton: {
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
  playButtonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  playButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 13.64,
    lineHeight: 22.32,
    textAlign: 'center',
  },
  pressed: { opacity: 0.6 },
  // The seven rows as one block, vertically centred between the subheading and the hero button --
  // the prep card's own `rows: { flex: 1, justifyContent: 'center' }`, kept here so the bars sit
  // at the same height on both cards.
  rowsWrap: { flex: 1, justifyContent: 'center' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
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
