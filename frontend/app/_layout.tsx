import {
  Nunito_600SemiBold,
  Nunito_700Bold,
  Nunito_800ExtraBold,
  Nunito_900Black,
  useFonts,
} from '@expo-google-fonts/nunito';
import { DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Asset } from 'expo-asset';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { type PropsWithChildren, useEffect, useState } from 'react';
import { InteractionManager } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import 'react-native-reanimated';

import { AuthProvider, useAuth } from '@/src/auth/auth-context';
import { colors } from '@/src/theme/tokens';
import { artworkWarmUpOrder, criticalArtwork } from '@/src/utils/artwork';
import { warmArtworkInOrder } from '@/src/utils/artwork-warm-up';

void SplashScreen.preventAutoHideAsync();

const navigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.surface1,
    text: colors.textPrimary,
    border: colors.border,
  },
};

function RootNavigator() {
  const { status } = useAuth();
  const authorized = status === 'authorized';
  const learnerAccess = authorized || status === 'preview';
  const onboarding = status === 'onboarding';

  return (
    <ThemeProvider value={navigationTheme}>
      <Stack screenOptions={{ animation: 'none', headerShown: false }}>
        <Stack.Screen name="index" />
        <Stack.Protected guard={!learnerAccess && !onboarding}>
          <Stack.Screen name="(auth)" />
        </Stack.Protected>
        <Stack.Protected guard={onboarding}>
          <Stack.Screen name="(onboarding)" />
        </Stack.Protected>
        <Stack.Protected guard={learnerAccess}>
          <Stack.Screen name="(learner)" />
        </Stack.Protected>
      </Stack>
      <StatusBar style="dark" />
    </ThemeProvider>
  );
}

/**
 * How long the splash may wait on authorization before giving up and showing the app anyway.
 *
 * The splash now waits for auth as well as for local resources (FE-016), which means a dead or
 * very slow network could otherwise hold a child on a static image indefinitely. Past this
 * ceiling the app renders regardless and `app/index.tsx` shows its own "Checking secure access…"
 * copy -- i.e. the OLD behaviour becomes the timeout path rather than the normal one.
 */
const SPLASH_AUTH_CEILING_MS = 2500;

/**
 * Holds the splash until the app is genuinely ready to be looked at, then hides it (FE-016).
 *
 * WHY THIS IS A SEPARATE COMPONENT, under `AuthProvider` rather than beside it. The decision needs
 * `useAuth().status`, which is only readable from inside the provider. That constraint is also
 * what fixed the bigger problem: `RootLayout` used to `return null` until fonts and artwork had
 * settled, and `AuthProvider` is one of the children that `null` withheld -- so session
 * restoration did not even BEGIN until every image had decoded, and the two costs added up
 * instead of overlapping. The provider is now mounted immediately and this gate withholds only
 * the navigator, so auth starts at t=0 and runs underneath the splash.
 *
 * WHY `ready` LATCHES. `status` returns to 'checking' later in normal use -- `authorizeSession`
 * sets it on every sign-in, and `retryAuthorization` sets it again. Without the latch, that would
 * re-enter this gate long after startup and unmount the whole navigator mid-session. Once the app
 * has been shown it stays shown; this gate is about the first paint only.
 */
function SplashGate({ children, localReady }: PropsWithChildren<{ localReady: boolean }>) {
  const { status } = useAuth();
  const [ceilingReached, setCeilingReached] = useState(false);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setCeilingReached(true), SPLASH_AUTH_CEILING_MS);
    return () => clearTimeout(timer);
  }, []);

  // 'checking' is the one status that means "we do not yet know where this child belongs". Every
  // other value -- authorized, onboarding, signed-out, and each failure -- is a real destination
  // that index.tsx can route to immediately, so none of them should hold the splash.
  const authSettled = status !== 'checking';
  const ready = shown || (localReady && (authSettled || ceilingReached));

  useEffect(() => {
    if (!ready || shown) return;
    setShown(true);
    void SplashScreen.hideAsync();
  }, [ready, shown]);

  if (!ready) return null;
  return <>{children}</>;
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Nunito_600SemiBold,
    Nunito_700Bold,
    Nunito_800ExtraBold,
    Nunito_900Black,
  });

  /**
   * The splash used to wait for FONTS ONLY, so every picture in the app began loading after it had
   * already been torn down -- the tab bar and the hero artwork visibly popped in a beat late on
   * each screen. Decoding them behind the splash, which the child is looking at anyway, means the
   * first frame of the real UI is complete.
   *
   * `settled`, not `loaded`: a preload FAILURE must let the app through. Artwork that will not
   * decode should cost a picture, never the whole app -- exactly the rule the local storage layer
   * follows. Expo Go also fetches these over Metro rather than from a bundle, so this is slower in
   * development than in a release build, where they are read from local disk.
   */
  const [artworkSettled, setArtworkSettled] = useState(false);
  useEffect(() => {
    let cancelled = false;
    const settle = () => {
      if (!cancelled) setArtworkSettled(true);
    };
    // `criticalArtwork`, not `allArtwork` (FE-015): only what the first frame after the splash can
    // actually draw. See src/utils/artwork.ts for which images that is and why.
    Asset.loadAsync([...criticalArtwork]).then(settle, settle);
    return () => {
      cancelled = true;
    };
  }, []);

  const fontsSettled = fontsLoaded || fontError;
  const localReady = Boolean(fontsSettled) && artworkSettled;

  /**
   * All artwork decoded into the image cache, in order (Home, B prep, C prep, C prep 2, B
   * results), once the splash is down and the first interactions have had the thread. That is the
   * sign-in screen for a signed-out child, so Home is already decoded when sign-in finishes.
   * `runAfterInteractions` rather than a bare effect so this decode cannot compete with the first
   * frame -- the whole point of deferring it was to stop paying for it up front, and doing it
   * eagerly here would simply move the cost rather than defer it. Order and caching:
   * `artworkWarmUpOrder` (src/utils/artwork.ts) and `warmArtworkInOrder`.
   *
   * Best-effort: nothing reads the outcome, and a failure leaves the screens that use these images
   * to load them on demand exactly as they would have.
   */
  useEffect(() => {
    if (!localReady) return;
    let cancelled = false;
    const task = InteractionManager.runAfterInteractions(() => {
      void warmArtworkInOrder(artworkWarmUpOrder, () => cancelled);
    });
    return () => {
      cancelled = true;
      task.cancel();
    };
  }, [localReady]);

  return (
    // Required by `react-native-gesture-handler` (used by `value-token-row.tsx`'s NP-04 reorder
    // drag, 10a) at the root of the app, on every platform including web -- without it, gestures
    // fail to register touches at all. Missing since 10a shipped; added 2026-08-26 once the owner
    // found NP-04's drag genuinely did not respond in the browser. `style={{ flex: 1 }}` so this
    // wrapper fills the screen rather than sizing to its own (empty) content.
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        {/* AuthProvider is OUTSIDE the gate on purpose: it is what makes session restoration run
            underneath the splash instead of after it. SplashGate withholds only the navigator. */}
        <AuthProvider>
          <SplashGate localReady={localReady}>
            <RootNavigator />
          </SplashGate>
        </AuthProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
