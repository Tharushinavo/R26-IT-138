import { useEffect, useMemo, useRef } from 'react';
import { LinearGradient } from 'expo-linear-gradient';
import { Animated, Easing, StyleSheet, View } from 'react-native';

import { AppText } from '@/src/components/app-text';
import type { PrepCardSkillId } from '@/src/features/home/skill-bar-fill';
import type { SkillBarChange } from '@/src/features/session/session-mastery-change';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The seven skill bars on the results screen (owner decision, 2026-10-20).
//
// WHAT THIS SCREEN'S BARS SAY THAT THE PREP CARD'S DO NOT. The prep card sweeps every bar from
// zero to the learner's current mastery -- it is a warm-up cue, and every row moves because every
// row is being introduced. Here the question is different: WHAT CHANGED THIS SESSION. So the two
// kinds of row are drawn differently, and the difference is the whole message:
//
//   * A skill whose BKT value went UP draws at full colour and SWEEPS from where it started to
//     where it now is. The motion is the report.
//   * A skill that did not move draws DULLED and perfectly still. It is still present -- a child
//     should see all seven skills, not a list that changes length -- but it is visibly not the
//     thing that happened.
//
// Rows, track geometry and label styling are reproduced from `home/play-prep-card.tsx` so the two
// screens look like one product. The ORDER and the probability-to-width rule are NOT copied: both
// come through session-mastery-change.ts from skill-bar-fill.ts, so the two screens can never
// disagree about how long a given bar is.
//
// Labels and colours match the prep card's own SKILL_ROWS, following this codebase's standing
// convention of copying shapes between screens rather than exporting a private symbol.
const SKILL_ROWS: readonly { key: PrepCardSkillId; label: string; color: string }[] = [
  { key: 'counting', label: 'Counting', color: colors.primary },
  { key: 'number_sense', label: 'Number Sense', color: colors.accentBlue },
  { key: 'place_value', label: 'Place Value', color: colors.accentGreen },
  { key: 'addition', label: 'Addition', color: '#ffb51f' },
  { key: 'subtraction', label: 'Subtraction', color: '#9a64df' },
  { key: 'multiplication', label: 'Multiplication', color: colors.accentBlue },
  { key: 'division', label: 'Division', color: colors.accentGreen },
];

/** The track's fixed width, in points. The shimmer travels across exactly this distance. */
const TRACK_WIDTH = 120;
const ROW_ANIMATION_MS = 780;
const ROW_STAGGER_MS = 110;
/** Let the screen settle before anything moves, so the growth is seen rather than missed. */
const START_DELAY_MS = 380;
/** How faint a skill that did not move is drawn. Present, readable, plainly not the news. */
const UNCHANGED_OPACITY = 0.3;
/** The travelling highlight on a bar that moved: how wide, how long it takes, and the rest between
 * passes. The gap is deliberately longer than the sweep -- this is a cue, not a strobe.
 *
 * WIDE AND SOFT, not narrow and bright. The highlight is a gradient that fades to nothing at both
 * edges (see `styles.shimmer`'s sibling below), and a fade needs room: at 34pt the falloff was
 * compressed into so few pixels that it read as a hard-edged block sliding along the bar, which is
 * what the angle was meant to disguise rather than cause. */
const SHIMMER_WIDTH = 52;
/** Transparent at both edges, brightest in the middle -- so the highlight has no edge to see. The
 * peak is well below full white: on a pale bar (the dulled rows' palette, or Addition's yellow) a
 * stronger centre washes the colour out instead of passing over it. */
const SHIMMER_COLORS = ['rgba(255,255,255,0)', 'rgba(255,255,255,0.5)', 'rgba(255,255,255,0)'] as const;
const SHIMMER_LOCATIONS = [0, 0.5, 1] as const;
/** THE SAME SPEED AS THE PREP CARD'S BARS (owner request): the card the Play button opens sweeps
 * its bars over `ROW_ANIMATION_MS`, and the highlight here travels over exactly that, on the same
 * easing curve. Derived from the constant rather than copied as a number, so the two surfaces
 * cannot drift apart if that timing is ever retuned. */
const SHIMMER_MS = ROW_ANIMATION_MS;
const SHIMMER_GAP_MS = 1500;

