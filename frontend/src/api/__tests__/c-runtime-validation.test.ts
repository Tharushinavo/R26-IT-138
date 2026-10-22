// Per-field rejection tests for the five Component C runtime guards, mirroring
// contract-freeze.test.ts's isHealthReadyResponse test: each valid sample is checked against
// the frozen schema's own `required` list (never a second, hand-maintained field list free to
// drift from it), then each required field is dropped in turn and the guard must reject.
//
// This file did not exist when 10.0a's component-c-api.ts and the five guards were first
// implemented — an oversight against that batch's own acceptance criteria ("every guard rejects
// each required field's absence, individually"), caught only when a state-vocabulary fix was
// requested against tests that turned out not to exist. Written now, alongside the fix.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  isCActiveSessionResponse,
  isCNextTaskResponse,
  isCSessionCommandResponse,
  isCSessionFields,
  isCSubmitActionResult,
} from '@/src/api/runtime-validation';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const openapiPath = resolve(repoRoot, 'backend', 'contract', 'openapi.v1.json');
const openapi = JSON.parse(readFileSync(openapiPath, 'utf-8'));

function requiredFieldsOf(schemaName: string): string[] {
  const schema = openapi.components.schemas[schemaName];
  assert.ok(schema, `schema ${schemaName} not found in the frozen contract`);
  return schema.required;
}

function assertRejectsEachRequiredFieldIndividually(
  schemaName: string,
  validSample: Record<string, unknown>,
  guard: (value: unknown) => boolean,
) {
  const required = requiredFieldsOf(schemaName);
  for (const field of required) {
    assert.ok(field in validSample, `sample for ${schemaName} is missing required field ${field}`);
  }
  assert.equal(guard(validSample), true, `${schemaName}'s valid sample should be accepted`);

  for (const field of required) {
    const mutated = { ...validSample };
    delete mutated[field];
    assert.equal(guard(mutated), false, `${schemaName}: dropping required field ${field} should fail closed`);
  }
}

const validCSessionFields = {
  c_session_id: 'c-session-1',
  state: 'active',
  session_mode: 'combined',
  session_phase: 'familiarization',
  grade: 3,
  started_at_utc: '2026-08-23T12:00:00Z',
  row_version: 1,
};

test('isCSessionFields rejects each required field individually', () => {
  assertRejectsEachRequiredFieldIndividually('CSessionFields', validCSessionFields, isCSessionFields);
});

// The fix under test: c_sessions.state has seven real values (persistence_models.py:34), not
// B's three. isCSessionFields must accept every one, and must still reject an empty string.
test('isCSessionFields accepts every real c_sessions.state value, not just B\'s three', () => {
  for (const state of ['starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed']) {
    assert.equal(
      isCSessionFields({ ...validCSessionFields, state }),
      true,
      `state=${state} should be accepted`,
    );
  }
  assert.equal(isCSessionFields({ ...validCSessionFields, state: '' }), false, 'an empty state must still be rejected');
});

test('isCSessionFields rejects a session_mode outside the frozen two-member enum', () => {
  assert.equal(isCSessionFields({ ...validCSessionFields, session_mode: 'b_only' }), false);
});

test('isCActiveSessionResponse accepts session: null and rejects a malformed non-null session', () => {
  const validNull = { session: null, request_id: 'req-1' };
  assert.equal(isCActiveSessionResponse(validNull), true);

  const validNonNull = { session: validCSessionFields, request_id: 'req-1' };
  assert.equal(isCActiveSessionResponse(validNonNull), true);

  const malformed = { session: { ...validCSessionFields, row_version: 'not-a-number' }, request_id: 'req-1' };
  assert.equal(isCActiveSessionResponse(malformed), false);

  assertRejectsEachRequiredFieldIndividually('CActiveSessionResponse', validNull, isCActiveSessionResponse);
});

const validCSessionCommandResponse = {
  ...validCSessionFields,
  request_id: 'req-1',
};

test('isCSessionCommandResponse rejects each required field individually', () => {
  assertRejectsEachRequiredFieldIndividually(
    'CSessionCommandResponse',
    validCSessionCommandResponse,
    isCSessionCommandResponse,
  );
});

test('isCSessionCommandResponse accepts every real c_sessions.state value, not just B\'s three', () => {
  for (const state of ['starting', 'active', 'completing', 'completed', 'abandoned', 'expired', 'technical_failed']) {
    assert.equal(
      isCSessionCommandResponse({ ...validCSessionCommandResponse, state }),
      true,
      `state=${state} should be accepted`,
    );
  }
});

const validCNextTaskResponse = {
  c_task_instance_id: 'task-1',
  game_family_id: 'C-GF-01',
  game_task_template_id: 'C-CC-01',
  task_index: 0,
  skill_id: 'skill-1',
  difficulty_level: 1,
  representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
  prompt_payload: { target_n: 3 },
  interactive_assets: {},
  valid_action_space: { valid_object_ids: 'list[str]' },
  scaffold_state: 'C0',
  technical_status: 'ok',
  blanks: null,
  prompt_text: 'Select every object.',
  request_id: 'req-1',
};

test('isCNextTaskResponse rejects each required field individually', () => {
  assertRejectsEachRequiredFieldIndividually('CNextTaskResponse', validCNextTaskResponse, isCNextTaskResponse);
});

test('isCNextTaskResponse rejects a valid_action_space whose values are not all strings', () => {
  assert.equal(
    isCNextTaskResponse({ ...validCNextTaskResponse, valid_action_space: { valid_object_ids: 3 } }),
    false,
  );
});

test('isCNextTaskResponse rejects an empty or non-string prompt_text', () => {
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, prompt_text: '' }), false);
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, prompt_text: 5 }), false);
});

// `blanks` is required but nullable: the generic per-field drop above proves absence is
// rejected, but "reject when removed" and "accept when null" are both true of this field, and a
// naive helper asserts only the first. These cases prove the second, plus the two non-null,
// non-integer shapes that must still fail closed.
test('isCNextTaskResponse accepts blanks: null and rejects a non-integer blanks', () => {
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, blanks: null }), true);
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, blanks: 3 }), true);
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, blanks: 1.5 }), false);
  assert.equal(isCNextTaskResponse({ ...validCNextTaskResponse, blanks: '1' }), false);
});

const validCSubmitActionResult = {
  c_task_instance_id: 'task-1',
  response_matched: true,
  scaffold_level: 'C0',
  request_id: 'req-1',
};

test('isCSubmitActionResult rejects each required field individually', () => {
  assertRejectsEachRequiredFieldIndividually('CSubmitActionResult', validCSubmitActionResult, isCSubmitActionResult);
});

test('isCSubmitActionResult rejects a non-boolean response_matched', () => {
  assert.equal(isCSubmitActionResult({ ...validCSubmitActionResult, response_matched: 'true' }), false);
});
