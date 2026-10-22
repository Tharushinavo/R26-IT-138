import type { LearnerSkillStateItem } from '@/src/api/generated/openapi-types';

// The learner's skill states as they stood when a session STARTED, so the results screen can show
// what moved (owner decision, 2026-10-20).
//
// WHY THIS EXISTS AT ALL. The server has no "before" to give: `GET /api/v1/b/learner/skill-states`
// returns the CURRENT `p_l` per skill and nothing historical. So the only way to show a change is
// to photograph the starting state on the client and compare at the end. Nothing is derived here --
// this module stores what the server said, verbatim, and hands it back.
//
// THIS IS A DELIBERATE REVERSAL OF A RECORDED RULE, not an oversight. `live-session-logic.ts`'s
// `resultsView` states that the results surface carries "no per-skill breakdown, no mastery figure"
// and that "a child who got everything wrong and a child who got everything right see the identical
// screen, by design". The owner has decided otherwise; see buildLog2.md's 2026-10-20 entry for the
// decision and its two known costs. Do not treat the existence of this module as permission to add
// further evaluative surfaces -- the ruling is about this one screen.
//
// IN MEMORY, KEYED BY SESSION, AND NEVER PERSISTED. Three reasons, all load-bearing:
//   * a snapshot is meaningless outside the session it belongs to, so the session id is the key;
//   * this app runs on shared classroom devices, and one child's mastery must never be shown
//     against another's -- the same rule `home-session-state-cache.ts` follows;
//   * the results screen is already documented as not surviving a reload ("the app keeps no
//     learner-facing record of performance"), and persisting this would quietly make it do so.
//
// A MISSING SNAPSHOT IS A SUPPORTED STATE, not an error. A reload mid-session, a direct link into
// the results route, or a session started before this shipped all leave nothing to compare against.
// The screen then shows current mastery with no "before" marker and no movement, which is honest --
// it says nothing rather than implying no progress was made.

const snapshots = new Map<string, readonly LearnerSkillStateItem[]>();

/** Photographs the starting state. Later calls for the same session are IGNORED. */
export function captureMasterySnapshot(
  sessionId: string,
  states: readonly LearnerSkillStateItem[] | null | undefined,
): void {
  if (!sessionId || !states) return;
  // FIRST WRITE WINS. The session screen can re-run its bootstrap (a remount, a retry, a
  // crash-recovery resume), and each of those happens AFTER questions have been answered. Letting
  // a later call overwrite would quietly re-baseline the snapshot to a mid-session state and make
  // the child's own progress disappear from the screen.
  if (snapshots.has(sessionId)) return;
  snapshots.set(sessionId, states);
}

/** The starting state for this session, or null if none was captured. */
export function readMasterySnapshot(sessionId: string): readonly LearnerSkillStateItem[] | null {
  return snapshots.get(sessionId) ?? null;
}

/** Drops one session's snapshot. */
export function dropMasterySnapshot(sessionId: string): void {
  snapshots.delete(sessionId);
}

/** Drops every snapshot. For sign-out, so the next account starts with nothing to compare. */
export function clearMasterySnapshots(): void {
  snapshots.clear();
}
