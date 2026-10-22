// Pure decision logic for the C session shell, split out of c-session-screen.tsx so every branch
// this batch introduces is testable under the existing `node:test` + `tsx` runner -- the same split
// live-session-logic.ts uses for Component B, and for the same reason: nothing here imports react,
// react-native, or the API client. This module decides what to render and where to route a failure.
// It never judges an answer, never decides a mathematical level, and never chooses when a session
// ends -- the server is authoritative on all three.

import type { ComponentType } from 'react';

import { ApiClientError } from '@/src/api/errors';
import type {
  CActiveSessionResponse,
  CNextTaskResponse,
  CreateCSessionRequest,
  CSubmitActionResult,
} from '@/src/api/generated/openapi-types';
import type { ArchetypeSurfaceProps } from '@/src/features/c-session/archetype-surfaces';
import { resolveArchetype, type ArchetypeId } from '@/src/features/c-session/archetypes/registry';

// --- task resolution -----------------------------------------------------------------------

export type TaskPlan =
  | { kind: 'archetype'; archetypeId: ArchetypeId; task: CNextTaskResponse }
  | { kind: 'fail-closed' };

/**
 * `resolveArchetype` returning `null` (unknown template id, or a `valid_action_space` carrying an
 * unbound declared type) is the ONLY thing that produces `'fail-closed'` here. A known template id
 * with every declared type bound always produces `'archetype'`, even though no surface exists yet
 * for any of the eight ids in this batch -- that is a separate fact the screen layer checks via
 * archetype-surfaces.ts, not this function's concern. Keeping the two facts apart is what makes
 * this function's own negative control real: a resolvable template must visibly take the
 * `'archetype'` branch, not silently share the `'fail-closed'` one for a different reason.
 */
export function planTask(task: CNextTaskResponse): TaskPlan {
  const archetypeId = resolveArchetype(task.game_task_template_id, task.valid_action_space);
  if (archetypeId === null) return { kind: 'fail-closed' };
  return { kind: 'archetype', archetypeId, task };
}

// --- task surface resolution ----------------------------------------------------------------

export type TaskSurfacePlan =
  | { kind: 'mount'; task: CNextTaskResponse; Surface: ComponentType<ArchetypeSurfaceProps> }
  | { kind: 'fail-closed'; reason: 'unresolvable-template' | 'no-surface-registered' };

/**
 * Composes `planTask` with surface resolution into the one decision the screen actually needs:
 * mount a surface, or fail closed. There is no rendering library in this project's devDependencies
 * (`@types/react`, `eslint`, `eslint-config-expo`, `tsx`, `typescript` only), so nothing can mount a
 * component tree to prove the screen renders correctly -- this function exists so the decision
 * itself is provable without one, mirroring `planTask`, `decideSessionBootstrap` and
 * `classifySessionFailure`'s own split from the screen.
 *
 * The resolver is a parameter, not an import of archetype-surfaces.ts's concrete table, so this
 * function is testable with a fake resolver that never touches the real registry. The screen passes
 * `resolveArchetypeSurface` itself.
 *
 * Both `ComponentType` and `ArchetypeSurfaceProps` above are `import type` only -- this module still
 * imports no react, react-native or API client value at runtime, matching this file's own header.
 *
 * The two fail-closed reasons are kept apart rather than collapsed, because `planTask`'s own doc
 * comment draws this distinction deliberately: an unresolvable template is a wire-shape problem,
 * while a resolved archetype with no registered surface is a "not built yet" problem. They already
 * rendered identically (both `FailClosedFrame`) before this function existed and still do -- this is
 * what makes the distinction checkable by a test rather than merely asserted in a comment.
 */
export function planTaskSurface(
  task: CNextTaskResponse,
  resolveSurface: (archetypeId: ArchetypeId) => ComponentType<ArchetypeSurfaceProps> | null,
): TaskSurfacePlan {
  const plan = planTask(task);
  if (plan.kind === 'fail-closed') return { kind: 'fail-closed', reason: 'unresolvable-template' };
  const Surface = resolveSurface(plan.archetypeId);
  if (!Surface) return { kind: 'fail-closed', reason: 'no-surface-registered' };
  return { kind: 'mount', task, Surface };
}

