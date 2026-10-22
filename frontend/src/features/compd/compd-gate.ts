// Where the compD tab sends a learner, as pure functions so the rule is tested without a renderer.
//
// The one rule that matters: an ERROR never shows the intro. "We could not ask the server" is not
// "this is your first visit" -- treating it as one would replay the intro to every returning child
// whenever the network blinks.

import type { Href } from 'expo-router';

import { ApiClientError } from '@/src/api/errors';
import type { DLearnerState } from '@/src/features/compd/api/compd-types';

export const COMPD_GATE_HREF = '/(learner)/compd' as Href;
export const COMPD_HOME_HREF = '/(learner)/compd/home' as Href;
export const COMPD_INTRO_HREF = '/(learner)/compd/intro/logo' as Href;

export type CompdGateFailure = 'sign-in-needed' | 'not-a-learner' | 'unreachable';

/**
 * DEVELOPMENT PREVIEW SWITCH (owner request, 2026-10-21: "deactivate the first-time rule, I need to
 * see how those pages render"). With `EXPO_PUBLIC_COMPONENT_D_ALWAYS_SHOW_INTRO=true` in a
 * development build, every compD tab press plays the intro again, whatever the server has stored.
 * It changes WHERE the learner goes inside compD, never who may enter -- and it is inert in any
 * non-development build. Remove the line from .env.local to restore the first-time rule.
 */
export function introAlwaysShown(): boolean {
  return (
    process.env.EXPO_PUBLIC_APP_ENV === 'development' &&
    process.env.EXPO_PUBLIC_COMPONENT_D_ALWAYS_SHOW_INTRO?.trim() === 'true'
  );
}

export function destinationFor(state: DLearnerState): Href {
  if (introAlwaysShown()) return COMPD_INTRO_HREF;
  return state.intro_completed ? COMPD_HOME_HREF : COMPD_INTRO_HREF;
}

/** The compD tab's target: straight home when this session already knows the intro is done. */
export function compdEntryHref(cached: DLearnerState | null): Href {
  if (introAlwaysShown()) return COMPD_GATE_HREF;
  return cached?.intro_completed ? COMPD_HOME_HREF : COMPD_GATE_HREF;
}

export function classifyGateFailure(error: unknown): CompdGateFailure {
  if (!(error instanceof ApiClientError)) return 'unreachable';
  if (error.kind === 'unauthenticated') return 'sign-in-needed';
  // The host's learner check answers 403 for a non-learner account and 404 for an account with no
  // learner yet (B's `_require_learner`); `requestJson` reports 404 as kind 'server', so the status
  // is what distinguishes it from a real server failure.
  if (error.kind === 'forbidden' || error.status === 404) return 'not-a-learner';
  return 'unreachable';
}
