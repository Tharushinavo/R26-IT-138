import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { AttemptResponse } from '@/src/api/generated/openapi-types';
import {
  classifyAttemptOutcome,
  isAnswerSurfaceDisabled,
  isDeadlinePassed,
  outcomeView,
} from '@/src/features/session/live-session-logic';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

// --- isDeadlinePassed ---------------------------------------------------------------------------

const deadline = '2026-07-29T12:05:00Z';
const deadlineMs = Date.parse(deadline);

test('isDeadlinePassed reports a deadline in the past as passed', () => {
  assert.equal(isDeadlinePassed(deadline, deadlineMs + 1_000), true);
});

test('isDeadlinePassed reports a deadline in the future as not passed', () => {
  assert.equal(isDeadlinePassed(deadline, deadlineMs - 1_000), false);
});

test('isDeadlinePassed treats exactly-equal as passed, matching the server comparison', () => {
  // The server evaluates `now >= opportunity.timeout_deadline_utc` (attempt_submission.py:213).
  assert.equal(isDeadlinePassed(deadline, deadlineMs), true);
});

test('isDeadlinePassed treats an unparseable deadline as not passed', () => {
  // Fail-safe direction: the one that keeps the child able to answer. The server decides anyway.
  assert.equal(isDeadlinePassed('not-a-date', deadlineMs), false);
  assert.equal(isDeadlinePassed('', deadlineMs), false);
});

// --- the soft-lock guard --------------------------------------------------------------------------

// DO NOT "FIX" THIS INTO A DISABLED STATE. Disabling the answer surface once the deadline passes
// would permanently soft-lock the session on that question, because:
//   1. No server-side sweep records timeouts — a TIMEOUT is written only when the *client* submits
//      after the deadline (attempt_submission.py:213-229); and
//   2. advancing past an opportunity requires at least one recorded attempt or timeout
//      (session_completion.py:22).
// No submit → no recorded TIMEOUT → no advance → the child is stuck on that question forever.
// Submitting late is free: the server sets submitted_value = None, never compares the answer, and
// returns event_kind TIMEOUT.
test('the answer surface stays interactive after the deadline has passed (soft-lock guard)', () => {
  assert.equal(
    isAnswerSurfaceDisabled({ deadlinePassed: true, hasOutcome: false, submitting: false }),
    false,
    'an expired deadline must never make the answer surface inert — that soft-locks the session',
  );
});

test('a device clock skewed past the deadline at mount changes nothing about interactivity', () => {
  // The client clock is advisory; event_kind on the response is truth. A phone set hours ahead
  // must not stop a child from answering.
  const skewedNow = deadlineMs + 6 * 60 * 60 * 1_000;
  assert.equal(isDeadlinePassed(deadline, skewedNow), true);
  assert.equal(
    isAnswerSurfaceDisabled({
      deadlinePassed: isDeadlinePassed(deadline, skewedNow),
      hasOutcome: false,
      submitting: false,
    }),
    false,
  );
});

test('the answer surface is inert only while submitting or once an outcome is shown', () => {
  assert.equal(
    isAnswerSurfaceDisabled({ deadlinePassed: false, hasOutcome: false, submitting: true }),
    true,
  );
  assert.equal(
    isAnswerSurfaceDisabled({ deadlinePassed: false, hasOutcome: true, submitting: false }),
    true,
  );
  assert.equal(
    isAnswerSurfaceDisabled({ deadlinePassed: false, hasOutcome: false, submitting: false }),
    false,
  );
});

// --- TIMEOUT outcome lock ---------------------------------------------------------------------------

// A lock on FE-3b's existing behaviour, not a reimplementation of it. The shape below is what the
// server actually returns on a timeout: submitted_value is never echoed, response_matched is null,
// and the answer is never compared (attempt_submission.py:216-229).
test('a real-shaped TIMEOUT response still classifies as timeout, never incorrect', () => {
  const timedOut: AttemptResponse = {
    attempt_index: 1,
    event_kind: 'TIMEOUT',
    item_opportunity_id: 'opportunity-1',
    request_id: 'req-timeout-1',
    response_matched: null,
    server_submitted_at_utc: '2026-07-29T12:06:11Z',
  } as AttemptResponse;

  assert.equal(classifyAttemptOutcome(timedOut), 'timeout');
  assert.notEqual(classifyAttemptOutcome(timedOut), 'incorrect');

  // And the copy the child sees stays neutral — no wrong-answer treatment, no retry prompt.
  const view = outcomeView(classifyAttemptOutcome(timedOut));
  assert.equal(view.canTryAgain, false);
  assert.notEqual(view.title, outcomeView('incorrect').title);
});

// --- no hardcoded timeout duration --------------------------------------------------------------------

// Grep-as-a-test, same pattern as no-auth-bypass.test.ts. The timeout bound is unapproved policy
// and lives only in the server's `server_timeout_deadline_utc`. A literal in the client would both
// duplicate that policy and be silently wrong the moment the server's value changed — and, worse,
// would invite a client-side expiry rule of exactly the kind the soft-lock guard above forbids.
const sessionModules = [
  'src/features/session/live-session-logic.ts',
  'src/features/session/live-session-screen.tsx',
  'src/features/session/session-command-store.ts',
];
const forbiddenLiterals = [/\b300000\b/, /\b300_000\b/, /\b300\b/, /5\s*\*\s*60/];

for (const relativePath of sessionModules) {
  test(`${relativePath} hardcodes no timeout duration`, () => {
    const source = readFileSync(resolve(frontendRoot, relativePath), 'utf-8');
    for (const pattern of forbiddenLiterals) {
      assert.equal(
        pattern.test(source),
        false,
        `${relativePath} must not contain ${pattern} — the timeout bound belongs to the server`,
      );
    }
  });
}
