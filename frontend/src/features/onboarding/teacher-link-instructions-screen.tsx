import { Ionicons } from '@expo/vector-icons';
import * as Crypto from 'expo-crypto';
import { router } from 'expo-router';
import { useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, TextInput, View } from 'react-native';

import type { InviteResolveResponse } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import { resolveClassroomInvite, requestClassroomMembership } from '@/src/api/learner-onboarding-api';
import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import { readPublicConfig } from '@/src/config/env';
import { colors, radius, spacing } from '@/src/theme/tokens';

type JoinPhase = 'entering' | 'resolving' | 'preview' | 'confirming';

const gradeLabels: Record<InviteResolveResponse['grade'], string> = {
  GRADE_2: '2',
  GRADE_3: '3',
};

// Mirrors the server's own join-code format (classroom_membership.py's _JOIN_CODE_LENGTH=8,
// grouped 4-4, e.g. "M7KP-4X9D") purely for display. The resolve/request endpoints already
// accept the code case-insensitively with separators ignored, so this is a readability aid
// only — it does not change what gets sent, and does not restrict which characters are typed.
function formatInviteTokenInput(raw: string): string {
  const alphanumeric = raw.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 8);
  if (alphanumeric.length <= 4) return alphanumeric;
  return `${alphanumeric.slice(0, 4)}-${alphanumeric.slice(4)}`;
}

function previewParts(resolution: InviteResolveResponse): { label: string; suffix: string } {
  if (resolution.classroom_name) {
    return { label: resolution.classroom_name, suffix: ' — is that the correct classroom?' };
  }
  const gradeLabel = gradeLabels[resolution.grade];
  return { label: `This Grade ${gradeLabel} classroom`, suffix: ' — is that the correct classroom?' };
}

