import { useEffect, useMemo, useRef } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { Image } from 'expo-image';
import {
  ActivityIndicator,
  Animated,
  Easing,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { LearnerSkillStateItem } from '@/src/api/generated/openapi-types';
import { AppText } from '@/src/components/app-text';
import { artwork } from '@/src/utils/artwork';
import { applyDemoPrepBarOverrides } from '@/src/features/home/demo-prep-bar-overrides';
import { skillBarFills, type PrepCardSkillId } from '@/src/features/home/skill-bar-fill';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// Purpose-made prep-card artwork: a garden scene framing a cream parchment panel, at the exact
// portrait aspect ratio (941/1672) Home's "Ready to Play" path panel already uses.
const startGameArtwork = artwork.startGame;
const CARD_ASPECT_RATIO = 941 / 1672;
// Fraction of the card's height, from the top, before the artwork's own cream panel begins --
// content starts below this so it never sits on top of the sky/cloud band.
const ARTWORK_PANEL_TOP = 0.155;

// The seven skills, keyed by Component B's own `skill_id`s and drawn in PREP_CARD_SKILL_ORDER.
// Until 2026-09-21 the bars were a staged animation to fixed targets (62/48/55/71/44/37/29) -- a
// warm-up cue, not a report, because no B response exposed mastery. They are now sized from the
// learner's REAL BKT state (GET /api/v1/b/learner/skill-states) under the product-owner ruling
// that mastery may be shown to the child as bar length only: no number, no label, no
// accessibility value. The probability-to-width rule lives in skill-bar-fill.ts, not here.
const SKILL_ROWS: readonly { key: PrepCardSkillId; label: string; color: string }[] = [
  { key: 'counting', label: 'Counting', color: colors.primary },
  { key: 'number_sense', label: 'Number Sense', color: colors.accentBlue },
  { key: 'place_value', label: 'Place Value', color: colors.accentGreen },
  { key: 'addition', label: 'Addition', color: '#ffb51f' },
  { key: 'subtraction', label: 'Subtraction', color: '#9a64df' },
  { key: 'multiplication', label: 'Multiplication', color: colors.accentBlue },
  { key: 'division', label: 'Division', color: colors.accentGreen },
];

const ROW_ANIMATION_MS = 780;
const ROW_STAGGER_MS = 110;

type PlayPrepCardProps = {
  ready: boolean;
  /** The learner's per-skill BKT state, or null while it loads / if the read failed. Null draws
   * every bar empty; the card never waits on this, since it is decoration for the child, not a
   * precondition for playing. */
  skillStates: readonly LearnerSkillStateItem[] | null;
  onStart: () => void;
  onDismiss: () => void;
};

/**
 * The blurred-backdrop preparation card shown while a full-charge Play press loads Component C's
 * first task. Rendered once, globally, by AdventureChargeProvider. Frames itself like Home's
 * "Ready to Play" card (same artwork, aspect ratio, rounded border), sweeps the seven skill bars
 * top-to-bottom to each skill's real mastery length, then hands off to the game via the
 * hero-styled Start Game button once the background prefetch has settled.
 */
export function PlayPrepCard({ ready, skillStates, onStart, onDismiss }: PlayPrepCardProps) {
  const { height, width } = useWindowDimensions();
  const insets = useSafeAreaInsets();

  const rowProgress = useRef(SKILL_ROWS.map(() => new Animated.Value(0))).current;
  const cardIn = useRef(new Animated.Value(0)).current;
  // `applyDemoPrepBarOverrides` is TEMPORARY and `__DEV__`-only -- see
  // demo-prep-bar-overrides.ts. It is an identity function in any release build.
  const fills = useMemo(
    () => applyDemoPrepBarOverrides(skillBarFills(skillStates)),
    [skillStates],
  );

  // Card geometry: keep the exact portrait aspect ratio of Home's path panel, sized to whatever
  // fits between the safe-area insets, then capped so it never dominates a tall screen.
  const availableHeight = height - insets.top - insets.bottom - spacing.xl * 2;
  const availableWidth = Math.min(width - spacing.lg * 2, 380);
  let cardHeight = Math.min(availableHeight, 600);
  let cardWidth = cardHeight * CARD_ASPECT_RATIO;
  if (cardWidth > availableWidth) {
    cardWidth = availableWidth;
    cardHeight = cardWidth / CARD_ASPECT_RATIO;
  }

  // The card itself enters immediately -- it owns the wait, so it must appear on the same frame as
  // the Play press rather than after a round trip.
  useEffect(() => {
    Animated.timing(cardIn, {
      duration: 240,
      easing: Easing.out(Easing.quad),
      toValue: 1,
      useNativeDriver: true,
    }).start();
  }, [cardIn]);

  /**
   * THE BAR SWEEP WAITS FOR THE DATA. Fixed 2026-10-10: the bars used to pop into place instead of
   * sweeping.
   *
   * Both animations used to live in one mount-only effect, and `skillStates` is `null` at mount --
   * it arrives from `GET /b/learner/skill-states` a round trip later. So the stagger ran against
   * `fills` of all zeroes, animated every bar from 0% to 0%, and finished. When the response landed
   * `fills` changed, which rebuilt each interpolation with a new `outputRange` -- but `rowProgress`
   * was already sitting at 1, so every bar JUMPED straight to its final width. The sweep had
   * already been spent on nothing.
   *
   * Starting it when the data arrives is what makes the animation visible, and it is also what the
   * card is for: "Warming up your skills..." while the Component C prefetch runs behind it.
   *
   * `startedRef` keeps it single-shot, so a later re-render cannot restart a sweep mid-flight.
   * A `skillStates` that never arrives (the fetch failed, or the learner has no Component B
   * history) correctly animates nothing: every fill is 0, so there is no bar to draw and the card
   * shows empty tracks, which is the documented behaviour for that case.
   */
  const sweepStartedRef = useRef(false);
  useEffect(() => {
    if (skillStates === null || sweepStartedRef.current) return;
    sweepStartedRef.current = true;

    const sweep = Animated.stagger(
      ROW_STAGGER_MS,
      rowProgress.map((value) =>
        Animated.timing(value, {
          duration: ROW_ANIMATION_MS,
          easing: Easing.out(Easing.cubic),
          toValue: 1,
          // `false`, necessarily: the fill animates `width`, a LAYOUT property, and the native
          // driver only handles transforms and opacity. FE-003 tried to escape that by animating
          // `scaleX` instead and was reverted -- see the JSX comment on the bar for why.
          useNativeDriver: false,
        }),
      ),
    );
    sweep.start();
    // Stop on unmount: the card is dismissed by its own X and by "Start Game", either of which can
    // land mid-sweep, and a running animation writing into unmounted views is a leak.
    return () => sweep.stop();
  }, [rowProgress, skillStates]);

  const cardStyle = useMemo(
    () => ({
      height: cardHeight,
      opacity: cardIn,
      transform: [
        { scale: cardIn.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1] }) },
      ],
      width: cardWidth,
    }),
    [cardHeight, cardIn, cardWidth],
  );

  return (
    <View style={styles.overlay}>
      <BlurView intensity={40} style={StyleSheet.absoluteFill} tint="light" />
      <View style={styles.scrim} />

      <Animated.View style={[styles.card, cardStyle]}>
        <Image
          accessibilityLabel="A sunny garden framing your adventure"
          contentFit="cover"
          source={startGameArtwork}
          style={StyleSheet.absoluteFill}
        />
        <View style={[styles.cardInner, { paddingTop: cardHeight * ARTWORK_PANEL_TOP + spacing.sm }]}>
          <Pressable
            accessibilityLabel="Close"
            accessibilityRole="button"
            hitSlop={10}
            onPress={onDismiss}
            style={styles.closeButton}>
            <Ionicons color={colors.textSecondary} name="close" size={20} />
          </Pressable>

          <View style={styles.heading}>
            <Ionicons color={colors.accentGreen} name="map" size={22} />
            <AppText style={styles.headingText}>Ready to Play</AppText>
          </View>
          <AppText style={styles.subheading}>Warming up your skills…</AppText>

          <View style={styles.rows}>
            {SKILL_ROWS.map((skill, index) => (
              <View key={skill.key} style={styles.row}>
                <AppText numberOfLines={1} style={styles.rowLabel}>
                  {index + 1}. {skill.label}
                </AppText>
                {/* Decorative on purpose (`accessible={false}`, no progressbar role, no
                    accessibilityValue): the ruling is bar LENGTH only, and a screen reader
                    announcing "62 percent" would be exactly the number the child must not get. */}
                <View accessible={false} importantForAccessibility="no-hide-descendants" style={styles.track}>
                  {/* ANIMATED `width`, and it must stay that way.

                      FE-003 (2026-10-09) replaced this with an animated `scaleX` on a full-width
                      fill, to get the sweep off the JS thread -- `width` is a layout property, so
                      the native driver cannot drive it. REVERTED 2026-10-10: the bars rendered at
                      FULL length regardless of the learner's real mastery. Verified against the
                      live data behind the screenshot that exposed it -- five skills whose true
                      fills are 17, 17, 56, 17 and 17 all drew as complete bars, which is a false
                      statement about a child's progress, not a cosmetic glitch.

                      Two further reasons not to retry it as-written: the performance claim was
                      never measured (FE-003 was filed [UNVERIFIED] and no dropped frame was ever
                      observed here), and the owner's judgement was that the original animation
                      looked better. An unmeasured optimisation does not get to outrank a correct,
                      preferred animation.

                      If this is ever revisited, the thing to establish FIRST is why `scaleX`
                      landed at 1: `transformOrigin` support and the interaction with
                      `useNativeDriver` on this RN/RNW version are both unconfirmed. Do not
                      reintroduce it on the strength of the theory alone. */}
                  <Animated.View
                    style={[
                      styles.trackFill,
                      {
                        backgroundColor: skill.color,
                        width: rowProgress[index].interpolate({
                          inputRange: [0, 1],
                          outputRange: ['0%', `${fills[skill.key]}%`],
                        }),
                      },
                    ]}
                  />
                </View>
              </View>
            ))}
          </View>

          <Pressable
            accessibilityHint="Starts your prepared math game"
            accessibilityRole="button"
            accessibilityState={{ disabled: !ready }}
            disabled={!ready}
            onPress={onStart}
            style={({ pressed }) => [
              styles.startButton,
              !ready && styles.startButtonDisabled,
              pressed && styles.startButtonPressed,
            ]}>
            {ready ? (
              <>
                <AppText style={styles.startButtonText}>Start Game</AppText>
                <Ionicons color={colors.primaryForeground} name="chevron-forward" size={20} />
              </>
            ) : (
              <>
                <ActivityIndicator color={colors.primaryForeground} size="small" />
                <AppText style={styles.startButtonText}>Preparing…</AppText>
              </>
            )}
          </Pressable>
        </View>
      </Animated.View>
    </View>
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
  // The artwork itself paints the cream card panel this content sits on -- no white tint needed
  // here, only the padding (paddingTop is overridden inline to clear the panel's own top edge).
  cardInner: {
    flex: 1,
    gap: spacing.sm,
    paddingBottom: spacing.md,
    paddingHorizontal: spacing.md,
  },
  closeButton: {
    alignItems: 'center',
    height: 28,
    justifyContent: 'center',
    position: 'absolute',
    right: spacing.xs,
    top: spacing.xs,
    width: 28,
    zIndex: 2,
  },
  heading: { alignItems: 'center', flexDirection: 'row', gap: 6, justifyContent: 'center' },
  headingText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 18,
    lineHeight: 22.5,
  },
  overlay: {
    alignItems: 'center',
    bottom: 0,
    justifyContent: 'center',
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  // Label on the left, bar pinned to the right edge of the row -- not butted up against the
  // label -- via space-between rather than a gap.
  row: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  // No fixed width: `row`'s space-between already reserves the track's own 120px on the right,
  // so the label is free to size to its full text ("6. Multiplication" etc.) without truncating.
  rowLabel: {
    fontFamily: typography.fonts.bold,
    fontSize: 14,
    lineHeight: 18,
  },
  // The seven rows as one block, vertically centered in the space between the subheading and
  // the Start Game button.
  rows: { flex: 1, gap: spacing.mdPlus, justifyContent: 'center' },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(22,22,28,0.3)' },
  startButton: {
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
  startButtonDisabled: { opacity: 0.6 },
  startButtonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  startButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 13.64,
    lineHeight: 22.32,
    textAlign: 'center',
  },
  subheading: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: 12,
    lineHeight: 16,
    marginTop: -2,
    textAlign: 'center',
  },
  trackFill: { borderRadius: radius.pill, height: '100%' },
  track: {
    backgroundColor: colors.surface3,
    borderRadius: radius.pill,
    height: 16,
    overflow: 'hidden',
    width: 120,
  },
});