// --- submission outcome ----------------------------------------------------------------------

export type SubmissionOutcome =
  | { kind: 'advance' }
  | { kind: 'retry'; scaffoldLevel: string };

/**
 * Turn one `CSubmitActionResult` into the screen's next move: advance to the next task, or stay on
 * this one and let the child retry. `response_matched` is the server's verdict, read and relayed --
 * this function never computes correctness, never inspects what the child submitted, and never
 * compares a submitted value against anything. It exists so that fact is provable (a source-scan
 * test can assert this function's only input is the already-validated result type, never the
 * submitted payload) rather than merely asserted in a comment.
 *
 * `scaffoldLevel` is carried through verbatim on a retry, exactly as the server sent it --
 * `scaffold_level` is a plain string on the wire (`CSubmitActionResult`), not a closed enum this
 * codebase owns, so an unexpected value is relayed rather than rejected. Displaying or ignoring it
 * is the caller's choice; this function does not interpret it.
 *
 * The backend allows unlimited resubmission of a task instance until a CORRECT answer writes its
 * one allowed terminal event (`task_service.py`'s `has_terminal_for_instance` guard) -- so `retry`
 * is not a client-invented affordance, it is the flow the contract already supports and this
 * function is what finally reads the result needed to drive it.
 */
export function planSubmissionOutcome(result: CSubmitActionResult): SubmissionOutcome {
  if (result.response_matched) return { kind: 'advance' };
  return { kind: 'retry', scaffoldLevel: result.scaffold_level };
}
// --- session continuation ------------------------------------------------------------------

/**
 * Whether the loop may continue for this session `state`. Component C's real state vocabulary is
 * seven values (`persistence_models.py:34`) and the frozen contract leaves `state` as a plain
 * string, not an enum -- so this checks equality against the one value that means "keep going" and
 * treats every OTHER string, named in the vocabulary or not, as "stop". It must never enumerate the
 * other six: restricting a guard to a subset of an open server vocabulary is the exact defect
 * 10.0a's own register entry found and corrected in the runtime guards ("the session-state
 * vocabulary"), and the fix generalises here rather than being re-derived.
 */
export function shouldContinueSession(state: string): boolean {
  return state === 'active';
}

// --- session bootstrap -----------------------------------------------------------------------

export type SessionBootstrapDecision =
  | { action: 'resume'; cSessionId: string }
  | { action: 'create'; body: CreateCSessionRequest }
  | { action: 'not-ready' };

/**
 * Decide how to bootstrap a session from what `getActiveSession` returned.
 *
 * `grade` and `sessionMode` are never invented here or anywhere in this batch: no document this
 * batch was built against names where a client should source them, and `CreateCSessionRequest`
 * requires both. They are accepted as optional external inputs -- ultimately a future screen's job
 * to supply, most likely via route params -- and when neither an active session nor both of them
 * is available, this fails closed to `'not-ready'` rather than fabricating a grade or a
 * session_mode.
 *
 * An existing session whose `state` is not `'active'` never resumes, no matter how it got there --
 * "never continue a session the server has terminated" is enforced here, not left to a comment.
 * `createSession` is idempotent by learner state server-side (`find_starting_or_active_for_learner`),
 * so falling through to `'create'` in that case is not a client-side guess about what should
 * happen next; the server decides whether a new session actually starts.
 */
export function decideSessionBootstrap(
  active: CActiveSessionResponse,
  grade: number | undefined,
  sessionMode: CreateCSessionRequest['session_mode'] | undefined,
): SessionBootstrapDecision {
  if (active.session && shouldContinueSession(active.session.state)) {
    return { action: 'resume', cSessionId: active.session.c_session_id };
  }
  if (typeof grade === 'number' && (sessionMode === 'combined' || sessionMode === 'c_only')) {
    return { action: 'create', body: { grade, session_mode: sessionMode } };
  }
  return { action: 'not-ready' };
}

