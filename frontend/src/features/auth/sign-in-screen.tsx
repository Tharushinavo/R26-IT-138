import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { artwork } from '@/src/utils/artwork';
import { type Gender, useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { colors, radius, spacing } from '@/src/theme/tokens';

const brandWordmark = artwork.mathmingoHeader;

type AuthMode = 'sign-in' | 'sign-up';
type SignUpStep = 1 | 2 | 3;

const genderOptions: { label: string; value: Gender }[] = [
  { label: 'Female', value: 'female' },
  { label: 'Male', value: 'male' },
];

/** Preserved email login/account UI; deferred while Component B pages are built. */
export function SignInScreen() {
  const palette = colors;
  const { notice, retryAuthorization, signInWithEmail, signOut, signUpWithEmail, status } =
    useAuth();
  const [mode, setMode] = useState<AuthMode>('sign-in');
  const [signUpStep, setSignUpStep] = useState<SignUpStep>(1);
  const [displayName, setDisplayName] = useState('');
  const [gender, setGender] = useState<Gender | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formMessage, setFormMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const busy = status === 'checking';
  const configurationError = status === 'configuration-error';
  const canSignIn = email.trim().length > 0 && password.length > 0 && !busy && !configurationError;
  const canSignUp =
    displayName.trim().length >= 2 &&
    gender !== null &&
    email.trim().length > 0 &&
    password.length >= 8 &&
    confirmPassword === password &&
    !busy &&
    !configurationError;
  // Sign-up is split into three screens (name+gender / email / password+confirm) so the card
  // never grows taller than the sign-in card does -- each screen shows at most the two fields
  // sign-in itself shows. `signUpStepReady` gates the primary button per screen; `canSignUp`
  // (unchanged) remains the final, whole-form gate `handleSignUp` itself checks against.
  const signUpStep1Ready = displayName.trim().length >= 2 && gender !== null && !busy && !configurationError;
  const signUpStep2Ready = email.trim().length > 0 && !busy && !configurationError;
  const signUpStepReady =
    signUpStep === 1 ? signUpStep1Ready : signUpStep === 2 ? signUpStep2Ready : canSignUp;

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode);
    setSignUpStep(1);
    setFormMessage(null);
    setSuccessMessage(null);
  }

  function handleSignUpNext() {
    setFormMessage(null);
    if (signUpStep === 1) {
      if (!signUpStep1Ready) {
        setFormMessage('Enter your name and select a gender option to continue.');
        return;
      }
      setSignUpStep(2);
      return;
    }
    if (signUpStep === 2 && signUpStep2Ready) setSignUpStep(3);
  }

  function handleSignUpBack() {
    setFormMessage(null);
    setSignUpStep((step) => (step === 3 ? 2 : 1));
  }

  async function handleSignIn() {
    setFormMessage(null);
    setSuccessMessage(null);
    const result = await signInWithEmail(email, password);
    if (!result.ok) setFormMessage(result.message);
  }

  async function handleSignUp() {
    setFormMessage(null);
    setSuccessMessage(null);

    if (!gender) {
      setFormMessage('Select a gender option to continue.');
      return;
    }
    if (password !== confirmPassword) {
      setFormMessage('The passwords do not match.');
      return;
    }

    const result = await signUpWithEmail({ displayName, email, gender, password });
    if (!result.ok) {
      setFormMessage(result.message);
    } else if (result.requiresEmailConfirmation) {
      setMode('sign-in');
      setSignUpStep(1);
      setPassword('');
      setConfirmPassword('');
      setSuccessMessage('Account created. Check your email to confirm it, then sign in.');
    }
  }

  function handlePrimaryPress() {
    if (mode === 'sign-in') {
      void handleSignIn();
      return;
    }
    if (signUpStep < 3) {
      handleSignUpNext();
      return;
    }
    void handleSignUp();
  }

  const displayedMessage = formMessage ?? notice;
  const primaryEnabled = mode === 'sign-in' ? canSignIn : signUpStepReady;
  const primaryLabel = mode === 'sign-in' ? 'LOG IN' : signUpStep < 3 ? 'NEXT' : 'CREATE';
  const headingTitle =
    mode === 'sign-in' ? 'Welcome back' : signUpStep === 1 ? 'Tell us a little about you.' : 'Create your account';

  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: palette.background }]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled">
          <View style={styles.brand}>
            <Image
              accessibilityLabel="MathMingo"
              contentFit="contain"
              source={brandWordmark}
              style={styles.brandWordmark}
            />
          </View>

          <View
            style={[
              styles.card,
              { backgroundColor: palette.surface1, borderColor: palette.border },
            ]}>
            <View style={[styles.modeSwitch, { backgroundColor: palette.primarySoft }]}>
              {(['sign-in', 'sign-up'] as const).map((item) => {
                const selected = mode === item;
                return (
                  <Pressable
                    accessibilityRole="tab"
                    accessibilityState={{ selected }}
                    key={item}
                    onPress={() => changeMode(item)}
                    style={[
                      styles.modeButton,
                      selected && { backgroundColor: palette.surface1, borderColor: palette.border },
                    ]}>
                    <AppText style={styles.modeText}>
                      {item === 'sign-in' ? 'LOG IN' : 'CREATE'}
                    </AppText>
                  </Pressable>
                );
              })}
            </View>

            <View style={styles.heading}>
              <AppText variant="subtitle">{headingTitle}</AppText>
              {mode === 'sign-in' ? (
                <AppText style={{ color: palette.textSecondary }}>
                  Log in to continue learning.
                </AppText>
              ) : null}
            </View>

            {displayedMessage ? (
              <Message color={palette.danger} backgroundColor={palette.dangerSoft} icon="alert-circle-outline">
                {displayedMessage}
              </Message>
            ) : null}

            {successMessage ? (
              <Message color={palette.textPrimary} backgroundColor={palette.primarySoft} icon="checkmark-circle-outline">
                {successMessage}
              </Message>
            ) : null}

            {status === 'unavailable' || status === 'access-denied' ? (
              <View style={styles.recoveryActions}>
                {status === 'unavailable' ? (
                  <Pressable
                    accessibilityRole="button"
                    disabled={busy}
                    onPress={() => void retryAuthorization()}
                    style={styles.textButton}>
                    <AppText>Try again</AppText>
                  </Pressable>
                ) : null}
                <Pressable
                  accessibilityRole="button"
                  disabled={busy}
                  onPress={() => void signOut()}
                  style={styles.textButton}>
                  <AppText>Use another account</AppText>
                </Pressable>
              </View>
            ) : null}

            {mode === 'sign-up' && signUpStep === 1 ? (
              <>
                <Field label="Name">
                  <TextInput
                    accessibilityLabel="Name"
                    autoCapitalize="words"
                    autoComplete="name"
                    editable={!busy && !configurationError}
                    onChangeText={setDisplayName}
                    placeholder="What should we call you?"
                    placeholderTextColor={palette.textMuted}
                    style={[
                      styles.input,
                      {
                        backgroundColor: palette.inputBackground,
                        borderColor: palette.border,
                        color: palette.textPrimary,
                      },
                    ]}
                    textContentType="name"
                    value={displayName}
                  />
                </Field>

                <Field label="Gender">
                  <View accessibilityRole="radiogroup" style={styles.genderGrid}>
                    {genderOptions.map((option) => {
                      const selected = gender === option.value;
                      return (
                        <Pressable
                          accessibilityRole="radio"
                          accessibilityState={{ checked: selected }}
                          key={option.value}
                          onPress={() => setGender(option.value)}
                          style={[
                            styles.genderOption,
                            {
                              backgroundColor: selected ? palette.primarySoft : palette.inputBackground,
                              borderColor: selected ? palette.primaryShadow : palette.border,
                            },
                          ]}>
                          <AppText style={styles.genderText}>{option.label}</AppText>
                        </Pressable>
                      );
                    })}
                  </View>
                </Field>
              </>
            ) : null}

            {mode === 'sign-in' || signUpStep === 2 ? (
            <Field label="Email">
              <TextInput
                accessibilityLabel="Email"
                autoCapitalize="none"
                autoComplete="email"
                editable={!busy && !configurationError}
                keyboardType="email-address"
                onChangeText={setEmail}
                placeholder="learner@example.com"
                placeholderTextColor={palette.textMuted}
                style={[
                  styles.input,
                  {
                    backgroundColor: palette.inputBackground,
                    borderColor: palette.border,
                    color: palette.textPrimary,
                  },
                ]}
                textContentType="username"
                value={email}
              />
            </Field>
            ) : null}

            {mode === 'sign-in' || signUpStep === 3 ? (
            <Field label="Password">
              <TextInput
                accessibilityLabel="Password"
                autoComplete={mode === 'sign-up' ? 'new-password' : 'current-password'}
                editable={!busy && !configurationError}
                onChangeText={setPassword}
                onSubmitEditing={() => mode === 'sign-in' && canSignIn && void handleSignIn()}
                placeholder={mode === 'sign-up' ? 'At least 8 characters' : 'Enter your password'}
                placeholderTextColor={palette.textMuted}
                secureTextEntry
                style={[
                  styles.input,
                  {
                    backgroundColor: palette.inputBackground,
                    borderColor: palette.border,
                    color: palette.textPrimary,
                  },
                ]}
                textContentType={mode === 'sign-up' ? 'newPassword' : 'password'}
                value={password}
              />
            </Field>
            ) : null}

            {mode === 'sign-up' && signUpStep === 3 ? (
              <Field label="Confirm password">
                <TextInput
                  accessibilityLabel="Confirm password"
                  autoComplete="new-password"
                  editable={!busy && !configurationError}
                  onChangeText={setConfirmPassword}
                  placeholder="Enter the password again"
                  placeholderTextColor={palette.textMuted}
                  secureTextEntry
                  style={[
                    styles.input,
                    {
                      backgroundColor: palette.inputBackground,
                      borderColor: palette.border,
                      color: palette.textPrimary,
                    },
                  ]}
                  textContentType="newPassword"
                  value={confirmPassword}
                />
              </Field>
            ) : null}

            <View style={mode === 'sign-up' && signUpStep > 1 ? styles.stepButtonsRow : undefined}>
              {mode === 'sign-up' && signUpStep > 1 ? (
                <Pressable
                  accessibilityRole="button"
                  disabled={busy}
                  onPress={handleSignUpBack}
                  style={({ pressed }) => [
                    styles.secondaryButton,
                    { borderColor: palette.border },
                    pressed && styles.buttonPressed,
                  ]}>
                  <AppText style={[styles.buttonText, { color: palette.textPrimary }]}>BACK</AppText>
                </Pressable>
              ) : null}

              <Pressable
                accessibilityRole="button"
                disabled={!primaryEnabled}
                onPress={handlePrimaryPress}
                style={({ pressed }) => [
                  styles.primaryButton,
                  mode === 'sign-up' && signUpStep > 1 && styles.primaryButtonFlex,
                  {
                    backgroundColor: primaryEnabled ? palette.primary : palette.textDisabled,
                    borderBottomColor: primaryEnabled ? palette.primaryShadow : palette.textDisabled,
                  },
                  pressed && primaryEnabled && styles.buttonPressed,
                ]}>
                {busy ? (
                  <ActivityIndicator color={palette.primaryForeground} />
                ) : (
                  <AppText style={[styles.buttonText, { color: palette.primaryForeground }]}>
                    {primaryLabel}
                  </AppText>
                )}
              </Pressable>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Field({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <View style={styles.fieldGroup}>
      <AppText style={styles.label}>{label}</AppText>
      {children}
    </View>
  );
}

