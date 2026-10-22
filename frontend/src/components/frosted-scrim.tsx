import { BlurView } from 'expo-blur';
import { Platform, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

/**
 * The frosted layer that lifts a popup off whatever is behind it.
 *
 * expo-blur does NOT blur on Android. `experimentalBlurMethod` defaults to `'none'` there, so a
 * BlurView renders as little more than a faint tint and the content behind it stays perfectly
 * sharp. Both verdict popups are drawn with no background of their own and lean entirely on this
 * layer for contrast, so on a real device the verdict text landed straight on top of the
 * question's own artwork -- unreadable. Web (CSS `backdrop-filter`) and iOS blur for real, which
 * is why this never showed up in browser testing.
 *
 * Android deliberately gets an opaque scrim rather than the experimental blur. Turning on
 * `experimentalBlurMethod="dimezisBlurView"` would blur for real, but Expo documents it as
 * experimental and prone to "performance and graphical issues" -- it redraws the view tree behind
 * it every frame, which is the wrong trade for the low-end Android hardware this app targets. A
 * flat scrim costs nothing and separates the two layers just as well.
 *
 * iOS and web are untouched and keep the real blur.
 */

// Near-opaque rather than fully opaque: enough to stop the question reading through as detail,
// while the last of it still hints that something is behind the popup, which is the impression
// the blur gives on the platforms that have one.
const ANDROID_LIGHT_SCRIM = 'rgba(252, 252, 253, 0.94)';

type FrostedScrimProps = {
  /** Blur strength on the platforms that blur. Ignored on Android, which does not. */
  intensity?: number;
  /**
   * How much the scrim WHITENS what it blurs, which on web is separate from the blur itself.
   *
   * expo-blur draws a tint colour over the backdrop filter, and the two tints this app uses differ
   * sharply in how opaque that colour is (`expo-blur/build/getBackgroundColor.js`, read rather than
   * assumed):
   *
   *   'light'   -> rgba(249,249,249, intensity/100 * 0.78)
   *   'default' -> rgba(255,255,255, intensity/100 * 0.30)
   *
   * So at the SAME intensity, 'default' is roughly a third as white. Use it where the surface
   * behind the scrim is meant to stay visible as texture rather than be washed out; keep 'light'
   * where the scrim's job is to hide detail. Blur radius is `intensity * 0.2`px either way, so
   * intensity can be raised to blur MORE while 'default' keeps the result transparent.
   */
  tint?: 'light' | 'default';
  style?: StyleProp<ViewStyle>;
};

export function FrostedScrim({ intensity = 40, style, tint = 'light' }: FrostedScrimProps) {
  if (Platform.OS === 'android') return <View style={[style, styles.androidScrim]} />;
  return <BlurView intensity={intensity} style={style} tint={tint} />;
}

const styles = StyleSheet.create({
  androidScrim: { backgroundColor: ANDROID_LIGHT_SCRIM },
});
