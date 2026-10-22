import type { HomeSessionState } from '@/src/features/home/session-progress';

/**
 * The last Home session state this app session actually resolved, per learner, so returning to
 * Home re-renders what the child last saw instead of flashing back to "Ready to Play".
 *
 * THE BUG THIS FIXES. `learner-home-screen.tsx` seeds its state with `{ kind: 'not-in-progress' }`
 * and only replaces it once TWO sequential network reads finish (`getActiveSession`, then
 * `getSessionSummary`). Home unmounts on every navigation, so each return to it repainted the
 * neutral panel -- "Ready to Play", question 1 "Start here" -- and then snapped to the real
 * "Your Session" panel with questions already answered. Owner report, 2026-10-10: visible every
 * time, going to Component C or Profile and back. The slower the link, the longer a child is
 * looking at a screen that says they have not started the session they are halfway through.
 *
 * WHY A CACHE RATHER THAN A SPINNER. A spinner would replace a wrong panel with no panel, which is
 * not better: the child still cannot see their progress, and Home's whole discipline (see
 * `combineHomeSessionState`) is that this screen never blocks and never shows an error where the
 * path was. Rendering the last known state and quietly revalidating keeps the screen truthful
 * about the last thing the server actually said, and self-corrects within one read.
 *
 * KEYED BY SUPABASE SUBJECT, the same key `b-session-prefetch-cache.ts` uses, so one learner's
 * progress can never be shown to another on a device that switches accounts. `forget` exists for
 * sign-out; a key that is never written simply reads as "nothing known", which renders exactly the
 * neutral state Home used to start from -- so a cold start is unchanged.
 *
 * IN MEMORY ONLY, deliberately. This is a render-continuity aid within one app session, not a
 * persistence layer: a relaunch should ask the server rather than trust a value that may be hours
 * stale and cannot be invalidated by anything that happened while the app was closed.
 *
 * NOT A SOURCE OF TRUTH. Nothing may branch on this to decide what to DO -- starting or resuming a
 * session still goes through the server, whose `POST /b/sessions` returns an existing session
 * anyway. It only decides what to DRAW while the real answer is in flight.
 */
const lastKnown = new Map<string, HomeSessionState>();

/** The last resolved state for this learner, or null if this app session has not resolved one. */
export function readHomeSessionState(subject: string | null): HomeSessionState | null {
  if (!subject) return null;
  return lastKnown.get(subject) ?? null;
}

/**
 * Records a state the server actually confirmed.
 *
 * MUST be called for a definitive not-in-progress answer too, not only for in-progress -- a
 * finished session has to be able to clear a cached in-progress value. The caller's rule is:
 * remember what the server SAID, never what a failed read could not tell us.
 */
export function writeHomeSessionState(subject: string | null, state: HomeSessionState): void {
  if (!subject) return;
  lastKnown.set(subject, state);
}

/** Drops one learner's entry. For sign-out, so the next account starts from the neutral state. */
export function forgetHomeSessionState(subject: string | null): void {
  if (!subject) return;
  lastKnown.delete(subject);
}

/** Drops every entry. Exported for sign-out paths that do not know the outgoing subject. */
export function clearHomeSessionStates(): void {
  lastKnown.clear();
}
