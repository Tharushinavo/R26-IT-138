import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { artwork } from '@/src/utils/artwork';
import { createLearnerProfile } from '@/src/api/learner-onboarding-api';
import { ApiClientError } from '@/src/api/errors';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import { readPublicConfig } from '@/src/config/env';
import { colors, radius, spacing } from '@/src/theme/tokens';
import { firstNameOf } from '@/src/utils/display-name';

const brandWordmark = artwork.mathmingoHeader;

export function FirstTimeWelcomeScreen() {
  const palette = colors;
  const { getAccessToken, profileName, retryAuthorization } = useAuth();
  const configResult = useMemo(() => readPublicConfig(), []);
  const [name, setName] = useState(profileName ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const idempotencyKeyRef = useRef(Crypto.randomUUID());

  const trimmedName = name.trim();
  const canSubmit = trimmedName.length > 0 && !submitting;

  async function handleContinue() {
    if (!canSubmit) return;
    const config = configResult.config;
    if (!config) {
      setErrorMessage('The app is not configured yet. Please try again later.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) {
        setErrorMessage('Your session expired. Please sign in again.');
        return;
      }

      await createLearnerProfile(config, accessToken, idempotencyKeyRef.current, {
        name: trimmedName,
      });
      await retryAuthorization();
      router.replace('/(onboarding)/teacher-link');
    } catch (error) {
      if (error instanceof ApiClientError && error.kind === 'invalid-request') {
        // The next attempt sends a corrected body, so it is a new action -> new key.
        idempotencyKeyRef.current = Crypto.randomUUID();
        setErrorMessage('Please check the name and try again.');
      } else {
        // Network/server failure: keep the same key so a retry replays the same request.
        setErrorMessage('We could not save your name. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScreenShell centered>
      <View style={styles.content}>
        <Image
          accessibilityLabel="MathMingo"
          contentFit="contain"
          source={brandWordmark}
          style={styles.brandWordmark}
        />
        <AppText align="center" variant="title">
          Hi{trimmedName ? `, ${firstNameOf(trimmedName)}` : ''}!
        </AppText>
        <AppText align="center" variant="subtitle">Welcome to MathMingo</AppText>

        <TextInput
          accessibilityLabel="Your name"
          autoCapitalize="words"
          autoComplete="name"
          editable={!submitting}
          onChangeText={setName}
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
          value={name}
        />

        {errorMessage ? (
          <View
            accessibilityLiveRegion="polite"
            accessibilityRole="alert"
            style={[styles.errorCard, { backgroundColor: palette.dangerSoft }]}>
            <Ionicons color={palette.danger} name="alert-circle-outline" size={20} />
            <AppText style={[styles.errorText, { color: palette.danger }]}>{errorMessage}</AppText>
          </View>
        ) : null}

        <Pressable
          accessibilityRole="button"
          accessibilityState={{ disabled: !canSubmit }}
          disabled={!canSubmit}
          onPress={() => void handleContinue()}
          style={({ pressed }) => [
            styles.button,
            {
              backgroundColor: canSubmit ? palette.primary : palette.textDisabled,
              borderBottomColor: canSubmit ? palette.primaryShadow : palette.textDisabled,
            },
            pressed && canSubmit && styles.buttonPressed,
          ]}>
          {submitting ? (
            <ActivityIndicator color={palette.primaryForeground} />
          ) : (
            <AppText style={[styles.buttonText, { color: palette.primaryForeground }]}>CONTINUE</AppText>
          )}
        </Pressable>
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    alignSelf: 'stretch',
    borderBottomWidth: 4,
    borderRadius: radius.md,
    justifyContent: 'center',
    minHeight: 60,
    paddingHorizontal: spacing.lg,
  },
  buttonPressed: { borderBottomWidth: 0, transform: [{ translateY: 4 }] },
  buttonText: { fontSize: 15, fontWeight: '800', letterSpacing: 0.4 },
  content: { alignItems: 'center', gap: spacing.lg, maxWidth: 520, width: '100%' },
  errorCard: {
    alignItems: 'flex-start',
    alignSelf: 'stretch',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  errorText: { flex: 1, fontSize: 15, lineHeight: 22 },
  brandWordmark: { aspectRatio: 1916 / 821, height: 136 },
  input: {
    alignSelf: 'stretch',
    borderRadius: radius.md,
    borderWidth: 2,
    fontSize: 17,
    fontWeight: '600',
    minHeight: 56,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
});