function Message({
  backgroundColor,
  children,
  color,
  icon,
}: {
  backgroundColor: string;
  children: React.ReactNode;
  color: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
}) {
  return (
    <View
      accessibilityLiveRegion="polite"
      accessibilityRole="alert"
      style={[styles.message, { backgroundColor }]}>
      <Ionicons color={color} name={icon} size={22} />
      <AppText style={[styles.messageText, { color }]}>{children}</AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  brand: { alignItems: 'center', gap: spacing.sm },
  buttonPressed: { borderBottomWidth: 0, transform: [{ translateY: 4 }] },
  buttonText: { fontSize: 15, fontWeight: '800', letterSpacing: 0.4 },
  card: {
    borderRadius: radius.lg,
    borderWidth: 2,
    gap: spacing.lg,
    maxWidth: 520,
    padding: spacing.lg,
    width: '100%',
  },
  fieldGroup: { gap: spacing.sm },
  flex: { flex: 1 },
  genderGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  genderOption: {
    borderRadius: radius.md,
    borderWidth: 2,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: spacing.smPlus,
  },
  genderText: { fontSize: 14, fontWeight: '800' },
  heading: { gap: spacing.xs },
  input: {
    borderRadius: radius.md,
    borderWidth: 2,
    fontSize: 17,
    fontWeight: '600',
    minHeight: 56,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  brandWordmark: { aspectRatio: 1916 / 821, height: 136 },
  label: { fontSize: 16, fontWeight: '800' },
  message: {
    alignItems: 'flex-start',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  messageText: { flex: 1, fontSize: 15, lineHeight: 22 },
  modeButton: {
    alignItems: 'center',
    borderColor: 'transparent',
    borderRadius: radius.sm,
    borderWidth: 2,
    flex: 1,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: spacing.sm,
  },
  modeSwitch: { borderRadius: radius.md, flexDirection: 'row', padding: spacing.xs },
  modeText: { fontSize: 13, fontWeight: '800', letterSpacing: 0.3 },
  primaryButton: {
    alignItems: 'center',
    borderBottomWidth: 4,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 60,
    paddingHorizontal: spacing.md,
  },
  primaryButtonFlex: { flex: 1 },
  recoveryActions: { alignItems: 'flex-start', gap: spacing.sm },
  secondaryButton: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 2,
    flex: 1,
    justifyContent: 'center',
    minHeight: 60,
    paddingHorizontal: spacing.md,
  },
  stepButtonsRow: { flexDirection: 'row', gap: spacing.sm },
  safeArea: { flex: 1 },
  scrollContent: {
    alignItems: 'center',
    flexGrow: 1,
    gap: spacing.xl,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xl,
  },
  textButton: { justifyContent: 'center', minHeight: 44 },
});
