// Pure decision logic for the live session screen (FE-3b), deliberately split out of
// live-session-screen.tsx so every branch this batch introduces is testable under the existing
// `node:test` + `tsx` runner. Nothing here imports react, react-native, expo-*, or the API client;
// the screen keeps only layout, state wiring and the actual network calls. (RNTL is Batch 15.)
//
// Scope reminder: this module decides what to render and how to classify what came back. It never
// judges an answer. `AttemptResponse` is authoritative for correctness, and `submitted_value` is
// built by FE-3a's `encodeSubmittedValue`, not here.

import type {
  PendingRequestAssistCommand,
  PendingSessionCommand,
  PendingSubmitResponseCommand,
} from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import type {
  AttemptResponse,
  HintRequestResponse,
  OpportunityAdvanceResponse,
  OpportunityPresentationFields,
} from '@/src/api/generated/openapi-types';
import { resolveRenderer } from '@/src/features/session/renderers/registry';
import type { AnswerState, RendererSpec } from '@/src/features/session/renderers/types';

// --- skill label ------------------------------------------------------------------------------

/**
 * Turn a catalogue `skill_id` into something a child can read: `number_sense` → "Number Sense".
 *
 * Underscore-split and title-case only. It does not map ids to curated display names — a lookup
 * table here would be catalogue content restated in the client, free to drift from the backend's
 * own skill set. An unrecognized or oddly-shaped id therefore degrades to a readable
 * approximation rather than to a blank or a thrown error.
 */
