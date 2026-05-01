import React, { useRef, useEffect } from 'react';
import { Animated, StyleSheet, Text, View, ScrollView } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

const FEATURES = [
  { emoji: '🔬', animal: '🦁', bg: '#FFF0D0', titleKey: 'feature1Title' as const, descKey: 'feature1Desc' as const, accentColor: colors.coral },
  { emoji: '🧩', animal: '🐸', bg: '#E8FFE8', titleKey: 'feature2Title' as const, descKey: 'feature2Desc' as const, accentColor: colors.green },
  { emoji: '💡', animal: '🦒', bg: '#E0E8FF', titleKey: 'feature3Title' as const, descKey: 'feature3Desc' as const, accentColor: colors.blue },
];

export default function SplashScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const fadeAnims = useRef(FEATURES.map(() => new Animated.Value(0))).current;
  const slideAnims = useRef(FEATURES.map(() => new Animated.Value(40))).current;
  const heroScale = useRef(new Animated.Value(0.5)).current;
  const heroOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Hero animation
    Animated.parallel([
      Animated.spring(heroScale, { toValue: 1, friction: 5, tension: 60, useNativeDriver: true }),
      Animated.timing(heroOpacity, { toValue: 1, duration: 600, useNativeDriver: true }),
    ]).start();

    // Staggered feature cards
    FEATURES.forEach((_, i) => {
      setTimeout(() => {
        Animated.parallel([
          Animated.timing(fadeAnims[i], { toValue: 1, duration: 500, useNativeDriver: true }),
          Animated.spring(slideAnims[i], { toValue: 0, friction: 6, tension: 60, useNativeDriver: true }),
        ]).start();
      }, 400 + i * 200);
    });
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Decorative background elements */}
      <View style={styles.bgBlob1} />
      <View style={styles.bgBlob2} />

      {/* Hero illustration */}
      <Animated.View style={[styles.heroSection, { transform: [{ scale: heroScale }], opacity: heroOpacity }]}>
        {/* Central brain with orbiting dimensions */}
        <View style={styles.heroOuterRing}>
          <View style={[styles.orbitDot, styles.orbit1]}>
            <Text style={{ fontSize: 20 }}>🧠</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit2]}>
            <Text style={{ fontSize: 20 }}>🎯</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit3]}>
            <Text style={{ fontSize: 20 }}>🔢</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit4]}>
            <Text style={{ fontSize: 20 }}>⚡</Text>
          </View>
          <View style={styles.heroCenter}>
            <Text style={{ fontSize: 48 }}>🐑</Text>
          </View>
        </View>
      </Animated.View>

      {/* Title */}
      <Text style={styles.title}>{t.splash.title}</Text>
      <Text style={styles.subtitle}>{t.splash.subtitle}</Text>

      {/* Feature cards – cartoon style */}
      <View style={styles.features}>
        {FEATURES.map((feat, i) => (
          <Animated.View
            key={i}
            style={[
              styles.featureCard,
              { backgroundColor: feat.bg, opacity: fadeAnims[i], transform: [{ translateY: slideAnims[i] }] },
            ]}
          >
            <View style={[styles.featureAnimal, { borderColor: feat.accentColor }]}>
              <Text style={{ fontSize: 28 }}>{feat.animal}</Text>
            </View>
            <View style={styles.featureContent}>
              <Text style={[styles.featureTitle, { color: feat.accentColor }]}>{t.splash[feat.titleKey]}</Text>
              <Text style={styles.featureDesc}>{t.splash[feat.descKey]}</Text>
            </View>
          </Animated.View>
        ))}
      </View>

      {/* Progress dots */}
      <View style={styles.dotsRow}>
        <View style={styles.dotActive} />
        <View style={styles.dot} />
        <View style={styles.dot} />
      </View>

      {/* CTA */}
      <View style={styles.cta}>
        <PrimaryButton
          title={`${t.splash.getStarted}  →`}
          onPress={() => navigation.replace('LanguageSelect')}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: 60,
    paddingBottom: spacing.xxl,
    alignItems: 'center',
  },
  // Background blobs
  bgBlob1: {
    position: 'absolute',
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(255, 217, 61, 0.15)',
    top: -40,
    right: -40,
  },
  bgBlob2: {
    position: 'absolute',
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(145, 209, 89, 0.10)',
    bottom: 100,
    left: -60,
  },
  // Hero illustration
  heroSection: {
    width: 200,
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  heroOuterRing: {
    width: 200,
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 100,
    borderWidth: 3,
    borderColor: colors.borderLight,
    borderStyle: 'dashed',
  },
  heroCenter: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#FFE082',
    shadowColor: 'rgba(255, 180, 0, 0.35)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 6,
  },
  orbitDot: {
    position: 'absolute',
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2.5,
    borderColor: colors.border,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  orbit1: { top: -8, left: '50%', marginLeft: -21 },
  orbit2: { top: '50%', right: -8, marginTop: -21 },
  orbit3: { bottom: -8, left: '50%', marginLeft: -21 },
  orbit4: { top: '50%', left: -8, marginTop: -21 },
  // Title
  title: {
    ...typography.title,
    color: colors.textWarm,
    textAlign: 'center',
    marginBottom: spacing.xs,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: spacing.lg,
    maxWidth: 300,
  },
  // Feature cards
  features: {
    width: '100%',
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  featureCard: {
    flexDirection: 'row',
    borderRadius: radius.xl,
    padding: spacing.lg,
    gap: spacing.md,
    alignItems: 'center',
    borderWidth: 0,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 10,
    elevation: 3,
  },
  featureAnimal: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
  },
  featureContent: {
    flex: 1,
    gap: 4,
  },
  featureTitle: {
    ...typography.subtitle,
    fontWeight: '800',
  },
  featureDesc: {
    ...typography.small,
    color: colors.textMuted,
    lineHeight: 18,
  },
  // Dots
  dotsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: spacing.lg,
  },
  dotActive: {
    width: 24,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.warmYellow,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
  },
  cta: {
    width: '100%',
  },
});
