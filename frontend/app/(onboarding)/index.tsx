import { router } from 'expo-router';
import { useEffect } from 'react';

import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';

/**
 * Real entry point for the (onboarding) group. Routes to whichever step the
 * learner still needs on app boot or re-entry; in-flow forward navigation is
 * handled directly by welcome/teacher-link/classroom-status themselves.
 */
export default function OnboardingIndexRoute() {
  const { me, status } = useAuth();

  useEffect(() => {
    if (status === 'checking') return;

    if (!me?.learnerProfile) {
      router.replace('/(onboarding)/welcome');
      return;
    }

    if (!me.classroomMembership) {
      router.replace('/(onboarding)/teacher-link');
      return;
    }

    router.replace({
      params: { membershipId: me.classroomMembership.membership_id },
      pathname: '/(onboarding)/classroom-status',
    });
  }, [me, status]);

  return (
    <ScreenShell centered>
      <AppText align="center" variant="subtitle">Checking your classroom…</AppText>
    </ScreenShell>
  );
}
