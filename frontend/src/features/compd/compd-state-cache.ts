import type { DLearnerState } from '@/src/features/compd/api/compd-types';

/**
 * The last Component D learner state the server confirmed in this app session, per learner.
 *
 * WHY IT EXISTS. The compD tab must go straight to compD's home once the intro has been seen
 * (owner requirement). Asking the server on every press would put a loading screen in front of
 * the child each time; reading this lets the tab bar route directly and the gate revalidate in the
 * background.
 *
 * Same rules as home-session-state-cache.ts: keyed by Supabase subject so a shared classroom
 * device never shows one child another's state; in memory only, so a relaunch asks the server;
 * `forget` is called from sign-out. It only decides where to GO first -- the gate still asks the
 * server, and the server's answer always wins.
 */
const lastKnown = new Map<string, DLearnerState>();

export function readCompdLearnerState(subject: string | null): DLearnerState | null {
  if (!subject) return null;
  return lastKnown.get(subject) ?? null;
}

/** Records a state the server actually returned -- never a guess made while a request failed. */
export function writeCompdLearnerState(subject: string | null, state: DLearnerState): void {
  if (!subject) return;
  lastKnown.set(subject, { intro_completed: state.intro_completed, language: state.language });
}

export function forgetCompdLearnerState(subject: string | null): void {
  if (!subject) return;
  lastKnown.delete(subject);
}

export function clearCompdLearnerStates(): void {
  lastKnown.clear();
}
