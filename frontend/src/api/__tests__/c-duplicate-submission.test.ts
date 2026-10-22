// `task_already_terminal` is the benign "you already answered this" case, not a session failure.
//
// THE INVARIANT THESE TESTS DEFEND, stated first because it is the one easy to erode later:
// `classifySessionFailure` reads `error.kind` and NOTHING else, deliberately, so two 409s with
// different causes cannot reach the screen differently. `isDuplicateSubmissionConflict` does NOT
// relax that -- it is a separate predicate asked at a single call site, and every 409 it does not
// positively recognise still falls through to `classifySessionFailure` untouched. The final test
// in this file exists to fail if someone ever "simplifies" the two into one.
//
// The backend guard is unchanged and remains the authority: the server still refuses the duplicate
// (`task_service.py:664-666`), still writes no second terminal event, and still scores nothing.
// What changed is only what the CHILD sees when it happens.

import assert from 'node:assert/strict';
import test from 'node:test';

import type { ApiErrorEnvelope } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import {
  classifySessionFailure,
  isDuplicateSubmissionConflict,
} from '@/src/features/c-session/c-session-logic';

/** The exact envelope shape `ConflictError(details=[...])` produces for this case. */
function terminalConflictEnvelope(): ApiErrorEnvelope {
  return {
    schema_version: '1.0',
    error: {
      code: 'CONFLICT',
      message: 'Conflict.',
      request_id: 'd43a6b07-7ee7-4f4f-9659-7f623a719c87',
      details: [{ location: ['c_task_instance_id'], type: 'task_already_terminal' }],
    },
  };
}

function conflict(envelope?: ApiErrorEnvelope): ApiClientError {
  return new ApiClientError('conflict', 'Conflict.', 409, 'req-1', envelope);
}

test('a task_already_terminal 409 is recognised as the benign duplicate', () => {
  assert.equal(isDuplicateSubmissionConflict(conflict(terminalConflictEnvelope())), true);
});

test('the detail is honoured when the envelope carries it as a bare object, not an array', () => {
  // `ApiErrorEnvelope.details` is typed as an object OR an array of objects; the predicate must
  // not depend on which the server happened to send.
  const envelope = terminalConflictEnvelope();
  envelope.error.details = { location: ['c_task_instance_id'], type: 'task_already_terminal' };
  assert.equal(isDuplicateSubmissionConflict(conflict(envelope)), true);
});

// --- 4. genuine failures keep their existing path ---------------------------------------------

test('a BARE 409 is NOT treated as a duplicate — it is a real session failure', () => {
  // This is the shape the unsigned-parameter and non-active-session refusals raise
  // (`task_service.py:375`, `:389`): a ConflictError with no details at all. Misreading one of
  // these as benign would show a child a correct-answer panel for a task the server refused to
  // serve, which is strictly worse than the technical-block screen.
  const bare = conflict(undefined);
  assert.equal(isDuplicateSubmissionConflict(bare), false);
  assert.equal(classifySessionFailure(bare), 'technical-block');
});

test('a 409 carrying some OTHER structured detail is not treated as a duplicate', () => {
  const envelope = terminalConflictEnvelope();
  envelope.error.details = [{ location: ['action_payload'], type: 'extra_forbidden' }];
  const other = conflict(envelope);
  assert.equal(isDuplicateSubmissionConflict(other), false);
  assert.equal(classifySessionFailure(other), 'technical-block');
});

test('non-409 failures are never treated as duplicates, whatever they carry', () => {
  for (const kind of ['network', 'timeout', 'unauthenticated', 'forbidden', 'server'] as const) {
    const error = new ApiClientError(kind, 'nope', 500, 'req', terminalConflictEnvelope());
    assert.equal(
      isDuplicateSubmissionConflict(error),
      false,
      `${kind} must not be swallowed as a duplicate even with a matching envelope`,
    );
  }
});

test('a non-ApiClientError is never treated as a duplicate', () => {
  assert.equal(isDuplicateSubmissionConflict(new Error('boom')), false);
  assert.equal(isDuplicateSubmissionConflict(null), false);
  assert.equal(isDuplicateSubmissionConflict(undefined), false);
});

// --- the invariant guard ----------------------------------------------------------------------

test('classifySessionFailure still routes EVERY 409 to technical-block, including this one', () => {
  // The narrowing lives at the call site, never inside classifySessionFailure. If someone later
  // teaches that function about envelopes, this fails -- which is the point.
  assert.equal(classifySessionFailure(conflict(terminalConflictEnvelope())), 'technical-block');
  assert.equal(classifySessionFailure(conflict(undefined)), 'technical-block');
});

// --- 3. the successful path is untouched -------------------------------------------------------

test('a successful submission never consults the duplicate predicate at all', () => {
  // The success path returns a result and never enters the catch, so no error object exists to
  // classify. Asserting the predicate rejects a non-error stands in for that: nothing about a
  // successful submission can be mistaken for a duplicate.
  assert.equal(isDuplicateSubmissionConflict({ response_matched: true } as unknown), false);
});
