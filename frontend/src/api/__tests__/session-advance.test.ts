import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { ApiClientError } from '@/src/api/errors';
import type {
  OpportunityAdvanceResponse,
  OpportunityPresentationFields,
} from '@/src/api/generated/openapi-types';
import {
  canAdvance,
  canRequestHint,
  classifyFailure,
  decideAdvance,
  decidePendingAssist,
  decidePendingReplay,
  hintStateFor,
  initialAnswerState,
  markHintsUnavailable,
  planPresentation,
} from '@/src/features/session/live-session-logic';
import { encodeSubmittedValue } from '@/src/features/session/renderers/encode';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

// The inline next question is an OpportunityPresentationFields — the *fields* shape, with no
// request_id of its own. That distinction is the non-obvious part of the advance path.
function nextOpportunity(
  overrides: Partial<OpportunityPresentationFields> = {},
): OpportunityPresentationFields {
  return {
    difficulty_level: 'CORE',
    grade: 3,
    item_instance_id: 'item-instance-2',
    item_opportunity_id: 'opportunity-2',
    presentation_token: 'token-2',
    presented_choices: ['12', '13', '14', '15'],
    prompt: { stem: 'What comes next: 12, 13, 14, __?' },
    representation_type: 'numeral',
    response_format: 'single_integer',
    server_timeout_deadline_utc: '2026-07-30T10:05:00Z',
    skill_id: 'counting',
    ...overrides,
  };
}

function advanceResponse(
  overrides: Partial<OpportunityAdvanceResponse> = {},
): OpportunityAdvanceResponse {
  return {
    item_opportunity_id: 'opportunity-1',
    next_opportunity: nextOpportunity(),
    opportunities_completed: 1,
    opportunities_total_bound: 5,
    request_id: 'req-advance-1',
    session_state: 'active',
    ...overrides,
  };
}

// --- the next question arrives inline ---------------------------------------------------------------

test('an advance carrying a next_opportunity yields the next plan, ready to render', () => {
  // No second POST /opportunities: the presentation is already in hand, and a re-fetch would be
  // latency a child pays for nothing.
  const decision = decideAdvance(advanceResponse());
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next' || decision.plan.kind !== 'render') return;
  assert.equal(decision.plan.itemOpportunityId, 'opportunity-2');
  assert.equal(decision.plan.stem, 'What comes next: 12, 13, 14, __?');
  assert.equal(decision.plan.skillLabel, 'Counting');
});

test("the next question's support code is the advance response's request_id", () => {
  // OpportunityPresentationFields carries no request_id. The advance response's is the correct
  // one: that request is what produced this question, so it is what a grown-up should quote.
  const decision = decideAdvance(advanceResponse({ request_id: 'req-advance-99' }));
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next') return;
  assert.equal(decision.plan.requestId, 'req-advance-99');
});

test('an inline next question with a drifted response_format still fails closed', () => {
  const decision = decideAdvance(
    advanceResponse({ next_opportunity: nextOpportunity({ response_format: 'not_a_real_format' }) }),
  );
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next') return;
  assert.equal(decision.plan.kind, 'unrenderable');
  if (decision.plan.kind !== 'unrenderable') return;
  assert.equal(decision.plan.requestId, 'req-advance-1');
});

test('planPresentation accepts the fields shape directly, with the request id supplied', () => {
  const plan = planPresentation(nextOpportunity(), 'req-advance-1');
  assert.equal(plan.kind, 'render');
  if (plan.kind !== 'render') return;
  assert.equal(plan.requestId, 'req-advance-1');
});

// --- completion ---------------------------------------------------------------------------------------

test('a null next_opportunity with session_state completed reaches the completion state', () => {
  const decision = decideAdvance(
    advanceResponse({
      next_opportunity: null,
      opportunities_completed: 5,
      session_state: 'completed',
    }),
  );
  assert.equal(decision.kind, 'completed');
  if (decision.kind !== 'completed') return;
  assert.equal(decision.progress.completed, 5);
  assert.equal(decision.progress.totalBound, 5);
});

// --- drift ---------------------------------------------------------------------------------------------

test('a null next_opportunity while still active is drift, not a guess', () => {
  // The server said neither "here is the next question" nor "the session is over". The screen
  // re-asks POST /opportunities and renders what comes back, rather than inventing a state.
  const decision = decideAdvance(advanceResponse({ next_opportunity: null, session_state: 'active' }));
  assert.equal(decision.kind, 'drift');
});

test('a next question alongside session_state completed is drift too', () => {
  // Contradictory: reaching the bound is exactly what makes next_opportunity null. Answering into
  // a session the server considers finished is the worse guess, so this fails closed as well.
  const decision = decideAdvance(advanceResponse({ session_state: 'completed' }));
  assert.equal(decision.kind, 'drift');
});

// --- progress passes through unmodified -------------------------------------------------------------------

test('progress is carried through exactly as the server reported it', () => {
  const decision = decideAdvance(
    advanceResponse({ opportunities_completed: 3, opportunities_total_bound: 7 }),
  );
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next') return;
  assert.deepEqual(decision.progress, { completed: 3, totalBound: 7 });
});