export function formatSkillLabel(skillId: string): string {
  const words = skillId
    .split(/[_\s-]+/)
    .map((word) => word.trim())
    .filter((word) => word.length > 0);
  if (words.length === 0) return '';
  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

// --- presentation → renderable plan -------------------------------------------------------------

export type SessionPlan =
  | {
      kind: 'render';
      spec: RendererSpec;
      stem: string;
      // The server's authored instruction sentence for templates whose stem is not a question on
      // its own -- "Guess the next number." above a bare "2, 3, 4, __". Server-supplied and
      // relayed verbatim, exactly like `stem`: the app never composes one (see the backend's
      // app/domain/live_engine/prompt_instructions.py for why it is authored there). `null` for
      // every template whose stem already states its own task, which is most of them.
      instruction: string | null;
      // The whole prompt payload, carried through unmodified for FE-3g's visual registry to read.
      // `stem` above stays the only *text* taken from it; this is not a licence to render arbitrary
      // keys as prose. Nothing here inspects or transforms it — the registry decides what is
      // drawable, and fails closed to stem-only when nothing is.
      promptPayload: Record<string, unknown>;
      skillLabel: string;
      // The raw wire id, carried alongside its formatted `skillLabel` for callers that need the id
      // itself rather than the child-readable version — the card's accent colour, keyed off this
      // exact string by session-skill-accents.ts, not off the display label.
      skillId: string;
      itemOpportunityId: string;
      requestId: string;
      timeoutDeadlineUtc: string;
    }
  // Structural drift: an unknown response_format, one whose presented_choices do not match it, or
  // a presentation with no usable stem (which `isOpportunityPresentationFields` should already
  // have rejected — this is belt-and-braces, and kept distinguishable in the support code path).
  // The screen renders a neutral error. It must never degrade to a free-text box — see
  // resolveRenderer's own comment for why that specific fallback is harmful.
  | {
      kind: 'unrenderable';
      reason: 'unsupported-format' | 'missing-stem';
      requestId: string;
      responseFormat: string;
    };

/**
 * `prompt` is an open `Record<string, unknown>` on the wire and carries more than the stem
 * (numbers, options, direction, …). This batch renders the stem and nothing else; improvising a
 * richer prompt renderer from keys whose semantics are per-template is explicitly out of scope.
 */
export function readPromptStem(prompt: Record<string, unknown>): string | null {
  const stem = prompt.stem;
  if (typeof stem !== 'string') return null;
  const trimmed = stem.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * The server's authored instruction, when the template has one. Read exactly like `stem` -- a
 * non-string or blank value is `null`, never a guess. A missing instruction is the normal case
 * (most stems ask their own question) and is NOT an unrenderable item: unlike `stem`, this being
 * absent never blocks the question, it just means there is no extra sentence to draw.
 */
export function readPromptInstruction(prompt: Record<string, unknown>): string | null {
  const instruction = prompt.instruction;
  if (typeof instruction !== 'string') return null;
  const trimmed = instruction.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * `presented_choices` is passed to the registry — and from there to the screen — in the server's
 * order, untouched. The server sorts lexicographically, so a child may see 10, 3, 9; that is a
 * backend issue tracked separately, and re-sorting here would be the client transforming server
 * data. `representation_type` is "numeral" for all 36 templates today and is treated as opaque:
 * nothing branches on it.
 */
// `requestId` is supplied separately rather than read off the presentation, because the two
// sources of a question do not carry it the same way. `POST /opportunities` returns an
// `OpportunityPresentationResponse`, which has its own `request_id`. But the question that arrives
// inline on an advance is an `OpportunityPresentationFields` — the *fields* shape, with no
// `request_id` of its own. For that one the correct support code is the advance response's
// `request_id`: that is the request which produced the question, and it is what a grown-up would
// quote. (`OpportunityPresentationResponse` is structurally a superset of the fields shape, so the
// original call site still passes its own response and its own request id.)
export function planPresentation(
  presentation: OpportunityPresentationFields,
  requestId: string,
): SessionPlan {
  const spec = resolveRenderer(presentation.response_format, presentation.presented_choices);
  const stem = readPromptStem(presentation.prompt);
  if (!spec || !stem) {
    return {
      kind: 'unrenderable',
      reason: spec ? 'missing-stem' : 'unsupported-format',
      requestId,
      responseFormat: presentation.response_format,
    };
  }
  return {
    kind: 'render',
    spec,
    stem,
    instruction: readPromptInstruction(presentation.prompt),
    promptPayload: presentation.prompt,
    skillLabel: formatSkillLabel(presentation.skill_id),
    skillId: presentation.skill_id,
    itemOpportunityId: presentation.item_opportunity_id,
    requestId,
    timeoutDeadlineUtc: presentation.server_timeout_deadline_utc,
  };
}

// --- advancing ------------------------------------------------------------------------------------

// Progress is whatever the server reported, carried through unmodified. There is no client-side
// counter and no client-side bound: the server's per-session opportunity cap is an unapproved
// engineering placeholder, not a governed session length. Nothing here hardcodes it, and no copy
// treats reaching it as an achievement — dressing a placeholder up as a milestone ("you did them
// all!") would make it much harder to change later. Neutral progress only.
//
// The literal itself is deliberately not written anywhere in this file, not even in a comment:
// session-advance.test.ts greps for it bluntly, and a guard with exemptions is a guard nobody
// trusts. See that test for the full reasoning.
export type SessionProgress = { completed: number; totalBound: number };

export type AdvanceDecision =
  // The next question arrived inline on the advance response. It is rendered directly — calling
  // POST /opportunities again would be a second round trip for a presentation already in hand,
  // and latency a child pays for nothing.
  | { kind: 'next'; plan: SessionPlan; progress: SessionProgress }
  | { kind: 'completed'; progress: SessionProgress }
  // Structural drift: the server said neither "here is the next question" nor "the session is
  // over". Rather than guessing which it meant, the screen re-asks POST /opportunities and renders
  // whatever comes back — the same fail-closed move FE-3b makes on a 409.
  | { kind: 'drift' };

export function decideAdvance(response: OpportunityAdvanceResponse): AdvanceDecision {
  const progress: SessionProgress = {
    completed: response.opportunities_completed,
    totalBound: response.opportunities_total_bound,
  };
  if (response.next_opportunity === null) {
    return response.session_state === 'completed' ? { kind: 'completed', progress } : { kind: 'drift' };
  }
  // A question alongside `session_state: 'completed'` contradicts the contract (the bound being
  // reached is exactly what makes next_opportunity null). Answering into a session the server
  // considers finished is the worse guess, so this fails closed too.
  if (response.session_state !== 'active') return { kind: 'drift' };
  return {
    kind: 'next',
    plan: planPresentation(response.next_opportunity, response.request_id),
    progress,
  };
}

// --- results ---------------------------------------------------------------------------------------

/**
 * The completed value to display. Clamped to the bound so a server anomaly (or a drifted bound)
 * can never render a completed count larger than the total at a child, and floored at zero for
 * the same reason. (Deliberately phrased without an example pair: the bound guard below scans
 * this file's whole source, comments included, and an illustrative "N of M" would leak the very
 * literal the guard exists to keep out — the same trip FE-3e hit.)
 *
 * The numbers come from the completion response the client already holds — `GET /summary` is
 * deliberately not called on this path (see `component-b-api.ts`'s note on `getSessionSummary`).
 */
export function clampCompleted(progress: SessionProgress): number {
  return Math.max(0, Math.min(progress.completed, progress.totalBound));
}

export type ResultsView = { headline: string; detail: string };

/**
 * The whole results surface: counts, and nothing else.
 *
 * `outcomeHistory` is accepted and **deliberately ignored**, and that is the point of the
 * parameter existing at all. The client does observe every `response_matched` as a session runs. It
 * must never accumulate them into a score, a count of correct answers, a percentage, stars, a
 * streak, a per-skill breakdown, or any other derived summary.
 *
 * The reason is governance, not minimalism. The backend deliberately withholds an evaluative
 * summary from the child-facing surface; a client that assembled one from responses it happened to
 * see would be synthesising exactly the thing that was withheld — a governance violation wearing
 * the costume of a helpful feature.
 *
 * SCOPE NARROWED 2026-10-20, and the narrowing is the point. The owner has ruled that the results
 * SCREEN may also draw per-skill mastery bars showing what moved during the session, so it is no
 * longer true that two children see an identical screen. THIS FUNCTION's guarantee is unchanged
 * and still enforced: the COPY — headline and detail — is byte-identical for every outcome
 * history, carries no score, and never reads `outcomeHistory`. The bars are drawn from the
 * server's own `p_l` values fetched separately (session-mastery-change.ts), never from responses
 * this client observed, which is the distinction that keeps the original rule intact where it
 * still applies. Do not derive anything evaluative from `outcomeHistory` here.
 *
 * Passing the history in and ignoring it makes that testable: a unit test asserts the copy is
 * byte-identical across every outcome history, which is the strongest available guard that nothing
 * evaluative has leaked in. If you are here to "fix" the missing score, this comment is the answer:
 * it is not missing.
 */
// `outcomeHistory` is intentionally never read in the body. Do not delete the parameter to tidy it
// away — it exists so that ignoring it is testable, per the note above.
export function resultsView(
  progress: SessionProgress,
  outcomeHistory?: readonly AttemptOutcome[],
): ResultsView {
  const completed = clampCompleted(progress);
  const noun = progress.totalBound === 1 ? 'question' : 'questions';
  return {
    // Warm about finishing, silent about performing.
    headline: 'All done!',
    detail: `You finished ${completed} of ${progress.totalBound} ${noun} today.`,
  };
}

/**
 * Advancing requires at least one recorded attempt — `attempt_count < 1` raises 409
 * (`session_completion.py:321-325`). The control is gated on the child having submitted, so the
 * ordinary path never spends a request discovering that. A recorded TIMEOUT counts: it is an
 * attempt row, which is why FE-3c's "always let them submit" rule is what makes the session
 * advanceable at all.
 */
export function canAdvance(hasRecordedAttempt: boolean): boolean {
  return hasRecordedAttempt;
}

// --- answer state seeds ---------------------------------------------------------------------

/**
 * The "nothing chosen yet" state for each surface. `chosenIndex: -1` and `count: -1` are sentinels
 * that `encodeSubmittedValue` already rejects, so submit starts unavailable without the screen
 * needing a second "has the child touched this?" flag. Note `count: 0` is a real answer (an empty
 * set) and must stay submittable — which is exactly why the seed is -1, not 0.
 */
export function initialAnswerState(spec: RendererSpec): AnswerState {
  if (spec.kind === 'choice') return { kind: 'choice', chosenIndex: -1 };
  if (spec.kind === 'free-entry') return { kind: 'free-entry', rawInput: '' };
  return { kind: 'count-selection', count: -1 };
}

// --- the timeout deadline ------------------------------------------------------------------------

/**
 * Whether the server's timeout deadline for this question has passed, according to the device
 * clock. Advisory only — the server evaluates `now >= opportunity.timeout_deadline_utc` itself at
 * submit time (attempt_submission.py:213) and the `event_kind` it returns is the only truth.
 *
 * The comparison is `>=`, matching the server's. An unparseable deadline is treated as *not*
 * passed: the fail-safe direction is always the one that keeps the child able to answer, and the
 * server decides regardless.
 *
 * No duration is hardcoded here or anywhere else in the session modules. The bound is unapproved
 * policy and exists only in the server's response; a literal in the client would both duplicate it
 * and be wrong the moment it changed. (`no-timeout-literal.test.ts` enforces that.)
 */
export function isDeadlinePassed(deadlineUtc: string, now: number): boolean {
  const deadline = Date.parse(deadlineUtc);
  if (Number.isNaN(deadline)) return false;
  return now >= deadline;
}

export type AnswerSurfaceState = {
  submitting: boolean;
  hasOutcome: boolean;
  deadlinePassed: boolean;
};

/**
 * Whether the answer surface (and the submit button) should be inert.
 *
 * `deadlinePassed` is accepted and then **deliberately ignored**. This is not an oversight, and it
 * must not be "fixed":
 *
 *   - No server-side sweep records timeouts. A TIMEOUT is only ever written when the *client*
 *     submits after the deadline (attempt_submission.py:213-229).
 *   - Advancing past an opportunity requires at least one recorded attempt or timeout
 *     (session_completion.py:22).
 *
 * So disabling input once the deadline passes would leave the child holding the only key to a lock
 * they can no longer reach: no submit → no recorded TIMEOUT → no advance → the session is soft-
 * locked on that question, permanently. The child must always be able to select and submit. The
 * server sets `submitted_value = None` and never compares the answer on a timeout, so submitting
 * "late" costs nothing and is the only thing that unblocks the session.
 *
 * The same holds at mount with a skewed device clock: a phone set hours ahead must not stop a
 * child answering. Interactivity never keys off the clock.
 */
export function isAnswerSurfaceDisabled(state: AnswerSurfaceState): boolean {
  return state.submitting || state.hasOutcome;
}

// --- pending-command replay -------------------------------------------------------------------

export type PendingReplayDecision =
  | { action: 'replay'; command: PendingSubmitResponseCommand }
  | { action: 'discard' }
  | { action: 'none' };

/**
 * Decide what to do with a locally persisted submit command when the server hands back an
 * opportunity on mount.
 *
 * A match is replayed *verbatim* — same idempotency key, same body. Same key means the server
 * returns the original attempt instead of recording a second one, and the body must be the saved
 * one because the server fingerprints the request body into the idempotency record: a body
 * rebuilt at replay time would fail the fingerprint check (and `client_elapsed_ms` is
 * unrecoverable after a relaunch anyway).
 *
 * A submit command for a different opportunity is stale — that question has already moved on — so
 * it is discarded rather than sent. Commands of other kinds are left alone: the shared store slot
 * also holds `start_session`, which the prep screen owns.
 */
export function decidePendingReplay(
  pending: PendingSessionCommand | null,
  sessionId: string,
  itemOpportunityId: string,
): PendingReplayDecision {
  if (!pending || pending.kind !== 'submit_response') return { action: 'none' };
  if (pending.sessionId !== sessionId) return { action: 'discard' };
  if (pending.itemOpportunityId !== itemOpportunityId) return { action: 'discard' };
  return { action: 'replay', command: pending };
}

// --- hints ---------------------------------------------------------------------------------------

// A 409 from POST .../assists is the NORMAL response, not an error path: only 2 of the 36
// templates carry hint content, so roughly 94% of the time a child asks for help there is none to
// give. Everything below is built for that as the default case.
//
// The service maps every one of these to the same neutral ConflictError: no hint content for this
// template, blank hint content, a catalogue/bundle checksum mismatch, and "already at L3"
// (hint_request.py). Its docstring is explicit that this is to "fail closed, never synthesize or
// approximate, never reveal the correct answer through the error path." That neutrality is a
// governance property, not an oversight — the client must not try to infer which 409 it got. The
// information genuinely is not there, and any attempt to guess works against the design.
//
// The server derives the level itself from its own count of prior hint events, under the
// opportunity row lock: strictly L1 → L2 → L3, single-step. The client never requests or sends a
// level. And a hint is never a mastery/BKT observation — separate table, separate path — so asking
// for help costs the child nothing anywhere in the science.

export type HintAvailability = 'available' | 'unavailable';

export type HintState = {
  itemOpportunityId: string;
  // Accumulated, never replaced: L2 elaborates on L1, and a child who has lost L1 off-screen has
  // lost the scaffold it was giving them. Kept in level order.
  received: readonly HintRequestResponse[];
  availability: HintAvailability;
};

// Mirrors the server's strict L1 → L2 → L3 ladder, and is used for exactly one thing: not sending
// a fourth request whose 409 is already certain. It is not an authority — the 409 path is, and it
// produces the identical `unavailable` state — so if the ladder ever lengthens server-side the
// only cost here is one wasted request, never a wrong state.
const HIGHEST_HINT_LEVEL = 3;

export function initialHintState(itemOpportunityId: string): HintState {
  return { itemOpportunityId, received: [], availability: 'available' };
}

/**
 * Hint state is scoped per `item_opportunity_id` and reset whenever the question changes. Keying
 * on the opportunity id rather than on a mount or a counter is what makes this stay correct when
 * FE-3e starts advancing the loop in place.
 */
export function hintStateFor(state: HintState | null, itemOpportunityId: string): HintState {
  if (state && state.itemOpportunityId === itemOpportunityId) return state;
  return initialHintState(itemOpportunityId);
}

/**
 * Record a delivered hint. Ordered by level and de-duplicated by level, so replaying a persisted
 * idempotency key — which returns the original level and content — re-renders rather than
 * duplicating.
 */
export function recordHint(state: HintState, hint: HintRequestResponse): HintState {
  const received = state.received.some((existing) => existing.hint_level === hint.hint_level)
    ? state.received
    : [...state.received, hint].sort((a, b) => a.hint_level - b.hint_level);
  return {
    ...state,
    received,
    availability:
      hint.hint_level >= HIGHEST_HINT_LEVEL ? 'unavailable' : state.availability,
  };
}

/**
 * A 409 closes the door for this opportunity and it stays closed.
 *
 * A 409 on the very first request (the 34-of-36 case: this template simply has no hint content)
 * and a 409 after L3 (the ladder is exhausted) are handled *identically* and are indistinguishable
 * here by design — see the neutrality note above. There is deliberately no separate "you have used
 * them all" branch: the server does not tell us which happened, and a client that guessed would be
 * inventing a distinction the governance boundary exists to erase.
 */
export function markHintsUnavailable(state: HintState): HintState {
  return { ...state, availability: 'unavailable' };
}

export function canRequestHint(state: HintState): boolean {
  return state.availability === 'available';
}

// Neutral and forward-pointing. A child who has just admitted they need help must not be met with
// something that reads as a rebuff ("No hints available"), as blame for having asked, or as help
// being withheld as a consequence. Asking is always fine; sometimes there is simply nothing extra
// to give for this particular question.
export const HINTS_UNAVAILABLE_COPY = 'No extra help for this one — have a go!';

export type PendingAssistDecision =
  | { action: 'reuse'; command: PendingRequestAssistCommand }
  | { action: 'fresh' };

/**
 * Whether a persisted assist command can be reused for the request the child just asked for.
 *
 * This is a real correctness point, not boilerplate. If an assist request succeeds but its
 * response is lost — network drop, app kill — retrying with a *fresh* key makes the server count
 * the first event and escalate: the child silently never sees L1, the gentlest hint, and lands on
 * L2 instead. Replaying the saved key returns the original level and content with no
 * re-escalation.
 */
export function decidePendingAssist(
  pending: PendingSessionCommand | null,
  sessionId: string,
  itemOpportunityId: string,
): PendingAssistDecision {
  if (!pending || pending.kind !== 'request_assist') return { action: 'fresh' };
  if (pending.sessionId !== sessionId) return { action: 'fresh' };
  if (pending.itemOpportunityId !== itemOpportunityId) return { action: 'fresh' };
  return { action: 'reuse', command: pending };
}

// --- outcome classification --------------------------------------------------------------------

// `AttemptResponse` is authoritative. `isAttemptResponse` already enforces the cross-field
// invariant (response_matched is null iff event_kind is TIMEOUT), so this is a total mapping over
// what a validated response can actually be.
export type AttemptOutcome = 'correct' | 'incorrect' | 'timeout';

/**
 * TIMEOUT is never an incorrect answer. The child did not answer at all — the server's five-minute
 * deadline simply passed, which is reachable in this batch with no countdown UI at all, just by
 * thinking for a while. Showing it as "wrong" would tell a child they got something wrong that
 * they never got the chance to get right. (The full timeout experience is FE-3c; not mishandling
 * it is this batch's job.)
 */
export function classifyAttemptOutcome(attempt: AttemptResponse): AttemptOutcome {
  if (attempt.event_kind === 'TIMEOUT') return 'timeout';
  return attempt.response_matched === true ? 'correct' : 'incorrect';
}

// Copy is neutral in every branch: encouraging for a match, invitational for a miss, and
// explicitly not blaming for a timeout. There is no client-side attempt cap — attempt limits are
// unapproved placeholders and the client must not invent one — so 'incorrect' always offers
// another try.
export type OutcomeView = { title: string; detail: string; canTryAgain: boolean };

export function outcomeView(outcome: AttemptOutcome): OutcomeView {
  if (outcome === 'correct') {
    return { title: 'Nice work!', detail: 'That one is right.', canTryAgain: false };
  }
  if (outcome === 'timeout') {
    return { title: "Time's up", detail: "Let's keep going.", canTryAgain: false };
  }
  // No detail copy: an unbounded "try as many times as you like" claim tracked the same
  // unapproved absence of a client-side attempt cap as the sentence above once did, restated as an
  // invitation instead of a limit — removed at the user's request rather than reworded, since
  // `canTryAgain: true` already carries everything this screen needs to know to offer TRY AGAIN.
  return { title: 'Not quite', detail: '', canTryAgain: true };
}

// --- failure classification ---------------------------------------------------------------------

export type SessionFailure =
  // 409 on submit. The screen re-calls /opportunities and re-renders whatever the server returns.
  // It never applies a client-side rule about what "should" have happened.
  | 'conflict'
  | 'authentication'
  | 'network'
  | 'technical';

export function classifyFailure(error: unknown): SessionFailure {
  if (!(error instanceof ApiClientError)) return 'technical';
  if (error.kind === 'conflict') return 'conflict';
  if (error.kind === 'unauthenticated' || error.kind === 'forbidden') return 'authentication';
  if (error.kind === 'network' || error.kind === 'timeout') return 'network';
  return 'technical';
}

export function failureRequestId(error: unknown): string | null {
  return error instanceof ApiClientError && error.requestId ? error.requestId : null;
}
