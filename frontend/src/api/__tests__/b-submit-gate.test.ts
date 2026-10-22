// Component B's answer-submission re-entry gate (FE-001, 2026-10-09).
//
// B shipped without one. `submitAnswer` gated on the `submitting` React state alone, which cannot
// serialise two taps dispatched in the same frame -- both read the pre-update `false`. Each tap
// then built its own command with a FRESH `Crypto.randomUUID()` idempotency key, so the server saw
// two unrelated requests and recorded a real second attempt (`attempt_index = 2`).
//
// The adaptive model itself was never at risk: `attempt_submission.py` gates the BKT observation on
// `attempt_index == 1 and event_kind == "RESPONSE"`. The defect is in the research record -- a
// child logged as having answered twice when they tapped twice on one answer. That is why this is
// guarded rather than left to the backend: unlike Component C, B's server has no
// `task_already_terminal` refusal to fall back on, because a fresh key per tap is a legitimate
// distinct request as far as idempotency is concerned.
//
// The gate mechanism itself is covered by c-submit-gate.test.ts and is not re-tested here. These
// tests cover the two things specific to B: that the ORDER of operations in `submitAnswer` is the
// one that actually protects the pending-command slot, and that the source has not regressed to a
// state-only guard.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { createSubmitGate } from '@/src/utils/submit-gate';

const SCREEN_PATH = 'src/features/session/live-session-screen.tsx';
const screenSource = readFileSync(SCREEN_PATH, 'utf8');

// The behavioural test. `submitAnswer` persists the command BEFORE sending it, into a single
// pending slot, so this models both steps: the gate has to exclude the second tap from the WRITE,
// not merely from the network call. A gate placed inside `sendSubmit` would let both taps write,
// and the stored replay record would end up pointing at the second tap's key while the first tap's
// request was the one actually in flight -- losing the record for the attempt that happened.
test('two concurrent submits write the pending command once, with the key that was sent', async () => {
  const gate = createSubmitGate();
  let pendingSlot: string | null = null;
  const sent: string[] = [];
  let releaseInFlight: (() => void) | null = null;

  const submitAnswer = async (idempotencyKey: string) => {
    if (!gate.tryEnter()) return;
    try {
      pendingSlot = idempotencyKey; // stands in for savePendingCommand
      await new Promise<void>((resolve) => {
        releaseInFlight = resolve;
      });
      sent.push(idempotencyKey); // stands in for api.submitResponse
    } finally {
      gate.release();
    }
  };

  const first = submitAnswer('key-first-tap');
  const second = submitAnswer('key-second-tap');

  assert.equal(pendingSlot, 'key-first-tap', 'the second tap must never overwrite the pending slot');
  releaseInFlight!();
  await Promise.all([first, second]);

  assert.deepEqual(sent, ['key-first-tap'], 'only one attempt may reach the server');
  assert.equal(
    pendingSlot,
    sent[0],
    'the persisted replay record must name the key that was actually sent',
  );
});

test('a failed submit still releases the gate, so the child can retry the question', async () => {
  const gate = createSubmitGate();

  const failing = async () => {
    if (!gate.tryEnter()) return;
    try {
      await Promise.reject(new Error('network died'));
    } catch {
      // sendSubmit routes its own failures rather than rethrowing; what matters is the `finally`.
    } finally {
      gate.release();
    }
  };

  await failing();
  assert.equal(gate.isBusy(), false, 'a failed submit must not leave the answer surface dead');
});

// Structural guards. The behavioural tests above prove the SHAPE is correct; these prove the screen
// still uses it, since the regression this is here to stop is a silent revert to a state-only check.
test('live-session-screen.tsx holds a submit gate in a ref', () => {
  assert.match(
    screenSource,
    /const submitGateRef = useRef\(createSubmitGate\(\)\)/,
    `${SCREEN_PATH} must hold the gate in a ref: React state cannot serialise same-frame taps`,
  );
});

test('the gate is taken before the pending command is persisted', () => {
  const gateIndex = screenSource.indexOf('submitGateRef.current.tryEnter()');
  // Matched on the call, not its argument list: B3 added a `subject` argument for subject-scoped
  // keys, and this test is about the ORDER of the two statements, not their signatures.
  const saveIndex = screenSource.indexOf('await savePendingCommand(');

  assert.notEqual(gateIndex, -1, 'submitAnswer must take the gate');
  assert.notEqual(saveIndex, -1, 'submitAnswer must still persist the command before sending');
  assert.ok(
    gateIndex < saveIndex,
    'the gate must be taken BEFORE savePendingCommand, or two taps can both write the single ' +
      'pending slot and the stored replay key stops matching the request that was sent',
  );
});

test('the gate is released in a finally', () => {
  assert.match(
    screenSource,
    /finally \{[\s\S]{0,400}?submitGateRef\.current\.release\(\)/,
    'the gate must be released from a `finally`, or one failure locks the answer surface for the ' +
      'rest of the question',
  );
});
