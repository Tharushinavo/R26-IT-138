/**
 * LoginScreen - Welcome back! Kid-friendly animated login with
 * cartoon animal mascot (Panda waving). Distinct from SignUp.
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
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export default function LoginScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const { login } = useAuth();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Animations
  const mascotBounce = useRef(new Animated.Value(0)).current;
  const mascotRotate = useRef(new Animated.Value(0)).current;
  const cardSlide = useRef(new Animated.Value(50)).current;
  const cardOpacity = useRef(new Animated.Value(0)).current;
  const float1 = useRef(new Animated.Value(0)).current;
  const float2 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Mascot wave animation
    Animated.loop(
      Animated.sequence([
        Animated.timing(mascotBounce, { toValue: -10, duration: 600, useNativeDriver: true }),
        Animated.timing(mascotBounce, { toValue: 0, duration: 600, useNativeDriver: true }),
      ])
    ).start();

    // Gentle rotation
    Animated.loop(
      Animated.sequence([
        Animated.timing(mascotRotate, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(mascotRotate, { toValue: -1, duration: 2000, useNativeDriver: true }),
      ])
    ).start();

    // Card entrance
    Animated.parallel([
      Animated.timing(cardSlide, { toValue: 0, duration: 600, useNativeDriver: true }),
      Animated.timing(cardOpacity, { toValue: 1, duration: 600, useNativeDriver: true }),
    ]).start();

    // Background floating elements
    const floatAnim = (anim: Animated.Value, delay: number) => {
      setTimeout(() => {
        Animated.loop(
          Animated.sequence([
            Animated.timing(anim, { toValue: -15, duration: 2000, useNativeDriver: true }),
            Animated.timing(anim, { toValue: 15, duration: 2000, useNativeDriver: true }),
          ])
        ).start();
      }, delay);
    };
    floatAnim(float1, 0);
    floatAnim(float2, 1000);
  }, []);

  const rotate = mascotRotate.interpolate({
    inputRange: [-1, 0, 1],
    outputRange: ['-5deg', '0deg', '5deg'],
  });

  const isValid = email.trim().length > 0 && password.length >= 4;

  async function handleSignIn() {
    if (!isValid) return;
    setLoading(true);
    setError(null);

    try {
      const user = await login({ email: email.trim(), password });
      console.log('[login] navigation after login', { userId: user.id, role: user.role });
      // Reset stack completely to prevent back-button leaking into previous sessions
      if (user.role === 'teacher' || user.role === 'admin') {
        navigation.reset({ index: 0, routes: [{ name: 'TeacherTabs', params: { teacherId: user.id } }] });
      } else {
        navigation.reset({ index: 0, routes: [{ name: 'StudentTabs', params: { studentId: user.id, role: user.role } }] });
      }
    } catch (e: any) {
      console.log('[login] login failed', { email: email.trim(), message: e?.message });
      setError(e?.message || 'Login failed. Please check your credentials.');
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {/* Decorative floating shapes */}
        <Animated.View style={[styles.floatShape, styles.float1, { transform: [{ translateY: float1 }] }]}>
          <Text style={styles.shapeText}>+</Text>
        </Animated.View>
        <Animated.View style={[styles.floatShape, styles.float2, { transform: [{ translateY: float2 }] }]}>
          <Text style={styles.shapeText}>×</Text>
        </Animated.View>

        {/* Header with waving mascot - Welcome Back theme */}
        <View style={styles.hero}>
          <Animated.View
            style={[
              styles.mascotWrap,
              { transform: [{ translateY: mascotBounce }, { rotate }] },
            ]}
          >
            <View style={styles.mascotCircle}>
              <Image source={ANIMAL_IMAGES[18]} style={styles.mascot} resizeMode="contain" />
            </View>
            <View style={styles.waveBadge}>
              <Text style={styles.waveText}>👋</Text>
            </View>
          </Animated.View>

          <Text style={styles.title}>{t.login.greeting}</Text>
          <Text style={styles.subtitle}>{t.login.subtitle}</Text>
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

            {/* Email */}
            <Text style={styles.label}>{t.login.email}</Text>
            <TextInput
              value={email}
              onChangeText={setEmail}
              placeholder={t.login.emailPlaceholder}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />

            {/* Password */}
            <Text style={styles.label}>{t.login.password}</Text>
            <TextInput
              value={password}
              onChangeText={setPassword}
              placeholder={t.login.passwordPlaceholder}
              placeholderTextColor={colors.textMuted}
              style={styles.input}
              secureTextEntry
              autoComplete="password"
            />

            {/* Sign In */}
            <PrimaryButton
              title={t.login.continue}
              onPress={handleSignIn}
              disabled={!isValid}
              loading={loading}
              style={styles.submitBtn}
            />

            {/* Forgot password */}
            <TouchableOpacity style={styles.forgotRow} activeOpacity={0.7}>
              <Text style={styles.forgotText}>{t.login.forgotPassword}</Text>
            </TouchableOpacity>

            {/* Sign up link */}
            <View style={styles.linkRow}>
              <Text style={styles.linkText}>{t.login.noAccount} </Text>
              <TouchableOpacity onPress={() => navigation.replace('SignUp')} activeOpacity={0.7}>
                <Text style={styles.linkAction}>{t.login.signUp}</Text>
              </TouchableOpacity>
            </View>
          </Card>
        </Animated.View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  flex: { flex: 1 },
  container: {
    flexGrow: 1,
    padding: spacing.lg,
    justifyContent: 'center',
  },
  // Floating decorative shapes
  floatShape: {
    position: 'absolute',
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: colors.skyBlueSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  float1: { top: 100, left: 20 },
  float2: { top: 150, right: 20, backgroundColor: colors.warmYellowSoft },
  shapeText: {
    fontSize: 24,
    fontWeight: '900',
    color: colors.primary,
  },
  // Hero section with mascot
  hero: {
    alignItems: 'center',
    marginBottom: spacing.lg,
  },
  mascotWrap: {
    position: 'relative',
    marginBottom: spacing.md,
  },
  mascotCircle: {
    width: 110,
    height: 110,
    borderRadius: 55,
    backgroundColor: colors.warmYellowSoft,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 4,
    borderColor: colors.warmYellow,
    shadowColor: 'rgba(255, 180, 0, 0.3)',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 1,
    shadowRadius: 16,
    elevation: 8,
  },
  mascot: { width: 90, height: 90 },
  waveBadge: {
    position: 'absolute',
    bottom: 0,
    right: -5,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.coral,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.background,
  },
  waveText: { fontSize: 18 },
  title: {
    ...typography.title,
    color: colors.textWarm,
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
  input: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.md,
    padding: spacing.md,
    fontSize: 16,
    color: colors.text,
    borderWidth: 1,
    borderColor: colors.border,
  },
  submitBtn: {
    marginTop: spacing.sm,
  },
  forgotRow: {
    alignItems: 'center',
    marginTop: spacing.md,
  },
  forgotText: {
    ...typography.caption,
    color: colors.textMuted,
    textDecorationLine: 'underline',
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
    color: colors.primary,
    fontWeight: '700',
  },
});
