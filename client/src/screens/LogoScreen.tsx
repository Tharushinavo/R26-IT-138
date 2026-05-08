import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View, Text, Image } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, typography, spacing } from '../theme';
import { ANIMAL_IMAGES } from '../assets/animalImages';
import { getStoredToken, getStoredUser } from '../api/client';

type Props = NativeStackScreenProps<RootStackParamList, 'Logo'>;

export default function LogoScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const navigatedRef = useRef(false);
  const scaleAnim = useRef(new Animated.Value(0.3)).current;
  const opacityAnim = useRef(new Animated.Value(0)).current;
  const taglineOpacity = useRef(new Animated.Value(0)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;
  // Animated values for floating number characters
  const num1Float = useRef(new Animated.Value(0)).current;
  const num2Float = useRef(new Animated.Value(0)).current;
  const num3Float = useRef(new Animated.Value(0)).current;
  const num4Float = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        tension: 50,
        useNativeDriver: true,
      }),
      Animated.timing(opacityAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();

    setTimeout(() => {
      Animated.timing(taglineOpacity, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }).start();
    }, 600);

    // Bounce mascot
    Animated.loop(
      Animated.sequence([
        Animated.timing(bounceAnim, { toValue: -8, duration: 800, useNativeDriver: true }),
        Animated.timing(bounceAnim, { toValue: 0, duration: 800, useNativeDriver: true }),
      ]),
    ).start();

    // Floating number animations (staggered)
    const floatLoop = (anim: Animated.Value, delay: number) => {
      setTimeout(() => {
        Animated.loop(
          Animated.sequence([
            Animated.timing(anim, { toValue: -6, duration: 1200, useNativeDriver: true }),
            Animated.timing(anim, { toValue: 6, duration: 1200, useNativeDriver: true }),
          ]),
        ).start();
      }, delay);
    };
    floatLoop(num1Float, 0);
    floatLoop(num2Float, 300);
    floatLoop(num3Float, 600);
    floatLoop(num4Float, 900);

    // After splash delay, check stored auth and route accordingly
    const timer = setTimeout(async () => {
      if (navigatedRef.current) return;
      navigatedRef.current = true;

      try {
        const token = await getStoredToken();
        const storedUser = await getStoredUser();

        if (token && storedUser) {
          if (storedUser.role === 'teacher' || storedUser.role === 'admin') {
            navigation.replace('TeacherDashboard', { teacherId: storedUser.id });
          } else {
            navigation.replace('StudentDashboard', { studentId: storedUser.id, role: storedUser.role });
          }
        } else {
          navigation.replace('Splash');
        }
      } catch {
        navigation.replace('Splash');
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [navigation]);

  return (
    <View style={styles.container}>
      {/* Decorative soft blobs */}
      <View style={[styles.blob, styles.blob1]} />
      <View style={[styles.blob, styles.blob2]} />
      <View style={[styles.blob, styles.blob3]} />

      {/* Floating cartoon number characters */}
      <Animated.View style={[styles.floatingNum, styles.numPos1, { transform: [{ translateY: num1Float }] }]}>
        <Text style={[styles.numText, { color: colors.coral }]}>1</Text>
        <View style={[styles.numBadge, { backgroundColor: colors.warmYellow }]}>
          <Text style={styles.numBadgeText}>+</Text>
        </View>
      </Animated.View>
      <Animated.View style={[styles.floatingNum, styles.numPos2, { transform: [{ translateY: num2Float }] }]}>
        <Text style={[styles.numText, { color: colors.green }]}>2</Text>
        <View style={[styles.numBadge, { backgroundColor: colors.green }]}>
          <Text style={styles.numBadgeText}>÷</Text>
        </View>
      </Animated.View>
      <Animated.View style={[styles.floatingNum, styles.numPos3, { transform: [{ translateY: num3Float }] }]}>
        <Text style={[styles.numText, { color: colors.blue }]}>3</Text>
        <View style={[styles.numBadge, { backgroundColor: colors.blue }]}>
          <Text style={styles.numBadgeText}>=</Text>
        </View>
      </Animated.View>
      <Animated.View style={[styles.floatingNum, styles.numPos4, { transform: [{ translateY: num4Float }] }]}>
        <Text style={[styles.numText, { color: colors.purple }]}>4</Text>
        <View style={[styles.numBadge, { backgroundColor: colors.pink }]}>
          <Text style={styles.numBadgeText}>×</Text>
        </View>
      </Animated.View>

      {/* Main mascot & logo */}
      <Animated.View
        style={[
          styles.logoContainer,
          { transform: [{ scale: scaleAnim }, { translateY: bounceAnim }], opacity: opacityAnim },
        ]}
      >
        <View style={styles.mascotCircle}>
          <Image source={ANIMAL_IMAGES[5]} style={styles.mascotImage} resizeMode="contain" />
        </View>
      </Animated.View>

      <Animated.View style={{ opacity: opacityAnim }}>
        <Text style={styles.appName}>MathsMate</Text>
      </Animated.View>

      <Animated.View style={{ opacity: taglineOpacity }}>
        <Text style={styles.tagline}>{t.logo.tagline}</Text>
      </Animated.View>

      {/* Bottom animal friends */}
      <View style={styles.bottomBar}>
        <View style={styles.animalRow}>
          <View style={[styles.animalPill, { backgroundColor: '#FFE0D0' }]}>
            <Image source={ANIMAL_IMAGES[1]} style={styles.animalPillImage} resizeMode="contain" />
          </View>
          <View style={[styles.animalPill, { backgroundColor: '#D6F5E3' }]}>
            <Image source={ANIMAL_IMAGES[15]} style={styles.animalPillImage} resizeMode="contain" />
          </View>
          <View style={[styles.animalPill, { backgroundColor: '#E0E8FF' }]}>
            <Image source={ANIMAL_IMAGES[18]} style={styles.animalPillImage} resizeMode="contain" />
          </View>
          <View style={[styles.animalPill, { backgroundColor: '#FFF0D0' }]}>
            <Image source={ANIMAL_IMAGES[12]} style={styles.animalPillImage} resizeMode="contain" />
          </View>
        </View>
        <Text style={styles.versionText}>Cognitive Skill Profiling System</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Soft decorative blobs
  blob: {
    position: 'absolute',
    borderRadius: 999,
  },
  blob1: {
    width: 260,
    height: 260,
    backgroundColor: 'rgba(255, 217, 61, 0.18)',
    top: -60,
    left: -60,
  },
  blob2: {
    width: 200,
    height: 200,
    backgroundColor: 'rgba(113, 160, 251, 0.12)',
    bottom: 80,
    right: -50,
  },
  blob3: {
    width: 160,
    height: 160,
    backgroundColor: 'rgba(145, 209, 89, 0.10)',
    top: '35%',
    left: -40,
  },
  // Floating number characters
  floatingNum: {
    position: 'absolute',
    alignItems: 'center',
  },
  numPos1: { top: 100, left: 30 },
  numPos2: { top: 80, right: 40 },
  numPos3: { bottom: 200, left: 50 },
  numPos4: { bottom: 180, right: 30 },
  numText: {
    fontSize: 48,
    fontWeight: '900',
  },
  numBadge: {
    position: 'absolute',
    bottom: -2,
    right: -10,
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numBadgeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '900',
  },
  // Mascot
  logoContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  mascotCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: '#FFE082',
    shadowColor: 'rgba(255, 180, 0, 0.4)',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 1,
    shadowRadius: 16,
    elevation: 8,
  },
  mascotImage: { width: 80, height: 80 },
  animalPillImage: { width: 32, height: 32 },
  appName: {
    fontSize: 42,
    fontWeight: '900',
    color: colors.textWarm,
    letterSpacing: -1,
    textAlign: 'center',
  },
  tagline: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 60,
    alignItems: 'center',
    gap: spacing.md,
  },
  animalRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  animalPill: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.6)',
  },
  versionText: {
    ...typography.small,
    color: colors.textMuted,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
});
