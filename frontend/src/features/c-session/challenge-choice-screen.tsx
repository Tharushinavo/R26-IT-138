import { useEffect, useRef, useState } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { Animated, Easing, Pressable, ScrollView, StyleSheet, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppText } from '@/src/components/app-text';
import {
  CHALLENGE_TASK_COUNT,
  DEFAULT_CHALLENGE_LENGTH,
  type ChallengeLength,
} from '@/src/features/c-session/challenge-length';
import { artwork } from '@/src/utils/artwork';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// "How long do you want to play?" -- the step between the Play prep card and a Component C game.
//
// INSPIRED BY COMPONENT B'S PREPARATION SCREEN, NOT COPIED FROM IT (owner request). What is taken
// from it is the shape of the moment: a full screen, a warm greeting line, a hero, then one
// obvious way forward. What is deliberately different is everything that carries meaning -- B's
// screen REPORTS (a named skill, a classroom, a lesson chip, a readiness state the child cannot
// influence), and this screen ASKS. So the hero is a question rather than a status, the body is
// two cards the child chooses between rather than panels they read, and the primary button says
// what was chosen rather than "Start".
//
// WHY A SCREEN AND NOT TWO BUTTONS ON THE PREP CARD. The prep card is a small overlay whose job is
// already taken: it shows mastery and covers the prefetch. Two run lengths need room to be
// explained -- a seven-year-old picking "endless" should be able to see what that means before
// they pick it, not infer it from a word.
//
// NOTHING HERE STARTS A SESSION. The session was already created by the prep card's background
// prefetch; this screen only carries a choice forward as a route param. That is why leaving it
// costs nothing and why it has no loading state of its own.

type ChallengeChoiceScreenProps = {
  /** Begin the run at the chosen length. */
  onStart: (length: ChallengeLength) => void;
};

// NO BACK CONTROL, by owner request. The consequence is worth stating plainly: once this screen is
// open, choosing a length is the only way off it -- there is no tab bar here and the route arrived
// by `replace`, so the stack has nothing to pop. A child who opened it by accident must start a run
// and then leave from the game. The web back gesture still works; a device back button does not
// have anywhere to go.

type OptionSpec = {
  value: ChallengeLength;
  /** A real emoji character, not an icon-font name. Sized against the tile in `optionEmoji`
   * below, on the same 0.72/0.9 ratio object-quantity-display.tsx already uses for its glyphs. */
  emoji: string;
  title: string;
  blurb: string;
  accent: string;
  tint: string;
};

// The two options, written for a child. The blurbs answer the question the title raises -- "and
// then what?" -- because "endless" means nothing to a seven-year-old without it.
const OPTIONS: readonly OptionSpec[] = [
  {
    accent: colors.primary,
    // Says what the run actually does, because the card at the end shows times and a child who
    // was not told they were being timed would meet that as a surprise verdict.
    // Says what is actually measured. "See how you did" would read to a child as right-and-wrong,
    // and that is the one thing this run cannot tell them: a C task is retried until it is
    // correct, so every finished game was got right in the end. Time is what varies, so time is
    // what the instruction promises.
    blurb: `Play ${CHALLENGE_TASK_COUNT} games. We time each one and show your times at the end.`,
    // A finish line: this run has an end, and that is the whole difference between the two.
    emoji: '🏁',
    tint: '#ffeceb',
    title: `${CHALLENGE_TASK_COUNT} Game Challenge`,
    value: 'challenge',
  },
  {
    accent: colors.accentGreen,
    blurb: 'Keep playing for as long as you like. Stop whenever you want.',
    emoji: '♾️',
    tint: '#e9f8f1',
    title: 'Keep Playing',
    value: 'endless',
  },
];

