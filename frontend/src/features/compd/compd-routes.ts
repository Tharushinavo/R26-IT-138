// compD's react-navigation screen NAMES -> MathMingo expo-router paths. Pure (type-only imports), so
// the mapping is tested under the Node test runner without loading the router.

import type { Href } from 'expo-router';

import { COMPD_HOME_HREF } from '@/src/features/compd/compd-gate';

const ROUTES = {
  Logo: '/(learner)/compd/intro/logo',
  Splash: '/(learner)/compd/intro/splash',
  LanguageSelect: '/(learner)/compd/intro/language',
  StudentHome: '/(learner)/compd/home',
  StudentTabs: '/(learner)/compd/home',
  StudentActivity: '/(learner)/compd/activity',
  MathActivity: '/(learner)/compd/activity',
  StudentProfile: '/(learner)/compd/result',
  ProfileResult: '/(learner)/compd/result',
  StudentHistory: '/(learner)/compd/history',
  ProfileHistory: '/(learner)/compd/history',
  // compD's "learning path" was a static screenshot of MathMingo's own Home. Inside MathMingo the
  // button goes to the real thing.
  LearningPath: '/(learner)/home',
} as const;

export type CompdRouteName = keyof typeof ROUTES;

export type NavigateParams = { sessionId?: string; screen?: string; params?: { sessionId?: string } } | undefined;

export function hrefFor(name: string, params: NavigateParams): Href {
  // `StudentTabs` with `{ screen }` was compD's way to jump to one of its tabs.
  const target = name === 'StudentTabs' && params?.screen ? params.screen : name;
  const pathname = ROUTES[target as CompdRouteName] ?? COMPD_HOME_HREF;
  const sessionId = params?.sessionId ?? params?.params?.sessionId;
  return (sessionId ? { params: { sessionId }, pathname } : pathname) as Href;
}