/** Learner-entered join code, previewed and confirmed against the real classroom-invite contract. */
export function TeacherLinkInstructionsScreen() {
  const palette = colors;
  const { getAccessToken } = useAuth();
  const configResult = useMemo(() => readPublicConfig(), []);
  const [inviteToken, setInviteToken] = useState('');
  const [phase, setPhase] = useState<JoinPhase>('entering');
  const [resolution, setResolution] = useState<InviteResolveResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const resolveKeyRef = useRef(Crypto.randomUUID());
  const membershipKeyRef = useRef(Crypto.randomUUID());

  const trimmedToken = inviteToken.trim();
  const canCheckCode = trimmedToken.length > 0 && phase === 'entering';

  function backToEntering(message: string | null) {
    setPhase('entering');
    setResolution(null);
    setErrorMessage(message);
  }

  async function handleCheckCode() {
    if (!canCheckCode) return;
    const config = configResult.config;
    if (!config) {
      setErrorMessage('The app is not configured yet. Please try again later.');
      return;
    }

    setPhase('resolving');
    setErrorMessage(null);
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) {
        backToEntering('Your session expired. Please sign in again.');
        return;
      }

      const response = await resolveClassroomInvite(config, accessToken, resolveKeyRef.current, {
        invite_token: trimmedToken,
      });
      setResolution(response);
      setPhase('preview');
    } catch (error) {
      if (error instanceof ApiClientError && (error.kind === 'invalid-request' || error.status === 404)) {
        // A corrected code is a new action -> new resolve key next time.
        resolveKeyRef.current = Crypto.randomUUID();
        backToEntering("We couldn't find a classroom with that code. Check it with your teacher and try again.");
      } else {
        backToEntering('We could not check that code. Please try again.');
      }
    }
  }

  async function handleConfirm() {
    const config = configResult.config;
    if (!config) {
      setErrorMessage('The app is not configured yet. Please try again later.');
      return;
    }

    setPhase('confirming');
    setErrorMessage(null);
    try {
      const accessToken = await getAccessToken();
      if (!accessToken) {
        backToEntering('Your session expired. Please sign in again.');
        return;
      }

      const membership = await requestClassroomMembership(config, accessToken, membershipKeyRef.current, {
        invite_token: trimmedToken,
      });
      router.replace({
        pathname: '/(onboarding)/classroom-status',
        params: { membershipId: membership.classroom_membership_id },
      });
    } catch (error) {
      if (error instanceof ApiClientError && error.kind === 'invalid-request') {
        membershipKeyRef.current = Crypto.randomUUID();
        backToEntering('That code could not be used. Check it with your teacher and try again.');
      } else {
        setPhase('preview');
        setErrorMessage('We could not connect to that classroom. Please try again.');
      }
    }
  }

  const preview = resolution ? previewParts(resolution) : null;

  return (
    <ScreenShell centered>
      <View style={styles.content}>
        <View style={[styles.iconCircle, { backgroundColor: palette.primarySoft }]}>
          <Ionicons color={palette.textPrimary} name="key-outline" size={42} />
        </View>
        <AppText align="center" variant="title">Connect your teacher</AppText>

        {phase === 'entering' || phase === 'resolving' ? (
          <>
            <AppText align="center" style={{ color: palette.textSecondary }}>
              Ask your teacher for the classroom code.
            </AppText>
            <TextInput
              accessibilityLabel="Classroom join code"
              autoCapitalize="characters"
              autoCorrect={false}
              editable={phase === 'entering'}
              onChangeText={(text) => setInviteToken(formatInviteTokenInput(text))}
              placeholder="e.g. M7KP-4X9D"
              placeholderTextColor={palette.textMuted}
              style={[
                styles.input,
                {
                  backgroundColor: palette.inputBackground,
                  borderColor: palette.border,
                  color: palette.textPrimary,
                },
              ]}
              value={inviteToken}
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
              accessibilityState={{ disabled: !canCheckCode }}
              disabled={!canCheckCode}
              onPress={() => void handleCheckCode()}
              style={({ pressed }) => [
                styles.continueButton,
                {
                  backgroundColor: canCheckCode ? palette.primary : palette.textDisabled,
                  borderBottomColor: canCheckCode ? palette.primaryShadow : palette.textDisabled,
                },
                pressed && canCheckCode && styles.buttonPressed,
              ]}>
              {phase === 'resolving' ? (
                <ActivityIndicator color={palette.primaryForeground} />
              ) : (
                <AppText style={[styles.continueText, { color: palette.primaryForeground }]}>CHECK CODE</AppText>
              )}
            </Pressable>
          </>
        ) : null}

        {(phase === 'preview' || phase === 'confirming') && resolution && preview ? (
          <>
            <View style={[styles.previewCard, { backgroundColor: palette.primarySoft }]}>
              <Ionicons color={palette.textPrimary} name="school-outline" size={24} />
              <AppText style={styles.previewText}>
                <AppText style={styles.previewName}>{preview.label}</AppText>
                {preview.suffix}
              </AppText>
            </View>

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
              disabled={phase === 'confirming'}
              onPress={() => void handleConfirm()}
              style={({ pressed }) => [
                styles.continueButton,
                { backgroundColor: palette.primary, borderBottomColor: palette.primaryShadow },
                pressed && phase !== 'confirming' && styles.buttonPressed,
              ]}>
              {phase === 'confirming' ? (
                <ActivityIndicator color={palette.primaryForeground} />
              ) : (
                <AppText style={[styles.continueText, { color: palette.primaryForeground }]}>YES, THAT&apos;S RIGHT</AppText>
              )}
            </Pressable>

            <Pressable
              accessibilityRole="button"
              disabled={phase === 'confirming'}
              onPress={() => backToEntering(null)}
              style={styles.textButton}>
              <AppText>Try a different code</AppText>
            </Pressable>
          </>
        ) : null}
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  buttonPressed: { borderBottomWidth: 0, transform: [{ translateY: 4 }] },
  content: { alignItems: 'center', gap: spacing.lg, maxWidth: 560, width: '100%' },
  continueButton: {
    alignItems: 'center',
    alignSelf: 'stretch',
    borderRadius: radius.md,
    borderBottomWidth: 4,
    justifyContent: 'center',
    minHeight: 60,
    paddingHorizontal: spacing.lg,
  },
  continueText: { fontSize: 15, fontWeight: '800', letterSpacing: 0.4 },
  errorCard: {
    alignItems: 'flex-start',
    alignSelf: 'stretch',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
  },
  errorText: { flex: 1, fontSize: 15, lineHeight: 22 },
  iconCircle: {
    alignItems: 'center',
    borderRadius: radius.xl,
    height: 88,
    justifyContent: 'center',
    width: 88,
  },
  input: {
    alignSelf: 'stretch',
    borderRadius: radius.md,
    borderWidth: 2,
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: 2,
    minHeight: 56,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    textAlign: 'center',
  },
  previewCard: {
    alignItems: 'flex-start',
    alignSelf: 'stretch',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing.smPlus,
    padding: spacing.md,
  },
  previewName: { fontWeight: '800' },
  previewText: { flex: 1, fontSize: 16, fontWeight: '500' },
  textButton: { justifyContent: 'center', minHeight: 44 },
});
