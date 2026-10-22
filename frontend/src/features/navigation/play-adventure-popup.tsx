// The "Play Adventure" prompt, raised by the tab bar's Play button when the adventure battery is
// not yet full (adventure-charge-context.tsx's `requestPlay`).
//
// It began as a quiet pill inside the header, briefly moved above the tab bar next to the button
// that raises it, and is now a real popup sitting back in the header band: the page behind it
// blurs and dims, and the pill animates in (2026-09-27, owner instruction). A message the child
// can miss is a message that does not work -- the blur is what makes them look at it.
//
// RENDERED GLOBALLY by AdventureChargeProvider, and deliberately NOT by the header bar it is drawn
// over: the blur has to cover the whole page, and a component cannot blur what is drawn above it --
// the header is 88px of a full screen. PlayPrepCard lives there for the same reason, and this sits
// beside it in the provider's tree.
//
// It never blocks the app, and it offers the child two ways out: the X on the pill, and a tap
// anywhere on the backdrop behind it. The X is there mostly to TEACH the second one -- a blurred
// screen with no visible control reads as stuck, so the icon says "this closes" even for a child
// who then taps the background instead. Everything else in the popup is untouchable
// (`pointerEvents` is off on the pill body), and the whole thing removes itself after
// PILL_VISIBLE_MS regardless of whether anything is pressed.

import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/src/components/app-text';
import {
  LEARNER_HEADER_HEIGHT,
  LEARNER_HEADER_HEIGHT_COMPACT,
} from '@/src/features/navigation/chrome-metrics';
import { colors, radius, spacing } from '@/src/theme/tokens';

const ENTRANCE_MS = 260;

export function PlayAdventurePopup({ onDismiss }: { onDismiss: () => void }) {
  const compact = useWindowDimensions().height < 760;
  const insets = useSafeAreaInsets();
  const enter = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(enter, {
      duration: ENTRANCE_MS,
      easing: Easing.out(Easing.back(1.6)),
      toValue: 1,
      useNativeDriver: true,
    }).start();
  }, [enter]);

  // Centred in the header band at the top of the screen (owner instruction, 2026-09-27), which is
  // where the pill originally lived before it briefly moved down beside the Play button. The band
  // is the header's OWN height, read from its module rather than repeated, so a change to the
  // header cannot leave this floating over or under it -- the same contract the tab bar's exported
  // geometry provides. Offset by the safe-area inset because the screens render the header inside
  // a SafeAreaView.
  const headerHeight = compact ? LEARNER_HEADER_HEIGHT_COMPACT : LEARNER_HEADER_HEIGHT;

  return (
    <View pointerEvents="box-none" style={StyleSheet.absoluteFill}>
      <Pressable accessibilityElementsHidden importantForAccessibility="no" onPress={onDismiss} style={StyleSheet.absoluteFill}>
        <Animated.View style={[StyleSheet.absoluteFill, { opacity: enter }]}>
          <BlurView intensity={28} style={StyleSheet.absoluteFill} tint="light" />
          <View style={styles.scrim} />
        </Animated.View>
      </Pressable>

      <Animated.View
        accessibilityLiveRegion="polite"
        accessibilityRole="alert"
        // `box-none`, not `none`: the slot and the pill body still pass touches through to the
        // backdrop, but the X inside can receive its own.
        pointerEvents="box-none"
        style={[
          styles.pillSlot,
          {
            height: headerHeight,
            top: insets.top,
            opacity: enter,
            transform: [
              { scale: enter.interpolate({ inputRange: [0, 1], outputRange: [0.82, 1] }) },
              // Drops IN from above, matching where it now sits; it rose from below during the
              // short time it lived above the tab bar.
              { translateY: enter.interpolate({ inputRange: [0, 1], outputRange: [-10, 0] }) },
            ],
          },
        ]}>
        <View pointerEvents="box-none" style={styles.pill}>
          <AppText style={styles.pillText}>Play Adventure</AppText>
          <Pressable
            accessibilityLabel="Dismiss"
            accessibilityRole="button"
            hitSlop={12}
            onPress={onDismiss}
            style={({ pressed }) => [styles.pillClose, pressed && styles.pillClosePressed]}>
            <Ionicons color={colors.primary} name="close" size={16} />
          </Pressable>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  // Same shape as before; the accent is the brand red (#ff6b68, `colors.primary`) rather than the
  // green it carried in the header, on owner instruction.
  pill: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.primary,
    borderRadius: radius.pill,
    borderWidth: 2,
    elevation: 6,
    flexDirection: 'row',
    gap: spacing.sm,
    // Less padding on the trailing edge than the leading one: the X carries its own hit area, so
    // matching the left padding would leave the icon looking adrift from the text.
    paddingLeft: spacing.mdPlus,
    paddingRight: spacing.smPlus,
    paddingVertical: spacing.sm,
    shadowColor: colors.primaryShadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.28,
    shadowRadius: 10,
  },
  pillClose: { alignItems: 'center', justifyContent: 'center' },
  pillClosePressed: { opacity: 0.5 },
  pillSlot: { alignItems: 'center', justifyContent: 'center', left: 0, position: 'absolute', right: 0 },
  pillText: { color: colors.primary, fontSize: 15, fontWeight: '900', letterSpacing: 0.3 },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(22,22,28,0.18)' },
});