export function ChallengeChoiceScreen({ onStart }: ChallengeChoiceScreenProps) {
  // The same breakpoint Component B's preparation screen uses, so the wordmark steps down at the
  // same viewport height on both screens rather than at one this file invented.
  const compact = useWindowDimensions().height < 760;
  // Pre-selected rather than empty, so the primary button is never disabled and a child who just
  // wants to play can press straight through. The default is the shorter run: a child who did not
  // read the options gets a game with an ending, not one that never stops.
  const [selected, setSelected] = useState<ChallengeLength>('challenge');
  const enter = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(enter, {
      duration: 260,
      easing: Easing.out(Easing.quad),
      toValue: 1,
      useNativeDriver: true,
    }).start();
  }, [enter]);

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* The Component C task card's own doodle pattern, now the ground the whole choice is made
          on -- so a choice about a C game is made on the surface that game is played on. It is
          `cover` on a 1:2 portrait, which fits a phone screen far better than it fitted a wide
          card, and the motifs are scattered rather than composed so no crop loses a subject.

          Behind everything and inert: decoration, hidden from screen readers, and never a
          precondition for the screen rendering -- the background colour underneath is what shows
          if the image fails. */}
      <Image
        accessibilityElementsHidden
        contentFit="cover"
        importantForAccessibility="no-hide-descendants"
        pointerEvents="none"
        source={artwork.cTaskBackground}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.canvas}>
        {/* The wordmark exactly as Component B's preparation screen draws it (owner request):
            same artwork, same 1916/821 ratio, same 68/56 heights, same left alignment. Sized by
            HEIGHT with the ratio doing the rest, never by a width/height pair -- artwork.ts
            records that these ratios are hardcoded in nine places and that a resize would
            silently break every one of them. */}
        <View style={[styles.topBar, compact && styles.topBarCompact]}>
          <Image
            accessibilityLabel="MathMingo"
            contentFit="contain"
            source={artwork.mathmingoHeader}
            style={[styles.brand, compact && styles.brandCompact]}
          />
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          style={styles.scroll}>
          <Animated.View
            style={[
              styles.body,
              {
                opacity: enter,
                transform: [{ translateY: enter.interpolate({ inputRange: [0, 1], outputRange: [14, 0] }) }],
              },
            ]}>
            {/* THE MASCOT ASKS THE QUESTION. `hero-section.webp` is the same artwork home opens
                with, so the child meets the same flamingo here; the bubble sits in the open sky
                and meadow on its LEFT, which is the only part of the image with nothing in it --
                the bird occupies roughly the right 40%, and anything placed there would cover its
                face.

                WHY THE QUESTION MOVED INTO THE BUBBLE rather than being repeated above the
                options. The screen asked it once as a plain heading already; printing it twice
                would be the same sentence competing with itself. Putting it in the bubble makes
                the ask friendly without adding a word, which is what this screen was missing. */}
            <View style={styles.hero}>
              <Image
                accessibilityLabel="Your flamingo friend, ready for an adventure"
                contentFit="cover"
                source={artwork.heroSection}
                style={StyleSheet.absoluteFill}
              />
              <View style={styles.bubble}>
                <AppText style={styles.bubbleGreeting}>Hi there!</AppText>
                <AppText style={styles.bubbleText}>How long do you want to play?</AppText>
                {/* The tail, pointing at the bird so the words read as HERS. A rotated square
                    rather than an SVG or a second image: it is the same fill as the bubble, so
                    the seam between them is invisible and there is nothing extra to load. */}
                <View style={styles.bubbleTail} />
              </View>
            </View>

            <View style={styles.options}>
              {OPTIONS.map((option) => {
                const isSelected = option.value === selected;
                return (
                  <Pressable
                    accessibilityRole="radio"
                    accessibilityState={{ checked: isSelected }}
                    key={option.value}
                    onPress={() => setSelected(option.value)}
                    style={({ pressed }) => [
                      styles.option,
                      isSelected && { borderColor: option.accent, borderWidth: 2.5 },
                      pressed && styles.optionPressed,
                    ]}>
                    <View style={[styles.optionIcon, { backgroundColor: option.tint }]}>
                      {/* A real emoji CHARACTER rather than an icon font, following the same
                          decision object-pool.tsx and object-quantity-display.tsx already made
                          for the countable objects. It is decoration: the option's title says
                          what this is, so announcing the glyph as well would read it twice. */}
                      <AppText accessibilityElementsHidden style={styles.optionEmoji}>
                        {option.emoji}
                      </AppText>
                    </View>
                    <View style={styles.optionText}>
                      <AppText style={styles.optionTitle}>{option.title}</AppText>
                      <AppText style={styles.optionBlurb}>{option.blurb}</AppText>
                    </View>
                    {/* The tick is the ONLY selected-state cue that does not rely on colour, which
                        matters on a screen whose two options are told apart by colour otherwise. */}
                    <View
                      style={[
                        styles.radio,
                        isSelected && { backgroundColor: option.accent, borderColor: option.accent },
                      ]}>
                      {isSelected ? (
                        <Ionicons
                          color={colors.primaryForeground}
                          name="checkmark"
                          size={15}
                          style={styles.radioGlyph}
                        />
                      ) : null}
                    </View>
                  </Pressable>
                );
              })}
            </View>
          </Animated.View>
        </ScrollView>

        <View style={styles.footer}>
          <Pressable
            accessibilityHint="Starts your game at the length you picked"
            accessibilityRole="button"
            onPress={() => onStart(selected)}
            style={({ pressed }) => [styles.startButton, pressed && styles.startButtonPressed]}>
            <AppText style={styles.startButtonText}>
              {selected === 'challenge' ? `Start ${CHALLENGE_TASK_COUNT} Games` : 'Start Playing'}
            </AppText>
            <Ionicons color={colors.primaryForeground} name="chevron-forward" size={22} />
          </Pressable>
        </View>
      </View>
    </SafeAreaView>
  );
}

/** Exported for the route, so a deep link with no choice still has one. */
export const FALLBACK_CHALLENGE_LENGTH = DEFAULT_CHALLENGE_LENGTH;

