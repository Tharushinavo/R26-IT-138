// `planSubmissionOutcome` (c-session-logic.ts) -- the pure decision behind the correct/incorrect +
// retry loop. See that function's own header for why it takes only a `CSubmitActionResult` and
// nothing about the submitted payload: correctness is the server's, computed once, before this
// function ever runs, and this function's whole job is to relay that verdict, never to re-derive
// it.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import type { CSubmitActionResult } from '@/src/api/generated/openapi-types';
import { planSubmissionOutcome } from '@/src/features/c-session/c-session-logic';

function validResult(overrides: Partial<CSubmitActionResult> = {}): CSubmitActionResult {
  return {
    c_task_instance_id: 'task-instance-1',
    request_id: 'req-1',
    response_matched: true,
    scaffold_level: 'C0',
    ...overrides,
  };
}

test('a matched result advances', () => {
  const outcome = planSubmissionOutcome(validResult({ response_matched: true }));
  assert.deepEqual(outcome, { kind: 'advance' });
});

test('a not-matched result retries, carrying the server scaffold_level', () => {
  const outcome = planSubmissionOutcome(validResult({ response_matched: false, scaffold_level: 'C2' }));
  assert.deepEqual(outcome, { kind: 'retry', scaffoldLevel: 'C2' });
});

test('an unexpected scaffold_level string is relayed verbatim, never rejected or coerced', () => {
  const outcome = planSubmissionOutcome(
    validResult({ response_matched: false, scaffold_level: 'SOMETHING_NEW_ON_THE_WIRE' }),
  );
  assert.deepEqual(outcome, { kind: 'retry', scaffoldLevel: 'SOMETHING_NEW_ON_THE_WIRE' });
});

test('scaffold_level on a matched result plays no role in the outcome', () => {
  // Deliberately mismatched-looking input (a matched result carrying a non-'C0' scaffold_level) --
  // planSubmissionOutcome must not infer anything from this combination; only response_matched
  // decides advance vs retry.
  const outcome = planSubmissionOutcome(validResult({ response_matched: true, scaffold_level: 'C3' }));
  assert.deepEqual(outcome, { kind: 'advance' });
});

// The structural proof that this function cannot be judging correctness itself: its own source
// contains no comparison operator against anything payload-shaped, and its only parameter type is
// the already-server-computed result -- never CNextTaskResponse, never a raw values/payload object.
// Comments are stripped first (this project's own established trap: an early guard here was once
// written as a bare substring match and failed on its own explanatory comments).
test('planSubmissionOutcome reads only response_matched and scaffold_level off its argument -- source scan', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const filePath = resolve(here, '..', '..', 'features', 'c-session', 'c-session-logic.ts');
  const source = readFileSync(filePath, 'utf8');

  const functionStart = source.indexOf('export function planSubmissionOutcome');
  assert.ok(functionStart >= 0, 'planSubmissionOutcome must exist in c-session-logic.ts');
  const bodyStart = source.indexOf('{', functionStart);
  const bodyEnd = source.indexOf('\n}', bodyStart);
  const body = source
    .slice(bodyStart, bodyEnd)
    .split('\n')
    .filter((line) => !line.trim().startsWith('//'))
    .join('\n');

  assert.match(body, /result\.response_matched/);
  assert.match(body, /result\.scaffold_level/);
  assert.doesNotMatch(body, /action_payload/);
  assert.doesNotMatch(body, /valid_action_space/);
  assert.doesNotMatch(body, /prompt_payload/);
});
