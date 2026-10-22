import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';
import {
  classifyGateFailure,
  COMPD_INTRO_HREF,
  destinationFor,
  introAlwaysShown,
  type CompdGateFailure,
} from '@/src/features/compd/compd-gate';
import { readCompdLearnerState, writeCompdLearnerState } from '@/src/features/compd/compd-state-cache';
import { colors as compdColors } from '@/src/features/compd/theme';
import { useCompdApi } from '@/src/features/compd/use-compd-api';
import { colors, radius, spacing } from '@/src/theme/tokens';

const FAILURE_COPY: Record<CompdGateFailure, { title: string; body: string; action: string }> = {
  'sign-in-needed': {
    title: 'Please sign in again',
    body: 'Your session has ended.',
    action: 'Sign in',
  },
  'not-a-learner': {
    title: 'Almost there!',
    body: 'Please finish setting up your learner account first.',
    action: 'Go home',
  },
  unreachable: {
    title: "We can't reach compD right now",
    body: 'Check the connection and try again.',
    action: 'Try again',
  },
};

/**
 * compD's entry point. Routes to the first-run intro or to compD's home from the SERVER's learner
 * state; with a cached state it routes at once and revalidates in the background. A failure shows
 * a message and never the intro (see compd-gate.ts).
 */
export function CompdGateScreen() {
  const { signOut } = useAuth();
  const { call, subject } = useCompdApi();
  const [failure, setFailure] = useState<CompdGateFailure | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    // With the preview switch on the destination is always the intro, so go now, not after the read.
    const cached = readCompdLearnerState(subject);
    const routedEarly = introAlwaysShown() || cached !== null;
    if (introAlwaysShown()) router.replace(COMPD_INTRO_HREF);
    else if (cached) router.replace(destinationFor(cached));

    void call((api, accessToken) => api.getLearnerState(accessToken)).then(
      (state) => {
        // Written even after this screen has gone: refreshing the cache is the whole point of the
        // background read when we already routed from it.
        writeCompdLearnerState(subject, state);
        if (!cancelled && !routedEarly) router.replace(destinationFor(state));
      },
      (error: unknown) => {
        if (!cancelled && !routedEarly) setFailure(classifyGateFailure(error));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [attempt, call, subject]);

  // Owner request 2026-10-21: no "Opening compD" loading screen. While the read is in flight the
  // area between the header and tab bar is plain compD background, so the intro or home just appears.
  if (!failure) return <View style={styles.waiting} />;

  const copy = FAILURE_COPY[failure];
  const act = () => {
    if (failure === 'sign-in-needed') void signOut();
    else if (failure === 'not-a-learner') router.replace('/(learner)/home');
    else {
      setFailure(null);
      setAttempt((value) => value + 1);
    }
  };

  return (
    <ScreenShell centered>
      <AppText align="center" variant="title">{copy.title}</AppText>
      <AppText align="center" style={styles.body}>{copy.body}</AppText>
      <Pressable
        accessibilityRole="button"
        onPress={act}
        style={({ pressed }) => [styles.button, pressed && styles.buttonPressed]}>
        <AppText style={styles.buttonText}>{copy.action}</AppText>
      </Pressable>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  body: { color: colors.textSecondary },
  button: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderBottomColor: colors.primaryShadow,
    borderBottomWidth: 4,
    borderRadius: radius.md,
    marginTop: spacing.md,
    minWidth: 200,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  buttonPressed: { borderBottomWidth: 1, transform: [{ translateY: 3 }] },
  buttonText: { color: colors.textOnPrimary, fontWeight: '800', textTransform: 'uppercase' },
  waiting: { backgroundColor: compdColors.background, flex: 1 },
});
