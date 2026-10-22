// Tests for the C session shell's pure logic (10.0b-ii): `planTask`'s fail-closed routing,
// `shouldContinueSession`'s open-vocabulary handling, `decideSessionBootstrap`'s
// never-resume-a-terminated-session rule, and `classifySessionFailure`'s single 409 bucket.
//
// Lives under src/api/__tests__/ rather than a directory next to the source it tests, because
// `npm run test:contract` (package.json) is a FLAT, non-recursive glob:
// `node --import tsx --test src/api/__tests__/*.test.ts`. A test placed under, say,
// src/features/c-session/__tests__/ would exist, look correct in review, and pass if ever run by
// hand -- and never run under the real gate. This is the same class of silent-vacuity trap this
// project has already shipped once (10.0a's missing guard-level tests, invisible inside a count
// that reconciled exactly). 10.0b-i's own tests already established this placement; this file
// follows it rather than rediscovering it.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { ApiClientError } from '@/src/api/errors';
import type { CActiveSessionResponse, CNextTaskResponse } from '@/src/api/generated/openapi-types';
import {
  classifySessionFailure,
  decideSessionBootstrap,
  planTask,
  shouldContinueSession,
} from '@/src/features/c-session/c-session-logic';

function makeTask(overrides: Partial<CNextTaskResponse> = {}): CNextTaskResponse {
  return {
    blanks: 1,
    c_task_instance_id: 'task-1',
    difficulty_level: 1,
    game_family_id: 'C-GF-02',
    game_task_template_id: 'C-NP-01',
    interactive_assets: {},
    prompt_payload: { shown_sequence: [1, 2, 3] },
    prompt_text: 'Write what comes next in the pattern.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { entered_values: 'list[int]' },
    ...overrides,
  };
}

// --- planTask ---------------------------------------------------------------------------------

test('planTask resolves a known template id with bound types to its archetype', () => {
  const plan = planTask(makeTask());
  assert.equal(plan.kind, 'archetype');
  if (plan.kind === 'archetype') {
    assert.equal(plan.archetypeId, 'ordered-value-sequence');
  }
});

test('planTask fails closed for an unknown template id (negative control)', () => {
  const plan = planTask(makeTask({ game_task_template_id: 'C-NOT-A-REAL-TEMPLATE' }));
  assert.equal(plan.kind, 'fail-closed');
});

test('planTask fails closed when valid_action_space declares an unbound type', () => {
  const plan = planTask(
    makeTask({ valid_action_space: { entered_values: 'not_a_real_type' } }),
  );
  assert.equal(plan.kind, 'fail-closed');
});

// --- shouldContinueSession ----------------------------------------------------------------------

test('shouldContinueSession is true only for "active"', () => {
  assert.equal(shouldContinueSession('active'), true);
});

test('shouldContinueSession is false for every other named state, and for an unnamed one (negative control)', () => {
  // Component C's real vocabulary is seven values (persistence_models.py:34); this must never
  // narrow to a subset of it, so every other named value AND a value outside the named seven are
  // both checked here, and both must be false.
  const named = ['starting', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed'];
  for (const state of named) {
    assert.equal(shouldContinueSession(state), false, `expected "${state}" not to continue`);
  }
  assert.equal(shouldContinueSession('some_future_eighth_state'), false);
});

// --- decideSessionBootstrap ----------------------------------------------------------------------

function makeActive(session: CActiveSessionResponse['session']): CActiveSessionResponse {
  return { request_id: 'req-active', session };
}

test('decideSessionBootstrap resumes an active session', () => {
  const active = makeActive({
    c_session_id: 'c-session-1',
    grade: 3,
    row_version: 1,
    session_mode: 'c_only',
    session_phase: 'familiarization',
    started_at_utc: '2026-08-24T00:00:00Z',
    state: 'active',
  });
  const decision = decideSessionBootstrap(active, undefined, undefined);
  assert.deepEqual(decision, { action: 'resume', cSessionId: 'c-session-1' });
});

test('decideSessionBootstrap never resumes a terminated session, even with a session on record (negative control)', () => {
  const active = makeActive({
    c_session_id: 'c-session-old',
    grade: 3,
    row_version: 4,
    session_mode: 'c_only',
    session_phase: 'familiarization',
    started_at_utc: '2026-08-24T00:00:00Z',
    state: 'completed',
  });
  const decision = decideSessionBootstrap(active, 3, 'c_only');
  assert.equal(decision.action, 'create');
});

test('decideSessionBootstrap creates when no session exists and both grade and session_mode are supplied', () => {
  const decision = decideSessionBootstrap(makeActive(null), 3, 'combined');
  assert.deepEqual(decision, { action: 'create', body: { grade: 3, session_mode: 'combined' } });
});

test('decideSessionBootstrap fails closed to not-ready rather than inventing grade or session_mode', () => {
  assert.deepEqual(decideSessionBootstrap(makeActive(null), undefined, undefined), {
    action: 'not-ready',
  });
  assert.deepEqual(decideSessionBootstrap(makeActive(null), 3, undefined), { action: 'not-ready' });
  assert.deepEqual(decideSessionBootstrap(makeActive(null), undefined, 'c_only'), {
    action: 'not-ready',
  });
});

// --- classifySessionFailure ----------------------------------------------------------------------

test('classifySessionFailure buckets a 409 as technical-block, and only a 409', () => {
  assert.equal(classifySessionFailure(new ApiClientError('conflict', 'x')), 'technical-block');
  assert.equal(classifySessionFailure(new ApiClientError('unauthenticated', 'x')), 'authentication');
  assert.equal(classifySessionFailure(new ApiClientError('forbidden', 'x')), 'authentication');
  assert.equal(classifySessionFailure(new ApiClientError('network', 'x')), 'network');
  assert.equal(classifySessionFailure(new ApiClientError('timeout', 'x')), 'network');
  assert.equal(classifySessionFailure(new ApiClientError('server', 'x')), 'technical');
  assert.equal(classifySessionFailure(new Error('not an ApiClientError')), 'technical');
});

test('classifySessionFailure carries no diagnostic distinction between two differently-caused 409s', () => {
  const a = new ApiClientError('conflict', 'unsigned parameter family', 409, 'req-a');
  const b = new ApiClientError('conflict', 'session not active', 409, 'req-b');
  // Both classify identically regardless of message content -- the function reads only .kind.
  assert.equal(classifySessionFailure(a), 'technical-block');
  assert.equal(classifySessionFailure(b), 'technical-block');
});