const styles = StyleSheet.create({
  // The hero and the options SHARE the height between the wordmark and the Start button, rather
  // than stacking at the top and leaving the rest empty. `space-evenly` is what lowers the image:
  // it puts an equal share of the leftover height above the hero, between the hero and the
  // options, and below the options -- so the screen fills itself at whatever height it is given
  // instead of needing a hand-tuned margin per device.
  //
  // The gap BETWEEN the two option cards is not part of this: that is `options.gap`, set on their
  // own container, so redistributing the outer space cannot open or close it.
  body: { flex: 1, justifyContent: 'space-evenly' },
  brand: { aspectRatio: 1916 / 821, height: 68 },
  brandCompact: { height: 56 },
  canvas: { alignSelf: 'center', flex: 1, maxWidth: 500, width: '100%' },
  footer: { paddingBottom: spacing.lg, paddingHorizontal: spacing.lg, paddingTop: spacing.sm },
  bubble: {
    backgroundColor: 'rgba(255,255,255,0.94)',
    borderRadius: radius.lg,
    elevation: 3,
    left: '5%',
    maxWidth: 230,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    position: 'absolute',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    top: '18%',
    width: '52%',
  },
  bubbleGreeting: {
    // The same orange Component B's preparation screen gives "Get Ready" (`heroReady`), so the
    // two prep moments greet the child in one voice. Written as the literal rather than pulled
    // from the theme because that screen holds it as a literal too -- there is no token for it,
    // and inventing one here would leave B's copy unconverted and the pair still split.
    color: '#ffb000',
    fontFamily: typography.fonts.heavy,
    fontSize: 13,
    lineHeight: 17,
  },
  bubbleText: {
    fontFamily: typography.fonts.heavy,
    fontSize: 17,
    lineHeight: 22,
  },
  // Square, rotated 45 degrees, half of it tucked behind the bubble's right edge.
  bubbleTail: {
    backgroundColor: 'rgba(255,255,255,0.94)',
    bottom: 14,
    height: 16,
    position: 'absolute',
    right: -6,
    transform: [{ rotate: '45deg' }],
    width: 16,
  },
  hero: {
    aspectRatio: 1672 / 941,
    backgroundColor: colors.secondarySoft,
    borderRadius: radius.lg,
    overflow: 'hidden',
    width: '100%',
  },
  option: {
    alignItems: 'center',
    // Solid again. The doodle pattern moved OUT of these cards and onto the screen behind them
    // (owner request): cropped into a card this wide it was a 1:2 portrait zoomed hard, and two
    // patterned cards on a plain ground read as busier than one patterned ground with two clean
    // cards on it. The cards now sit ON the pattern instead of each carrying their own copy.
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1.5,
    elevation: 2,
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.md,
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 5,
  },
  optionBlurb: {
    color: colors.textSecondary,
    fontFamily: typography.fonts.body,
    fontSize: 13,
    lineHeight: 18,
  },
  optionIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 52,
    justifyContent: 'center',
    width: 52,
  },
  // 0.72 and 0.9 of the 52pt tile, the ratio object-quantity-display.tsx settled on for emoji in
  // a fixed box. An emoji's ink sits well inside its em square, so matching the icon font's old
  // `size={26}` literally would have drawn a visibly SMALLER mark than the icons it replaced.
  optionEmoji: { fontSize: 37, includeFontPadding: false, lineHeight: 47, textAlign: 'center' },
  optionPressed: { opacity: 0.9, transform: [{ scale: 0.99 }] },
  optionText: { flex: 1, gap: 3 },
  optionTitle: {
    fontFamily: typography.fonts.heavy,
    fontSize: 16,
    lineHeight: 20,
  },
  // `gap` is UNCHANGED and deliberately so -- it is the spacing between the two cards the owner
  // asked to keep. The `marginTop` that used to sit here is gone: it was pushing the block down
  // from the hero, which is now `body`'s even distribution's job, and leaving both in would have
  // stacked one offset on top of the other.
  options: { gap: spacing.md },
  pressed: { opacity: 0.6 },
  radio: {
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 2,
    height: 24,
    justifyContent: 'center',
    width: 24,
  },
  radioGlyph: { includeFontPadding: false, lineHeight: 15, textAlign: 'center' },
  safeArea: { backgroundColor: colors.background, flex: 1 },
  scroll: { flex: 1 },
  // `flexGrow: 1` is what gives the body a height to distribute: without it the content container
  // is only as tall as its children, `flex: 1` on the body resolves to nothing, and the screen
  // stacks at the top with the leftover height sitting empty underneath.
  scrollContent: { flexGrow: 1, padding: spacing.lg, paddingTop: spacing.md },
  startButton: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderColor: colors.surface1,
    borderRadius: 16,
    borderWidth: 2,
    elevation: 4,
    flexDirection: 'row',
    gap: 6,
    justifyContent: 'center',
    minHeight: 56,
    paddingHorizontal: spacing.lg,
    shadowColor: colors.primaryShadow,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
  },
  startButtonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  startButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 16,
    letterSpacing: typography.letterSpacing.button,
  },
  topBar: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    paddingBottom: spacing.sm,
    paddingHorizontal: spacing.smPlus,
    paddingTop: 4,
  },
  topBarCompact: { paddingBottom: spacing.xs },
});
