import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';

/**
 * A single-use, in-memory handoff from the Play tab's press handler
 * (adventure-charge-context.tsx's `requestPlay`) to `c-session-screen.tsx`.
 *
 * Unlike the Component B prefetch attempted (and reverted) earlier the same day, this is safe by
 * construction for a structural reason specific to Component C: `next_task` was built to RESUME
 * the session's own pending task rather than mint a new one whenever one is still open
 * (`task_service.py`'s `find_most_recent_for_session`, CONNECT's own resume-instead-of-mint fix) --
 * so calling it from a second call site is, by design, never a duplicate "open," only a repeat
 * read of the same pending task. Component B's `selectOpportunity` carries no such guarantee,
 * which is why that attempt was reverted rather than fixed forward.
 *
 * Keyed by Supabase subject, not session id: Component C holds at most one active session per
 * learner (`getActiveSession` takes no session id at all), so there is nothing else to key on.
 * `take` deletes the entry -- a later real re-fetch (retry, crash recovery, deep link straight to
 * `/c-session`) always falls through to the screen's own normal bootstrap rather than ever reading
 * stale data.
 */
export type CSessionPrefetchResult = { cSessionId: string; task: CNextTaskResponse } | null;

const pending = new Map<string, Promise<CSessionPrefetchResult>>();

export function putCSessionPrefetch(subject: string, promise: Promise<CSessionPrefetchResult>): void {
  pending.set(subject, promise);
}

export function takeCSessionPrefetch(subject: string): Promise<CSessionPrefetchResult> | null {
  const value = pending.get(subject);
  if (value === undefined) return null;
  pending.delete(subject);
  return value;
}
