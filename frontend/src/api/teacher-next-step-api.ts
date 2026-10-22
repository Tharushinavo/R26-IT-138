// The learner's next step, as decided by their teacher in Component 3.
//
// SPEC: `Learning-Insight-Early-Warning-System/SHOWING_TEACHER_DECISIONS_IN_THE_STUDENT_APP.md`,
// §4 steps 6-8 ("Student app (other team)"). Component 3 owns the data, the rule about which rows
// may be shown, and the wording; this app only asks and renders.
//
// WHAT THIS FILE DELIBERATELY DOES NOT DO:
//
//   * It does not read `t3_*` tables. §5: "Do not have the student app read t3_* tables directly."
//     Coupling to another team's schema makes every migration of theirs an outage of ours, and it
//     puts their ethical gate outside the codebase that enforces it.
//   * It sends NO student id. §3.1: identity comes from the token, and §5 warns that a
//     `student_id` parameter added "for testing" becomes the way one child reads another's.
//   * It maps nothing. §3.3: the endpoint returns finished sentences and the student app "must not
//     map `proposed_action` to text of its own -- one source of wording, one place to review it."
//     So `headline` and `detail` are rendered verbatim, and this module has no vocabulary of its
//     own to drift from theirs.
//   * It never persists or caches. §4 step 8. There is no module-level store here on purpose --
//     every caller fetches fresh, and the value lives only in the component's own state, so it
//     cannot outlive a screen, let alone an account, on a shared classroom device.
//
// FAIL-CLOSED, AND THAT IS WHAT MAKES IT SAFE TO SHIP EARLY. The endpoint does not exist yet
// (Component 3's §4 steps 1-5 are unbuilt as of 2026-10-10). Every failure -- unconfigured base
// URL, 404, 401, network error, malformed body -- resolves to `null`, which the UI renders as
// nothing at all. So this is inert until Component 3 ships, and becomes live with no change here.

/**
 * Component 3's base URL. Separate from `EXPO_PUBLIC_API_BASE_URL` because it is a DIFFERENT
 * SERVICE owned by a different team -- pointing this at our own backend would 404 every call.
 *
 * Unset means the feature is off: `fetchTeacherNextStep` returns null without making a request.
 * That is the correct default while Component 3's endpoint does not exist, and it means a
 * deployment that never configures this simply never shows the dot.
 */
function componentThreeBaseUrl(): string | null {
  const raw = process.env.EXPO_PUBLIC_T3_API_BASE_URL?.trim();
  if (!raw) return null;
  return raw.replace(/\/+$/, '');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

/**
 * Narrows the §3.1 response to the two fields this app renders.
 *
 * VALIDATED, NOT CAST, and hand-written rather than schema-based to match this codebase's own
 * `runtime-validation.ts` (same `isRecord` / `isNonEmptyString` shape) -- adding a validation
 * dependency for one response would be the larger change.
 *
 * It matters more here than for our own API: this is ANOTHER TEAM's service, so a shape change on
 * their side has to degrade to "show nothing" rather than render `undefined` to a child. Both
 * strings must be non-empty, because an empty `headline` would open a popup with nothing in it --
 * worse than the no-message path, which at least says something true.
 */
function readNextStep(body: unknown): { headline: string; detail: string; disclosure: string | null } | null {
  if (!isRecord(body)) return null;
  const step = body.next_step;
  if (!isRecord(step)) return null; // covers the common `null` case and any malformed one
  if (!isNonEmptyString(step.headline) || !isNonEmptyString(step.detail)) return null;
  return {
    detail: step.detail,
    disclosure: isNonEmptyString(body.disclosure) ? body.disclosure : null,
    headline: step.headline,
  };
}

export type TeacherNextStep = {
  headline: string;
  detail: string;
  /** Component 3's own provenance line, rendered verbatim alongside the message when present. */
  disclosure: string | null;
};

/** How long to wait before giving up. Short: nothing on this screen depends on the answer. */
const REQUEST_TIMEOUT_MS = 6000;

/**
 * Asks Component 3 what this learner's teacher chose for them.
 *
 * Resolves to `null` whenever there is nothing to show OR anything at all went wrong -- the two
 * are deliberately indistinguishable to the caller, because they render identically (§4 step 7:
 * "nothing at all"). A caller that could tell them apart would be tempted to show an error to a
 * child, which is the one thing a profile screen must not do.
 */
export async function fetchTeacherNextStep(accessToken: string): Promise<TeacherNextStep | null> {
  const baseUrl = componentThreeBaseUrl();
  if (!baseUrl || !accessToken) return null;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${baseUrl}/api/v1/t3/me/next-step`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
      method: 'GET',
      signal: controller.signal,
    });
    if (!response.ok) return null;

    return readNextStep(await response.json());
  } catch {
    // Network failure, abort, non-JSON body. Nothing to show, and nothing to say about it.
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
