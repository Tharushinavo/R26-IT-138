import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  TextInput,
  View,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import { useLanguage } from '../i18n/LanguageContext';
import { colors, radius, spacing, typography } from '../theme';

type Props = NativeStackScreenProps<RootStackParamList, 'SignUp'>;

const STUDENT_KEY = 'mm.studentId';
const NAME_KEY = 'mm.name';
const ROLE_KEY = 'mm.role';

export default function SignUpScreen({ navigation }: Props) {
  const { t } = useLanguage();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'student' | 'teacher'>('student');
  const [loading, setLoading] = useState(false);

  const isValid = name.trim().length > 0 && email.trim().length > 0 && password.length >= 4;

  async function handleSignUp() {
    if (!isValid) return;
    setLoading(true);

    const studentId = `S_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
    await AsyncStorage.setItem(STUDENT_KEY, studentId);
    await AsyncStorage.setItem(NAME_KEY, name.trim());
    await AsyncStorage.setItem(ROLE_KEY, role);

    setLoading(false);

    if (role === 'teacher') {
      navigation.replace('TeacherDashboard', { teacherId: studentId });
    } else {
      navigation.replace('StudentDashboard', { studentId, role });
    }
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.flex}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        {/* Header */}
        <View style={styles.hero}>
          <View style={styles.iconCircle}>
            <Text style={{ fontSize: 36 }}>✨</Text>
          </View>
          <Text style={styles.title}>{t.signUp.title}</Text>
          <Text style={styles.subtitle}>{t.signUp.subtitle}</Text>
        </View>

        <Card style={styles.card}>
          {/* Name */}
          <Text style={styles.label}>{t.signUp.fullName}</Text>
          <TextInput
            value={name}
            onChangeText={setName}
            placeholder={t.signUp.namePlaceholder}
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            autoCapitalize="words"
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
          />

          {/* Role */}
          <Text style={[styles.label, { marginTop: spacing.sm }]}>{t.signUp.iAmA}</Text>
          <View style={styles.roleRow}>
            <TouchableOpacity
              style={[styles.roleBtn, role === 'student' && styles.roleBtnActive]}
              onPress={() => setRole('student')}
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 28 }}>🧒</Text>
              <Text style={[styles.roleText, role === 'student' && styles.roleTextActive]}>
                {t.signUp.studentLabel}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.roleBtn, role === 'teacher' && styles.roleBtnActive]}
              onPress={() => setRole('teacher')}
              activeOpacity={0.7}
            >
              <Text style={{ fontSize: 28 }}>👩‍🏫</Text>
              <Text style={[styles.roleText, role === 'teacher' && styles.roleTextActive]}>
                {t.signUp.teacherLabel}
              </Text>
            </TouchableOpacity>
          </View>

          {/* Submit */}
          <PrimaryButton
            title={t.signUp.createAccount}
            onPress={handleSignUp}
            disabled={!isValid}
            loading={loading}
          />

          {/* Sign in link */}
          <View style={styles.linkRow}>
            <Text style={styles.linkText}>{t.signUp.alreadyHaveAccount} </Text>
            <TouchableOpacity onPress={() => navigation.replace('Login')} activeOpacity={0.7}>
              <Text style={styles.linkAction}>{t.signUp.signIn}</Text>
            </TouchableOpacity>
          </View>
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: colors.background },
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xxl,
  },
  hero: {
    alignItems: 'center',
    marginTop: spacing.sm,
    marginBottom: spacing.lg,
  },
  iconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    borderWidth: 3,
    borderColor: '#FFE082',
    shadowColor: 'rgba(255, 180, 0, 0.3)',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 1,
    shadowRadius: 8,
    elevation: 4,
  },
  title: {
    ...typography.title,
    color: colors.textWarm,
    textAlign: 'center',
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  card: {
    gap: spacing.md,
  },
  label: {
    ...typography.caption,
    color: colors.textWarm,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  input: {
    backgroundColor: colors.surfaceSoft,
    borderRadius: radius.xl,
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
    fontSize: 16,
    color: colors.text,
    borderWidth: 2,
    borderColor: colors.border,
  },
  roleRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  roleBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.md,
    borderRadius: radius.xl,
    backgroundColor: colors.surfaceSoft,
    borderWidth: 2.5,
    borderColor: colors.border,
    gap: spacing.xs,
  },
  roleBtnActive: {
    borderColor: colors.warmYellow,
    backgroundColor: '#FFF8E0',
  },
  roleText: {
    ...typography.caption,
    color: colors.textMuted,
  },
  roleTextActive: {
    color: colors.textWarm,
    fontWeight: '700',
  },
  linkRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  linkText: {
    ...typography.body,
    color: colors.textMuted,
  },
  linkAction: {
    ...typography.subtitle,
    color: colors.coral,
  },
});