export function SessionMasteryBars({ changes }: { changes: readonly SkillBarChange[] }) {
  // One driver per row, each 0 -> 1, interpolated into a width between `before` and `after`. A row
  // that did not improve is never started, so its driver stays at 0 -- and since its `before` and
  // `after` are equal, staying at 0 is exactly "draw it at its current width and hold still".
  const drivers = useRef(SKILL_ROWS.map(() => new Animated.Value(0))).current;
  // A second driver per row for the travelling highlight. Separate from `drivers` because the two
  // animations answer to different rules: the width sweep runs once and stops, the shimmer repeats
  // for as long as the screen is open.
  const shimmers = useRef(SKILL_ROWS.map(() => new Animated.Value(0))).current;

  const bySkill = useMemo(
    () => new Map(changes.map((change) => [change.skillId, change])),
    [changes],
  );

  useEffect(() => {
    // The dependency is the CHANGES, not the mount: this screen fetches its "after" values, so the
    // first render has nothing to grow toward. Animating on mount would sweep every bar from its
    // start to its start -- invisible -- and then snap when the data arrived, which is the exact
    // bug play-prep-card.tsx records in its own sweep effect.
    if (changes.length === 0) return;

    // ONLY THE ROWS THAT MOVED ARE ANIMATED, and the stagger is counted over those rows alone. If
    // the only improvement is the seventh skill, the child should not sit through six empty beats
    // waiting for the one bar that has something to say.
    const moving = SKILL_ROWS.map((row, index) => ({ driver: drivers[index], key: row.key }))
      .filter((row) => bySkill.get(row.key)?.improved === true)
      .map((row) =>
        Animated.timing(row.driver, {
          duration: ROW_ANIMATION_MS,
          easing: Easing.out(Easing.cubic),
          toValue: 1,
          // `false`, necessarily: the fill animates `width`, a LAYOUT property, and the native
          // driver handles only transforms and opacity. The prep card carries the full history of
          // why animating `scaleX` instead is NOT a safe substitute here -- it drew every bar at
          // full length, which is a false statement about a child's progress.
          useNativeDriver: false,
        }),
      );
    if (moving.length === 0) return;

    const sweep = Animated.stagger(ROW_STAGGER_MS, moving);
    const timer = setTimeout(() => sweep.start(), START_DELAY_MS);
    // Stop on unmount: Home and Play Again can both be pressed mid-sweep, and a running animation
    // writing into unmounted views is a leak.
    return () => {
      clearTimeout(timer);
      sweep.stop();
    };
  }, [bySkill, changes, drivers]);

  // THE SHIMMER IS THE CUE THAT ACTUALLY LANDS, and it exists because the sweep often cannot.
  //
  // `improved` is decided on the BKT probability, not the drawn width (see session-mastery-change
  // .ts). Under TEST_FIXTURE_ONLY parameters `p_l` saturates toward 1.0, so a skill that genuinely
  // moved routinely moves 0.996 -> 0.998: a real change that is far too small for a 120pt bar to
  // show. Without this, such a row is lit but motionless, which is indistinguishable at a glance
  // from a row that did nothing -- and "what changed" is the entire point of this screen.
  //
  // So a bar that moved carries a highlight travelling along its length, on a loop. It is clipped
  // to the FILL, so it reads as light moving through that skill's own bar rather than across the
  // empty track behind it. Rows start a stagger apart and then hold that offset, which makes the
  // group read as one wave running down the list instead of five bars flashing at once.
  useEffect(() => {
    if (changes.length === 0) return;

    const moving = SKILL_ROWS.map((row, index) => ({ index, key: row.key })).filter(
      (row) => bySkill.get(row.key)?.improved === true,
    );
    if (moving.length === 0) return;

    const loops = moving.map(({ index }) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(shimmers[index], {
            duration: SHIMMER_MS,
            // The prep card's own curve, for the same reason as the duration above.
            easing: Easing.out(Easing.cubic),
            toValue: 1,
            // `true`, and this is the reason the cue is a TRANSFORM rather than a colour or width
            // change: translateX is one of the few things the native driver can own, so the loop
            // runs off the JS thread and cannot be stuttered by anything this screen is doing.
            useNativeDriver: true,
          }),
          Animated.delay(SHIMMER_GAP_MS),
        ]),
      ),
    );

    // Started on a per-row timer rather than with Animated.stagger, so every row keeps an
    // IDENTICAL period and merely begins at a different phase. A stagger inside the loop body
    // would re-apply its delay on every pass and the rows would drift out of formation.
    const timers = loops.map((loop, ordinal) =>
      setTimeout(() => loop.start(), START_DELAY_MS + ordinal * ROW_STAGGER_MS),
    );

    return () => {
      timers.forEach(clearTimeout);
      loops.forEach((loop) => loop.stop());
      // Park each highlight off the left edge, so a row cannot be left with a bright band frozen
      // in the middle of it if the screen unmounts mid-pass.
      moving.forEach(({ index }) => shimmers[index].setValue(0));
    };
  }, [bySkill, changes, shimmers]);

  return (
    <View style={styles.rows}>
      {SKILL_ROWS.map((row, index) => {
        const change = bySkill.get(row.key);
        const before = change?.before ?? 0;
        const after = change?.after ?? 0;
        const improved = change?.improved ?? false;
        return (
          <View key={row.key} style={styles.row}>
            <AppText numberOfLines={1} style={styles.rowLabel}>
              {index + 1}. {row.label}
            </AppText>
            {/* Decorative on purpose: `accessible={false}`, no progressbar role, and deliberately
                no spoken value prop -- deliberately not spelled out here, because a guard test
                scans this file for it. The ruling is bar LENGTH only, and a screen reader
                announcing "62 percent" would be exactly the number the child must not be given.
                NO NUMBER IS RENDERED anywhere in this component. */}
            <View accessible={false} importantForAccessibility="no-hide-descendants" style={styles.track}>
              <Animated.View
                style={[
                  styles.trackFill,
                  {
                    backgroundColor: row.color,
                    // DULLED WHEN NOTHING MOVED. Opacity rather than a second, greyer palette, so
                    // the row is recognisably the same skill in the same colour as on the prep
                    // card -- just quiet.
                    opacity: improved ? 1 : UNCHANGED_OPACITY,
                    width: drivers[index].interpolate({
                      inputRange: [0, 1],
                      outputRange: [`${before}%`, `${after}%`],
                    }),
                  },
                ]}>
                {improved ? (
                  <Animated.View
                    style={[
                      styles.shimmer,
                      {
                        transform: [
                          {
                            translateX: shimmers[index].interpolate({
                              inputRange: [0, 1],
                              outputRange: [-SHIMMER_WIDTH, TRACK_WIDTH],
                            }),
                          },
                          // A slight lean, so it reads as a sheen passing over the bar. Gentler
                          // than it was: with the edges now fading to transparent there is no
                          // visible edge for a steep angle to flatter, and a steep one on a 16pt
                          // bar mostly just sharpened the leading corner.
                          { skewX: '-12deg' },
                        ],
                      },
                    ]}>
                    <LinearGradient
                      colors={SHIMMER_COLORS}
                      end={{ x: 1, y: 0 }}
                      locations={SHIMMER_LOCATIONS}
                      start={{ x: 0, y: 0 }}
                      style={StyleSheet.absoluteFill}
                    />
                  </Animated.View>
                ) : null}
              </Animated.View>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  // Label on the left, bar pinned to the right edge of the row -- matching the prep card exactly.
  row: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  rowLabel: {
    fontFamily: typography.fonts.bold,
    fontSize: 14,
    lineHeight: 18,
  },
  rows: { gap: spacing.mdPlus, justifyContent: 'center' },
  shimmer: {
    bottom: 0,
    position: 'absolute',
    top: 0,
    width: SHIMMER_WIDTH,
  },
  // `overflow: hidden` is load-bearing: it clips the highlight to the FILLED part of the bar, so
  // the cue never paints across the empty remainder of the track.
  trackFill: { borderRadius: radius.pill, height: '100%', overflow: 'hidden' },
  track: {
    backgroundColor: colors.surface3,
    borderRadius: radius.pill,
    height: 16,
    overflow: 'hidden',
    width: TRACK_WIDTH,
  },
});
