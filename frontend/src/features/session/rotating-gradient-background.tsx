// The slow, continuously rotating background wash both components' task screens sit on.
//
// Extracted from live-session-screen.tsx on 2026-09-28, when Component C was given the same
// background (owner instruction). It was private to Component B, and C's own convention has been
// to REPRODUCE B's shapes rather than import a private symbol -- but a rotation speed, an easing
// and a diagonal-sizing trick copied into a second file is a pair that drifts. Two screens that
// must look identical share the component; two screens that merely rhyme keep their own styles.
//
// A slow, continuous CLOCKWISE rotation around the screen's own centre. The gradient is drawn onto
// a square child sized to the screen's DIAGONAL (measured via onLayout, in real pixels -- not a
// flat percentage guess): a screen-sized gradient rotated about its centre would sweep its own
// corners into view, showing bare background at the edges every quarter turn. A square of the
// diagonal's side length always covers the screen at every angle.

import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';

/** Appends a 2-digit hex alpha to a 6-digit hex colour. The gradient is a faded wash over the
 * screen's own background, never the raw saturated colour. */
export function withAlpha(hex: string, alphaHex: string): string {
  return `${hex}${alphaHex}`;
}

/** The alpha both components use for the wash. Shared so one of them cannot quietly get bolder. */
export const GRADIENT_WASH_ALPHA = '33';

/**
 * Milliseconds for one full clockwise lap. Was 45000; sped up to 20000 on 2026-10-10 (owner
 * instruction) now that the Component C task card sits on a patterned background and the wash
 * behind it reads as a slower-moving layer than before.
 *
 * SHARED, SO THIS MOVES BOTH SCREENS. Component B's live session uses this same component, by
 * design -- this file's own header: "Two screens that must look identical share the component."
 * Speeding up C alone would reintroduce exactly the drift the extraction removed.
 *
 * KEPT WELL BELOW ANYTHING ATTENTION-GRABBING. This is the background of a screen where a child is
 * doing arithmetic under a timer; the rotation exists to keep the surface from feeling dead, not to
 * be noticed. 20s is still a slow sweep -- about 18 degrees per second. Going much below ~12s
 * starts to read as motion in the periphery, which is a distraction in a screening instrument and
 * an accessibility concern for motion-sensitive users, so treat that as the floor.
 */
export const SCREEN_GRADIENT_DURATION_MS = 20000;

type RotatingGradientBackgroundProps = {
  colors: readonly [string, string];
  /**
   * One lap, in milliseconds. Defaults to the shared screen-background speed; pass a smaller number
   * for a layer that should turn faster than it. A SECOND rotating layer only reads as a separate
   * thing if its period is clearly different -- two layers at similar speeds look like one
   * mis-rendered layer.
   */
  durationMs?: number;
  /**
   * Direction. Defaults to clockwise, matching the screen background. A counter-rotating layer is
   * the cheapest way to make two gradients legible as two: same-direction layers at different
   * speeds still drift together periodically, opposite-direction ones never do.
   */
  clockwise?: boolean;
};

export function RotatingGradientBackground({
  clockwise = true,
  colors: gradientColors,
  durationMs = SCREEN_GRADIENT_DURATION_MS,
}: RotatingGradientBackgroundProps) {
  const rotation = useSharedValue(0);
  const [screenSize, setScreenSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    // -1 repeats forever; `false` (no reverse) keeps every lap in ONE direction, never swinging
    // back the way a reversing repeat would on alternate laps. Direction is the sign of the target
    // angle, so a counter-clockwise layer is -360 rather than a reversed repeat.
    const target = clockwise ? 360 : -360;
    rotation.value = withRepeat(withTiming(target, { duration: durationMs, easing: Easing.linear }), -1, false);
  }, [clockwise, durationMs, rotation]);

  const spinStyle = useAnimatedStyle(() => ({ transform: [{ rotate: `${rotation.value}deg` }] }));

  const diagonal = screenSize
    ? Math.ceil(Math.sqrt(screenSize.width ** 2 + screenSize.height ** 2))
    : 0;

  return (
    <View
      onLayout={(event) =>
        setScreenSize({
          width: event.nativeEvent.layout.width,
          height: event.nativeEvent.layout.height,
        })
      }
      pointerEvents="none"
      style={styles.background}>
      {screenSize ? (
        <Animated.View
          style={[
            spinStyle,
            {
              height: diagonal,
              left: (screenSize.width - diagonal) / 2,
              position: 'absolute',
              top: (screenSize.height - diagonal) / 2,
              width: diagonal,
            },
          ]}>
          <LinearGradient
            colors={gradientColors}
            end={{ x: 1, y: 1 }}
            start={{ x: 0, y: 0 }}
            style={styles.fill}
          />
        </Animated.View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  background: { ...StyleSheet.absoluteFillObject, overflow: 'hidden' },
  fill: { flex: 1 },
});
