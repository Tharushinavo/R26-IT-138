// compD's screens were written for react-navigation: they receive `{ navigation, route }` props and
// navigate by screen NAME. Inside MathMingo they are expo-router routes. Rather than rewrite every
// navigation call in screens of up to 1,200 lines, `withCompdScreen` hands each screen the props it
// expects, and `useCompdNavigation` translates compD's screen names into routes (compd-routes.ts).
//
// Only `sessionId` is ever carried as a route parameter. compD used to pass `studentId` everywhere;
// the server now takes the learner from the access token, so no learner id appears in a URL.

import { router, useLocalSearchParams } from 'expo-router';
import { useMemo, type ComponentType } from 'react';

import { COMPD_HOME_HREF } from '@/src/features/compd/compd-gate';
import { hrefFor, type NavigateParams } from '@/src/features/compd/compd-routes';

export type CompdNavigation = {
  navigate: (name: string, params?: NavigateParams) => void;
  replace: (name: string, params?: NavigateParams) => void;
  reset: (state: { routes: { name: string; params?: NavigateParams }[] }) => void;
  goBack: () => void;
  /** compD set native header options; compD pages draw their own header, so this does nothing. */
  setOptions: (options: unknown) => void;
};

/** Leaving compD (only the learning path does) replaces, so Back does not return into compD's stack. */
function leavesCompd(name: string) {
  return name === 'LearningPath';
}

export function useCompdNavigation(): CompdNavigation {
  return useMemo<CompdNavigation>(
    () => ({
      navigate: (name, params) => {
        if (leavesCompd(name)) router.replace(hrefFor(name, params));
        else router.push(hrefFor(name, params));
      },
      replace: (name, params) => router.replace(hrefFor(name, params)),
      reset: (state) => {
        const last = state.routes[state.routes.length - 1];
        router.replace(last ? hrefFor(last.name, last.params) : COMPD_HOME_HREF);
      },
      // After a reload there is no history to pop; compD home is the safe place to land.
      goBack: () => (router.canGoBack() ? router.back() : router.replace(COMPD_HOME_HREF)),
      setOptions: () => undefined,
    }),
    [],
  );
}

export type CompdScreenProps = {
  navigation: CompdNavigation;
  route: { params: { sessionId?: string } };
};

/** Mounts a compD screen with the `{ navigation, route }` props it was written against. */
export function withCompdScreen(Screen: ComponentType<CompdScreenProps>) {
  return function CompdRoute() {
    const navigation = useCompdNavigation();
    const { sessionId } = useLocalSearchParams<{ sessionId?: string }>();
    const route = useMemo(() => ({ params: { sessionId: typeof sessionId === 'string' ? sessionId : undefined } }), [sessionId]);
    return <Screen navigation={navigation} route={route} />;
  };
}