test('a bound the client has never seen before is reported unchanged, not clamped', () => {
  // There is no client-side bound to disagree with. MAX_OPPORTUNITIES_PER_SESSION is an unapproved
  // engineering placeholder, so the client must follow the server's number wherever it goes.
  const decision = decideAdvance(
    advanceResponse({ opportunities_completed: 11, opportunities_total_bound: 12 }),
  );
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next') return;
  assert.deepEqual(decision.progress, { completed: 11, totalBound: 12 });
});

// --- the advance gate ----------------------------------------------------------------------------------------

test('advancing is gated on a recorded attempt', () => {
  // attempt_count < 1 raises 409 (session_completion.py:321-325), so the control stays closed
  // until the child has submitted. A recorded TIMEOUT counts — which is why FE-3c's "always let
  // them submit" rule is what makes the session advanceable at all.
  assert.equal(canAdvance(false), false);
  assert.equal(canAdvance(true), true);
});

test('a 409 on complete routes to re-presenting, never to a client-side rule', () => {
  // The screen re-calls POST /opportunities on 'conflict' and renders whatever the server returns
  // — the same move FE-3b makes on a 409 from submit.
  assert.equal(classifyFailure(new ApiClientError('conflict', 'no attempt yet', 409)), 'conflict');
  assert.notEqual(classifyFailure(new ApiClientError('server', 'boom', 500)), 'conflict');
});

// --- per-question state resets ------------------------------------------------------------------------------

test('every piece of per-question state resets on a new item_opportunity_id', () => {
  const decision = decideAdvance(advanceResponse());
  assert.equal(decision.kind, 'next');
  if (decision.kind !== 'next' || decision.plan.kind !== 'render') return;

  // Answer state: seeded fresh, so nothing is submittable until the child touches the new question.
  const seed = initialAnswerState(decision.plan.spec);
  assert.equal(encodeSubmittedValue(decision.plan.spec, seed), null);

  // Hint state: FE-3d already keys on item_opportunity_id, so this is a re-key, not a manual clear.
  // Verified rather than rebuilt.
  const closedHints = markHintsUnavailable(hintStateFor(null, 'opportunity-1'));
  const nextHints = hintStateFor(closedHints, decision.plan.itemOpportunityId);
  assert.equal(nextHints.itemOpportunityId, 'opportunity-2');
  assert.deepEqual(nextHints.received, []);
  assert.equal(canRequestHint(nextHints), true);
});

test('a stale pending command from the previous question never survives into the next one', () => {
  // submit_response and request_assist share one store slot (FE-3d). The advance path clears it,
  // and both decision helpers independently refuse anything keyed to the question just left.
  const staleSubmit = {
    body: { client_elapsed_ms: 900, submitted_value: '14' },
    createdAt: '2026-07-30T10:00:00.000Z',
    endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
    idempotencyKey: 'stale-submit',
    itemOpportunityId: 'opportunity-1',
    kind: 'submit_response',
    sessionId: 'session-1',
  } as const;
  const staleAssist = {
    createdAt: '2026-07-30T10:00:00.000Z',
    endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/assists',
    idempotencyKey: 'stale-assist',
    itemOpportunityId: 'opportunity-1',
    kind: 'request_assist',
    sessionId: 'session-1',
  } as const;

  assert.deepEqual(decidePendingReplay(staleSubmit, 'session-1', 'opportunity-2'), { action: 'discard' });
  assert.deepEqual(decidePendingAssist(staleAssist, 'session-1', 'opportunity-2'), { action: 'fresh' });
});

// --- no hardcoded session bound ---------------------------------------------------------------------------------

// Grep-as-a-test, matching the existing timeout guard. MAX_OPPORTUNITIES_PER_SESSION = 5 is an
// unapproved engineering placeholder, not a governed session length: the client must read the
// bound off `opportunities_total_bound` every time and must never assume, clamp to, or celebrate
// a particular number.
//
// live-session-screen.tsx is scanned with its StyleSheet block removed — that block is full of
// legitimate 5s (font sizes, opacities, widths) that would drown the signal. The split marker is
// asserted so this can never silently pass by failing to find it.
const STYLE_MARKER = 'const styles = StyleSheet.create(';

test('live-session-logic.ts hardcodes no session bound', () => {
  const source = readFileSync(resolve(frontendRoot, 'src/features/session/live-session-logic.ts'), 'utf-8');
  assert.equal(/\b5\b/.test(source), false, 'the session bound belongs to the server');
  assert.equal(source.includes('MAX_OPPORTUNITIES'), false);
});

test('live-session-screen.tsx hardcodes no session bound outside its stylesheet', () => {
  const source = readFileSync(resolve(frontendRoot, 'src/features/session/live-session-screen.tsx'), 'utf-8');
  const markerAt = source.indexOf(STYLE_MARKER);
  assert.notEqual(markerAt, -1, 'stylesheet marker moved — update this guard rather than deleting it');
  const logic = source.slice(0, markerAt);
  assert.equal(/\b5\b/.test(logic), false, 'the session bound belongs to the server');
  assert.equal(source.includes('MAX_OPPORTUNITIES'), false);
});