// --- failure classification -----------------------------------------------------------------

export type SessionFailureKind = 'technical-block' | 'authentication' | 'network' | 'technical';

/**
 * Classify a failed C API call into the neutral screen it should route to.
 *
 * `'technical-block'` covers every 409 and ONLY a 409: `task_service.py:375` and `:389` collapse
 * the unsigned-parameter refusal, every `LiveEngineCError`, and a non-active session into one bare
 * `ConflictError`, so this function reads only `error.kind` and nothing else about the error -- no
 * `.message`, no `.envelope` -- which is what makes it structurally impossible for two differently
 * caused 409s to reach the screen differently. Everything else buckets into the same three
 * categories Component B's `classifyFailure` already uses, for the same reasons.
 */
export function classifySessionFailure(error: unknown): SessionFailureKind {
  if (!(error instanceof ApiClientError)) return 'technical';
  if (error.kind === 'conflict') return 'technical-block';
  if (error.kind === 'unauthenticated' || error.kind === 'forbidden') return 'authentication';
  if (error.kind === 'network' || error.kind === 'timeout') return 'network';
  return 'technical';
}

// --- submission re-entry gate -----------------------------------------------------------------

// MOVED, 2026-10-09, to src/utils/submit-gate.ts, because Component B's answer path needed the
// same guard and was found not to have it. Re-exported from here so this module stays the import
// site C already uses (c-session-screen.tsx and c-submit-gate.test.ts both read it from this
// path); only the implementation's home changed, and the full rationale travelled with it.
export { createSubmitGate, type SubmitGate } from '@/src/utils/submit-gate';

// --- duplicate submission ---------------------------------------------------------------------

/** The backend's own discriminator for a resubmission against an already-terminated instance. */
const TASK_ALREADY_TERMINAL = 'task_already_terminal';

/**
 * Is this 409 the benign "you already answered this" case, rather than a real session failure?
 *
 * DELIBERATELY NOT PART OF `classifySessionFailure`. That function reads `error.kind` and nothing
 * else, on purpose, so that two differently-caused 409s cannot reach the screen differently -- its
 * own header says so. Widening it to sniff envelopes would dismantle exactly the property it was
 * written to guarantee. This is a separate, narrower question asked at one call site (the submit
 * catch in `c-session-screen.tsx`) about one specific structured detail, and every 409 it does not
 * recognise still falls through to `classifySessionFailure` unchanged.
 *
 * WHY THE DETAIL IS TRUSTWORTHY HERE, when the gate refusals' 409s are not distinguishable: the
 * unsigned-parameter and non-active-session refusals raise a BARE `ConflictError` with no details
 * at all (`task_service.py:375`, `:389`), whereas this one is raised with an explicit structured
 * body -- `[{"location": ["c_task_instance_id"], "type": "task_already_terminal"}]`
 * (`task_service.py:664-666`). The distinction is a real difference in what the server sends, not
 * an inference drawn from a message string.
 *
 * WHAT IT IMPLIES, and why the caller may show a correct-answer panel on the strength of it:
 * `completed_correct` is the ONLY terminal reason wired in the backend -- Phase 6a's T1 ruling,
 * with the other eight explicitly fail-closed and documented as not built (`terminal_event.py`'s
 * own header, T1-1/T1-5). An instance can therefore only be terminal because the child already
 * answered it correctly. If a second terminal reason is ever wired, THIS ASSUMPTION BREAKS and
 * this function must be revisited before that lands.
 *
 * This does not soften the backend guard in any way. The server still refuses the duplicate, still
 * writes nothing, and still scores nothing; the only thing that changes is that the child sees the
 * outcome of the answer they already got right instead of "Something changed on our end".
 */
export function isDuplicateSubmissionConflict(error: unknown): boolean {
  if (!(error instanceof ApiClientError)) return false;
  if (error.kind !== 'conflict') return false;
  const details = error.envelope?.error?.details;
  if (!details) return false;
  const entries = Array.isArray(details) ? details : [details];
  return entries.some((entry) => entry?.type === TASK_ALREADY_TERMINAL);
}
