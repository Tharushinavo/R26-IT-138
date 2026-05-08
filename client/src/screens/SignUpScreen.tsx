/**
 * SignUpScreen - Celebration theme! Kid-friendly animated signup with
 * different mascot (Koala with party hat). Emphasizes role selection.
 * Distinct from Login - celebratory colors and confetti animations.
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import { ANIMAL_IMAGES } from '../assets/animalImages';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'SignUp'>;
type UserRole = 'student' | 'teacher';

export default function SignUpScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const { register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('student');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Animations
  const mascotScale = useRef(new Animated.Value(0.5)).current;
  const mascotRotate = useRef(new Animated.Value(0)).current;
  const cardSlide = useRef(new Animated.Value(100)).current;
  const cardOpacity = useRef(new Animated.Value(0)).current;
  const confettiY1 = useRef(new Animated.Value(-50)).current;
  const confettiY2 = useRef(new Animated.Value(-50)).current;
  const confettiY3 = useRef(new Animated.Value(-50)).current;
  const rolePulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Entrance animations
    Animated.parallel([
      Animated.spring(mascotScale, { toValue: 1, friction: 5, useNativeDriver: true }),
      Animated.timing(cardSlide, { toValue: 0, duration: 500, useNativeDriver: true }),
      Animated.timing(cardOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
    ]).start();

    // Mascot gentle wiggle
    Animated.loop(
      Animated.sequence([
        Animated.timing(mascotRotate, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(mascotRotate, { toValue: -1, duration: 800, useNativeDriver: true }),
      ])
    ).start();

    // Falling confetti
    const dropConfetti = (anim: Animated.Value, delay: number, speed: number) => {
      setTimeout(() => {
        Animated.loop(
          Animated.sequence([
            Animated.timing(anim, { toValue: 800, duration: speed, useNativeDriver: true }),
            Animated.timing(anim, { toValue: -50, duration: 0, useNativeDriver: true }),
          ])
        ).start();
      }, delay);
    };
    dropConfetti(confettiY1, 0, 4000);
    dropConfetti(confettiY2, 1500, 3500);
    dropConfetti(confettiY3, 3000, 4500);
  }, []);

  // Pulse animation when role changes
  useEffect(() => {
    Animated.sequence([
      Animated.timing(rolePulse, { toValue: 1.05, duration: 150, useNativeDriver: true }),
      Animated.timing(rolePulse, { toValue: 1, duration: 150, useNativeDriver: true }),
    ]).start();
  }, [role]);

  const rotate = mascotRotate.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-8deg', '0deg', '8deg'],
  });

  const isValid =
    fullName.trim().length > 0 &&
    email.trim().length > 0 &&
    password.length >= 4;

  async function handleSignUp() {
    if (!isValid) return;
    setLoading(true);
    setError(null);

    try {
      const user = await register({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        role,
      });
      // Navigate based on role
      if (user.role === 'teacher' || user.role === 'admin') {
        navigation.replace('TeacherDashboard', { teacherId: user.id });
      } else {
        navigation.replace('StudentDashboard', { studentId: user.id, role: user.role });
      }
    } catch (e: any) {
      setError(e?.message || 'Registration failed. Please try again.');
      setLoading(false);
    }
  }

  const getRoleIcon = (r: UserRole) => (r === 'student' ? '🧒' : '👩‍🏫');

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Falling confetti decorations */}
        <Animated.Text style={[styles.confetti, styles.conf1, { transform: [{ translateY: confettiY1 }] }]}>🎉</Animated.Text>
        <Animated.Text style={[styles.confetti, styles.conf2, { transform: [{ translateY: confettiY2 }] }]}>✨</Animated.Text>
        <Animated.Text style={[styles.confetti, styles.conf3, { transform: [{ translateY: confettiY3 }] }]}>🎊</Animated.Text>

        {/* Header with party mascot - Celebration theme */}
        <View style={styles.hero}>
          <Animated.View
            style={[
              styles.mascotWrap,
              { transform: [{ scale: mascotScale }, { rotate }] },
            ]}
          >
            <View style={styles.mascotCircle}>
              <Image source={ANIMAL_IMAGES[13]} style={styles.mascot} resizeMode="contain" />
            </View>
            <View style={styles.partyHat}>
              <Text style={styles.partyEmoji}>🎉</Text>
            </View>
          </Animated.View>

          <Text style={styles.title}>{t.signUp.title}</Text>
          <Text style={styles.subtitle}>{t.signUp.subtitle}</Text>
        </View>

        <Animated.View
          style={[
            styles.cardWrap,
            { transform: [{ translateY: cardSlide }], opacity: cardOpacity },
          ]}
        >
          <Card style={styles.card}>
            {error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            {/* Name */}
            <Text style={styles.label}>{t.signUp.fullName}</Text>
            <TextInput
              value={fullName}
              onChangeText={setFullName}
              placeholder={t.signUp.namePlaceholder}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              autoCapitalize="words"
              autoComplete="name"
            />

            {/* Email */}
            <Text style={styles.label}>{t.signUp.email}</Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder={t.signUp.emailPlaceholder}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />

            {/* Password */}
            <Text style={styles.label}>{t.signUp.password}</Text>
            <TextInput
              value={password}
              onChangeText={setPassword}
              placeholder={t.signUp.passwordPlaceholder}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              secureTextEntry
              autoComplete="new-password"
            />

            {/* Role - Emphasized with celebration colors */}
            <Text style={[styles.label, styles.roleLabel]}>{t.signUp.iAmA}</Text>
            <Animated.View style={{ transform: [{ scale: rolePulse }] }}>
              <View style={styles.roleRow}>
                <TouchableOpacity
                  style={[styles.roleBtn, role === 'student' && styles.roleBtnActiveStudent]}
                  onPress={() => setRole('student')}
                  activeOpacity={0.7}
                >
                  <Text style={styles.roleEmoji}>{getRoleIcon('student')}</Text>
                  <Image source={ANIMAL_IMAGES[6]} style={styles.roleIcon} resizeMode="contain" />
                  <Text style={[styles.roleText, role === 'student' && styles.roleTextActiveStudent]}>
                    {t.signUp.studentLabel}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.roleBtn, role === 'teacher' && styles.roleBtnActiveTeacher]}
                  onPress={() => setRole('teacher')}
                  activeOpacity={0.7}
                >
                  <Text style={styles.roleEmoji}>{getRoleIcon('teacher')}</Text>
                  <Image source={ANIMAL_IMAGES[10]} style={styles.roleIcon} resizeMode="contain" />
                  <Text style={[styles.roleText, role === 'teacher' && styles.roleTextActiveTeacher]}>
                    {t.signUp.teacherLabel}
                  </Text>
                </TouchableOpacity>
              </View>
            </Animated.View>

            {/* Sign Up - Coral celebratory color */}
            <PrimaryButton
              title={t.signUp.createAccount}
              onPress={handleSignUp}
              disabled={!isValid}
              loading={loading}
              style={styles.submitBtn}
              variant="coral"
            />

            {/* Login link */}
            <View style={styles.linkRow}>
              <Text style={styles.linkText}>{t.signUp.alreadyHaveAccount} </Text>
              <TouchableOpacity onPress={() => navigation.replace('Login')} activeOpacity={0.7}>
                <Text style={styles.linkAction}>{t.signUp.signIn}</Text>
              </TouchableOpacity>
            </View>
          </Card>
        </Animated.View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    padding: spacing.lg,
    justifyContent: 'center',
  },
  // Confetti decorations
  confetti: {
    position: 'absolute',
    fontSize: 28,
  },
  conf1: { left: 30, top: 0 },
  conf2: { right: 40, top: 0 },
  conf3: { left: '50%', top: 0 },
  // Hero section
  hero: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  mascotWrap: {
    position: 'relative',
    marginBottom: spacing.md,
  },
  mascotCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#FFF0EB',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.coral,
    shadowColor: 'rgba(224, 110, 82, 0.3)',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 16,
    elevation: 8,
  },
  mascot: { width: 95, height: 95 },
  partyHat: {
    position: 'absolute',
    top: -10,
    right: -5,
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.background,
    transform: [{ rotate: '15deg' }],
  },
  partyEmoji: { fontSize: 22 },
  title: {
    ...typography.title,
    color: colors.coral,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  cardWrap: {},
  card: { gap: spacing.sm },
  errorBox: {
    backgroundColor: 'rgba(224, 110, 82, 0.15)',
    padding: spacing.sm,
    borderRadius: radius.md,
    marginBottom: spacing.sm,
  },
  errorText: {
    ...typography.caption,
    color: colors.coral,
    textAlign: 'center',
  },
  label: {
    ...typography.caption,
    color: colors.textWarm,
    fontWeight: '700',
  },
  roleLabel: {
    marginTop: spacing.sm,
    textAlign: 'center',
  },
  input: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.md,
    padding: spacing.md,
    fontSize: 16,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
  },
  // Role selection - emphasized design
  roleRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  roleBtn: {
    flex: 1,
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 3,
    borderColor: colors.border,
    gap: spacing.xs,
  },
  roleBtnActiveStudent: {
    borderColor: colors.green,
    backgroundColor: '#E8F9E8',
  },
  roleBtnActiveTeacher: {
    borderColor: colors.coral,
    backgroundColor: '#FFF0EB',
  },
  roleEmoji: {
    fontSize: 28,
  },
  roleIcon: {
    width: 40,
    height: 40,
  },
  roleText: {
    ...typography.caption,
    color: colors.textMuted,
    fontWeight: '600',
  },
  roleTextActiveStudent: {
    color: colors.green,
    fontWeight: '800',
  },
  roleTextActiveTeacher: {
    color: colors.coral,
    fontWeight: '800',
  },
  submitBtn: {
    marginTop: spacing.sm,
  },
  linkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: spacing.lg,
  },
  linkText: {
    ...typography.body,
    color: colors.textMuted,
  },
  linkAction: {
    ...typography.body,
    color: colors.coral,
    fontWeight: '700',
  },
});
