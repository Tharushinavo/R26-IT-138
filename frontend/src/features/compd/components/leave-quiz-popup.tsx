import { useEffect, useRef } from 'react';

import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { Animated, Easing, Pressable, StyleSheet, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/src/components/app-text';
import { FrostedScrim } from '@/src/components/frosted-scrim';
import AnimalMascot from '@/src/features/compd/components/animal-mascot';
import { artwork } from '@/src/utils/artwork';
import { colors, radius, spacing, typography } from '@/src/theme/tokens';

// The same garden artwork, aspect ratio and frosted backdrop as Component C's Play prep card
// (src/features/home/play-prep-card.tsx), so leaving compD's quiz looks like the rest of the app
// (owner request, 2026-10-21). Content starts below the artwork's sky band, as it does there.
const CARD_ASPECT_RATIO = 941 / 1672;
const ARTWORK_PANEL_TOP = 0.155;
const MAX_CARD_HEIGHT = 520;

type Props = {
  lang: 'en' | 'si';
  onKeepPlaying: () => void;
  onLeave: () => void;
};

/** "Leave the quiz?" over a blurred quiz. Closing it (X or Keep playing) resumes the run. */
export default function LeaveQuizPopup({ lang, onKeepPlaying, onLeave }: Props) {
  const { height, width } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const cardIn = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(cardIn, { duration: 200, easing: Easing.out(Easing.quad), toValue: 1, useNativeDriver: true }).start();
  }, [cardIn]);

  const availableHeight = height - insets.top - insets.bottom - spacing.xl * 2;
  const availableWidth = Math.min(width - spacing.lg * 2, 380);
  let cardHeight = Math.min(availableHeight, MAX_CARD_HEIGHT);
  let cardWidth = cardHeight * CARD_ASPECT_RATIO;
  if (cardWidth > availableWidth) {
    cardWidth = availableWidth;
    cardHeight = cardWidth / CARD_ASPECT_RATIO;
  }

  const si = lang === 'si';

  return (
    <View accessibilityViewIsModal style={styles.overlay}>
      <FrostedScrim intensity={40} style={StyleSheet.absoluteFill} />
      <View style={styles.scrim} />

      <Animated.View
        style={[
          styles.card,
          {
            height: cardHeight,
            opacity: cardIn,
            transform: [{ scale: cardIn.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1] }) }],
            width: cardWidth,
          },
        ]}>
        <Image accessible={false} contentFit="cover" source={artwork.startGame} style={StyleSheet.absoluteFill} />
        <View style={[styles.cardInner, { paddingTop: cardHeight * ARTWORK_PANEL_TOP + spacing.sm }]}>
          <Pressable
            accessibilityLabel={si ? 'වසන්න' : 'Close'}
            accessibilityRole="button"
            hitSlop={10}
            onPress={onKeepPlaying}
            style={styles.closeButton}>
            <Ionicons color={colors.textSecondary} name="close" size={20} />
          </Pressable>

          <AppText style={styles.heading}>{si ? 'ක්‍රියාකාරකමෙන් ඉවත් වෙනවාද?' : 'Leave the quiz?'}</AppText>
          <AppText style={styles.subheading}>
            {si ? 'මෙතෙක් දුන් පිළිතුරු සුරැකෙන්නේ නැත.' : 'Your answers so far will not be saved.'}
          </AppText>

          <View style={styles.mascot}>
            <AnimalMascot animal={5} size={Math.min(140, cardHeight * 0.28)} />
          </View>

          <Pressable
            accessibilityRole="button"
            onPress={onKeepPlaying}
            style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}>
            <AppText style={styles.primaryButtonText}>{si ? 'දිගටම සෙල්ලම් කරන්න' : 'Keep playing'}</AppText>
            <Ionicons color={colors.primaryForeground} name="chevron-forward" size={20} />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            onPress={onLeave}
            style={({ pressed }) => [styles.secondaryButton, pressed && styles.buttonPressed]}>
            <AppText style={styles.secondaryButtonText}>{si ? 'ඉවත් වන්න' : 'Leave'}</AppText>
          </Pressable>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  buttonPressed: { borderBottomWidth: 0, transform: [{ translateY: 3 }] },
  card: {
    borderRadius: radius.lg,
    elevation: 8,
    overflow: 'hidden',
    shadowColor: colors.foreground,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.22,
    shadowRadius: 14,
  },
  cardInner: { flex: 1, gap: spacing.sm, paddingBottom: spacing.md, paddingHorizontal: spacing.md },
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
  heading: { fontFamily: typography.fonts.heavy, fontSize: 18, lineHeight: 24, textAlign: 'center' },
  mascot: { alignItems: 'center', flex: 1, justifyContent: 'center' },
  overlay: {
    alignItems: 'center',
    bottom: 0,
    justifyContent: 'center',
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
    zIndex: 10,
  },
  primaryButton: {
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
  primaryButtonText: {
    color: colors.primaryForeground,
    fontFamily: typography.fonts.bold,
    fontSize: 13.64,
    lineHeight: 22.32,
    textAlign: 'center',
  },
  scrim: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(22,22,28,0.3)' },
  secondaryButton: {
    alignItems: 'center',
    backgroundColor: colors.surface1,
    borderColor: colors.border,
    borderRadius: 14.88,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: 14.88,
  },
  secondaryButtonText: {
    color: colors.textSecondary,
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
});
