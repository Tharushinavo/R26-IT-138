import React, { useEffect, useRef } from 'react';
import { Animated, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import { useLanguage } from '../i18n/LanguageContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'Splash'>;

const FEATURES = [
  { animal: '🦁', bg: '#FFF0D0', titleKey: 'feature1Title' as const, descKey: 'feature1Desc' as const, accentKey: 'coral' as const },
  { animal: '🐸', bg: '#E8FFE8', titleKey: 'feature2Title' as const, descKey: 'feature2Desc' as const, accentKey: 'green' as const },
  { animal: '🐒', bg: '#E0E8FF', titleKey: 'feature3Title' as const, descKey: 'feature3Desc' as const, accentKey: 'blue' as const },
];

export default function SplashScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const { colors, isDark } = useAppTheme();
  const styles = createStyles(colors);
  const fadeAnims = useRef(FEATURES.map(() => new Animated.Value(0))).current;
  const slideAnims = useRef(FEATURES.map(() => new Animated.Value(40))).current;
  const heroScale = useRef(new Animated.Value(0.5)).current;
  const heroOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(heroScale, { toValue: 1, friction: 5, tension: 60, useNativeDriver: true }),
      Animated.timing(heroOpacity, { toValue: 1, duration: 600, useNativeDriver: true }),
    ]).start();

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
      <Animated.View style={[styles.heroSection, { transform: [{ scale: heroScale }], opacity: heroOpacity }]}>
        <View style={styles.heroOuterRing}>
          <View style={[styles.orbitDot, styles.orbit1]}>
            <Text style={styles.orbitIcon}>🧠</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit2]}>
            <Text style={styles.orbitIcon}>🎯</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit3]}>
            <Text style={styles.orbitIcon}>🔢</Text>
          </View>
          <View style={[styles.orbitDot, styles.orbit4]}>
            <Text style={styles.orbitIcon}>⚡</Text>
          </View>
          <View style={styles.heroCenter}>
            <Text style={styles.heroIcon}>🐑</Text>
          </View>
        </View>
      </Animated.View>

      <Text style={styles.title}>{t.splash.title}</Text>
      <Text style={styles.subtitle}>{t.splash.subtitle}</Text>

      <View style={styles.features}>
        {FEATURES.map((feat, i) => {
          const accentColor = colors[feat.accentKey];
          return (
            <Animated.View
              key={feat.titleKey}
              style={[
                styles.featureCard,
                {
                  backgroundColor: isDark ? colors.surfaceSoft : feat.bg,
                  opacity: fadeAnims[i],
                  transform: [{ translateY: slideAnims[i] }],
                },
              ]}
            >
              <View style={[styles.featureAnimal, { borderColor: accentColor }]}>
                <Text style={styles.featureAnimalText}>{feat.animal}</Text>
              </View>
              <View style={styles.featureContent}>
                <Text style={[styles.featureTitle, { color: accentColor }]}>{t.splash[feat.titleKey]}</Text>
                <Text style={styles.featureDesc}>{t.splash[feat.descKey]}</Text>
              </View>
            </Animated.View>
          );
        })}
      </View>

      <View style={styles.dotsRow}>
        <View style={styles.dotActive} />
        <View style={styles.dot} />
        <View style={styles.dot} />
      </View>

      <View style={styles.cta}>
        <PrimaryButton title={`${t.splash.getStarted}  →`} onPress={() => navigation.replace('LanguageSelect')} />
      </View>
    </ScrollView>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: 60,
    paddingBottom: spacing.xxl,
    alignItems: 'center',
    backgroundColor: colors.background,
  },
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
    borderColor: colors.yellow,
    shadowColor: colors.shadow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 10,
    elevation: 6,
  },
  heroIcon: { fontSize: 48 },
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
  orbitIcon: { fontSize: 20 },
  orbit1: { top: -8, left: '50%', marginLeft: -21 },
  orbit2: { top: '50%', right: -8, marginTop: -21 },
  orbit3: { bottom: -8, left: '50%', marginLeft: -21 },
  orbit4: { top: '50%', left: -8, marginTop: -21 },
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
    borderWidth: 1.5,
    borderColor: colors.border,
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
  featureAnimalText: { fontSize: 28 },
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
