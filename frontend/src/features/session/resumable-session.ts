// Is there a Component B session to resume?
//
// This lived in session-preparation-screen.tsx, which is where its only caller was until the
// prefetch needed it too. That made b-session-prefetch.ts import the preparation SCREEN, while the
// screen imports the prefetch -- a require cycle, and Metro's warning about one is precise: "can
// result in uninitialized values". A module with no imports of its own cannot be part of a cycle,
// so the function moved here and both sides import it.

import type { ActiveSessionResponse } from '@/src/api/generated/openapi-types';

/**
 * GET /api/v1/b/sessions/active is a UX affordance, not a correctness requirement: it exists so the
 * child sees "Resume" before tapping, instead of discovering it after. POST /api/v1/b/sessions
 * never 409s on an existing session (it takes an advisory lock, finds any starting-or-active
 * session for the learner, and returns it with 201 regardless of idempotency key -- see
 * b_session_lifecycle.py:185-194), so a failed or stale read here is self-correcting: if a session
 * actually exists, starting "a new one" anyway just returns it. That is why this is safe to treat
 * as best-effort -- any failure (including the development fixture, which does not implement this
 * call) degrades silently to the Start label rather than a new error phase.
 */
export async function resolveResumableSessionId(
  api: { getActiveSession: (accessToken: string) => Promise<ActiveSessionResponse> },
  accessToken: string,
): Promise<string | null> {
  try {
    const { session } = await api.getActiveSession(accessToken);
    if (session && session.state === 'active') return session.session_id;
    return null;
  } catch {
    return null;
  }
}
