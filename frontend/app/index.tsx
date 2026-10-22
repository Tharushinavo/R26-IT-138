import { Redirect, type Href } from 'expo-router';

import { useAuth } from '@/src/auth/auth-context';
import { AppText } from '@/src/components/app-text';
import { ScreenShell } from '@/src/components/screen-shell';

/**
 * Page 0 bootstrap route.
 * Page 1 will replace this temporary redirect with secure session restoration
 * and backend authorization before choosing an application destination.
 */
export default function BootstrapRoute() {
  const { status } = useAuth();

  if (status === 'checking') {
    return (
      <ScreenShell centered>
        <AppText align="center" variant="subtitle">Checking secure access…</AppText>
      </ScreenShell>
    );
  }

  if (status === 'authorized' || status === 'preview') {
    return <Redirect href="/(learner)/home" />;
  }
  // "/(onboarding)" (the group-index shorthand) is a valid runtime route — confirmed live: it
  // resolves to app/(onboarding)/index.tsx, which then forwards to the right onboarding step.
  // Expo Router's generated route-literal union does not include the bare group shorthand (only
  // fully-qualified leaf paths), so this is a known typed-routes gap, not a real invalid route.
  if (status === 'onboarding') return <Redirect href={'/(onboarding)' as Href} />;
  return <Redirect href="/(auth)/sign-in" />;
}
