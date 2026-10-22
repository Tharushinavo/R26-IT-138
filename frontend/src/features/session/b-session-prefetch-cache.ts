import type { OpportunityPresentationResponse } from '@/src/api/generated/openapi-types';

/**
 * A single-use, in-memory handoff from Home's hero button (learner-home-screen.tsx's
 * `openBLearning`) through the preparation screen to `live-session-screen.tsx`, so the child sees
 * ONE loading surface (the prep screen's own artwork) instead of two.
 *
 * WHY THIS IS SAFE, given the earlier attempt this supersedes. c-session-prefetch-cache.ts says a
 * Component B prefetch "was reverted rather than fixed forward" because "Component B's
 * `selectOpportunity` carries no such guarantee" of resuming rather than minting. That is no
 * longer true, and the note is stale: `select_next_opportunity`
 * (app/application/opportunity_selection.py) now takes a per-learner advisory lock, then calls
 * `find_open_for_session` and RE-ISSUES an already-OPEN opportunity via
 * `reissue_presentation_for_open_opportunity` -- the BE4e crash-recovery path -- minting only when
 * the session has none open. So a second caller is a repeat read of the same question, never a
 * duplicate open, exactly as Component C's `next_task` is.
 *
 * THE CLOCK DOES NOT RUN DURING THIS PREFETCH. Corrected 2026-10-10; the paragraph that used to
 * sit here claimed the opposite and was wrong.
 *
 * What it said: that `timeout_deadline_utc` is fixed at creation and never reset, so "every second
 * between this prefetch and the child seeing the question is spent from their answering budget."
 * The first half is true of a RE-ISSUE and only of a re-issue. The conclusion does not follow,
 * because a separate route anchors the deadline afterwards: `POST .../presented` ->
 * `anchor_presentation` (opportunity_persistence.py) sets BOTH `presented_at_utc` and
 * `timeout_deadline_utc = now + timeout` on the first acknowledgement, and
 * `live-session-screen.tsx` sends it when the question renders. The five minutes therefore start
 * when the child can actually see the question, and the deadline written at selection is a
 * fail-safe that is normally overwritten before it can matter.
 *
 * The backend says so explicitly: "Anchoring at selection charged the child for server and network
 * time -- prefetch included -- which is exactly that [infrastructure failure being learner
 * failure]." First acknowledgement wins; later ones are no-ops returning the same deadline, so a
 * remount can neither extend nor shorten what the child has.
 *
 * WHAT STILL FOLLOWS FROM THE ORIGINAL PARAGRAPH: nothing about the prefetch, but the timeout
 * mechanics it describes are accurate and worth keeping. No server sweep records timeouts; one is
 * written only when the client submits after the deadline, and the server then sets
 * `submitted_value = None` and never grades the answer (live-session-logic.ts's own note). The one
 * residual exposure is a FAILED acknowledgement, where the selection-time fail-safe is what the
 * submission is judged against -- which is why that request is retried once (see the PRESENTATION
 * ACKNOWLEDGEMENT effect in live-session-screen.tsx).
 *
 * AUTO-ADVANCE IS UNCHANGED, and its justification is now stated correctly. The preparation screen
 * still auto-advances a prefetched fresh start (owner ruling, 2026-09-27; reaffirmed 2026-10-10),
 * but NOT because it protects the answering budget -- it does not need to. It is a continuity and
 * fewer-taps decision: the child sees one loading surface, the prep screen's own artwork, instead
 * of that plus "Getting your question ready...". Do not re-justify it on clock grounds.
 *
 * Keyed by Supabase subject rather than session id, because the session id is one of the things
 * being prefetched. `take` deletes the entry, so any later re-entry (retry, relaunch, deep link
 * straight to /session/[id]) falls through to live-session-screen's own normal
 * `presentOpportunity` rather than ever reading stale data.
 */
export type BSessionPrefetchResult = {
  sessionId: string;
  presentation: OpportunityPresentationResponse;
} | null;

const pending = new Map<string, Promise<BSessionPrefetchResult>>();

export function putBSessionPrefetch(subject: string, promise: Promise<BSessionPrefetchResult>): void {
  pending.set(subject, promise);
}

export function takeBSessionPrefetch(subject: string): Promise<BSessionPrefetchResult> | null {
  const value = pending.get(subject);
  if (value === undefined) return null;
  pending.delete(subject);
  return value;
}

/** Reads without consuming -- the prep screen needs to know whether to auto-advance before the
 * session screen consumes the entry. */
export function peekBSessionPrefetch(subject: string): Promise<BSessionPrefetchResult> | null {
  return pending.get(subject) ?? null;
}

export function dropBSessionPrefetch(subject: string): void {
  pending.delete(subject);
}
