import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { PendingRequestAssistCommand, PendingSessionCommand } from '@/src/api/contracts';
import type { HintRequestResponse } from '@/src/api/generated/openapi-types';
import {
  canRequestHint,
  decidePendingAssist,
  hintStateFor,
  initialHintState,
  markHintsUnavailable,
  recordHint,
  HINTS_UNAVAILABLE_COPY,
} from '@/src/features/session/live-session-logic';

function hint(level: number, content: string, itemOpportunityId = 'opportunity-1'): HintRequestResponse {
  return {
    catalogue_checksum: 'sha256:abc',
    catalogue_version: '1.0.0',
    content,
    content_id: `hint-${level}`,
    hint_level: level,
    item_opportunity_id: itemOpportunityId,
    request_id: `req-hint-${level}`,
  };
}

// --- the availability state machine ---------------------------------------------------------------

test('a fresh opportunity starts with hints available and none received', () => {
  const state = initialHintState('opportunity-1');
  assert.equal(canRequestHint(state), true);
  assert.deepEqual(state.received, []);
});

test('the ladder walks available → L1 → L2 → L3 → unavailable', () => {
  // The client never requests or sends a level: the server derives it from its own count of prior
  // hint events under the opportunity row lock, strictly single-step. These are the levels it
  // hands back, in order.
  let state = initialHintState('opportunity-1');
  assert.equal(canRequestHint(state), true);

  state = recordHint(state, hint(1, 'Look at how much each number grows.'));
  assert.equal(state.received.map((h) => h.hint_level).join(','), '1');
  assert.equal(canRequestHint(state), true);

  state = recordHint(state, hint(2, 'Each step adds the same amount.'));
  assert.equal(state.received.map((h) => h.hint_level).join(','), '1,2');
  assert.equal(canRequestHint(state), true);

  state = recordHint(state, hint(3, 'Count on one more from 48.'));
  assert.equal(state.received.map((h) => h.hint_level).join(','), '1,2,3');
  // The ladder is exhausted; a fourth request would only earn a 409.
  assert.equal(canRequestHint(state), false);
});

test('received hints accumulate in level order rather than replacing', () => {
  // L2 elaborates on L1. A child who has lost L1 off-screen has lost the scaffold it gave them.
  const state = [hint(1, 'first'), hint(2, 'second'), hint(3, 'third')].reduce(
    recordHint,
    initialHintState('opportunity-1'),
  );
  assert.deepEqual(
    state.received.map((h) => h.content),
    ['first', 'second', 'third'],
  );
});

test('received hints stay in level order even if they arrive out of order', () => {
  const state = [hint(2, 'second'), hint(1, 'first')].reduce(
    recordHint,
    initialHintState('opportunity-1'),
  );
  assert.deepEqual(state.received.map((h) => h.hint_level), [1, 2]);
});

test('re-recording the same level does not duplicate it (a replayed key returns the original)', () => {
  const first = recordHint(initialHintState('opportunity-1'), hint(1, 'Look again.'));
  const replayed = recordHint(first, hint(1, 'Look again.'));
  assert.equal(replayed.received.length, 1);
});

// --- 409, the normal case -----------------------------------------------------------------------

// Only 2 of the 36 templates carry hint content, so roughly 94% of the time a child asks for help
// the very first request 409s. That is the DEFAULT case, not an error path.
test('a 409 on the first request closes hints for this opportunity', () => {
  const state = markHintsUnavailable(initialHintState('opportunity-1'));
  assert.equal(canRequestHint(state), false);
  assert.deepEqual(state.received, []);
});

test('a 409 on the first request is indistinguishable from a 409 after L3 — by design', () => {
  // The service maps "no hint content for this template", "blank content", "catalogue/bundle
  // checksum mismatch" and "already at L3" to the same neutral ConflictError, so that it can
  // "fail closed, never synthesize or approximate, never reveal the correct answer through the
  // error path" (hint_request.py). That neutrality is a governance property, not an oversight:
  // the client must not try to infer which 409 it received, and the information is genuinely not
  // there to infer from. These two paths therefore produce the same availability, and the copy
  // the child sees is the same in both.
  const noContentAtAll = markHintsUnavailable(initialHintState('opportunity-1'));
  const ladderExhausted = markHintsUnavailable(
    [hint(1, 'a'), hint(2, 'b'), hint(3, 'c')].reduce(recordHint, initialHintState('opportunity-1')),
  );
  assert.equal(canRequestHint(noContentAtAll), canRequestHint(ladderExhausted));
  assert.equal(canRequestHint(noContentAtAll), false);
});

test('unavailable is terminal for the opportunity — a later hint cannot reopen it', () => {
  const closed = markHintsUnavailable(initialHintState('opportunity-1'));
  assert.equal(canRequestHint(recordHint(closed, hint(1, 'late'))), false);
});

test('the unavailable copy closes the door gently and points forward', () => {
  const copy = HINTS_UNAVAILABLE_COPY.toLowerCase();
  // A child who has just admitted they need help must not be met with a rebuff, with blame for
  // asking, or with the suggestion that help was withheld as a consequence.
  for (const wrong of ['no hints available', 'not allowed', 'used up', 'sorry', "can't", 'denied']) {
    assert.ok(!copy.includes(wrong), `hint-unavailable copy must not read as "${wrong}"`);
  }
  assert.ok(copy.length > 0);
});

// --- per-opportunity scoping ----------------------------------------------------------------------

test('hint state resets on a new item_opportunity_id', () => {
  // Keyed on the opportunity id rather than a mount or a counter, so this stays correct when
  // FE-3e starts advancing the loop in place.
  const closed = markHintsUnavailable(
    recordHint(initialHintState('opportunity-1'), hint(1, 'first question')),
  );
  const next = hintStateFor(closed, 'opportunity-2');
  assert.equal(next.itemOpportunityId, 'opportunity-2');
  assert.deepEqual(next.received, []);
  assert.equal(canRequestHint(next), true);
});

test('hint state survives a re-presentation of the same opportunity (crash recovery)', () => {
  const state = recordHint(initialHintState('opportunity-1'), hint(1, 'keep me'));
  assert.equal(hintStateFor(state, 'opportunity-1'), state);
});

test('hintStateFor seeds from nothing on first render', () => {
  const state = hintStateFor(null, 'opportunity-1');
  assert.equal(state.itemOpportunityId, 'opportunity-1');
  assert.equal(canRequestHint(state), true);
});

// --- idempotency-key reuse --------------------------------------------------------------------------

const savedAssist: PendingRequestAssistCommand = {
  createdAt: '2026-07-30T09:00:00.000Z',
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/assists',
  idempotencyKey: 'assist-key-1',
  itemOpportunityId: 'opportunity-1',
  kind: 'request_assist',
  sessionId: 'session-1',
};

test('a persisted assist key for this opportunity is reused, not replaced', () => {
  // If the first request succeeded but its response was lost (network drop, app kill), a FRESH key
  // would make the server count that first event and escalate — the child would silently never see
  // L1, the gentlest hint, and land on L2. Replaying the saved key returns the original level and
  // content with no re-escalation.
  const decision = decidePendingAssist(savedAssist, 'session-1', 'opportunity-1');
  assert.equal(decision.action, 'reuse');
  if (decision.action !== 'reuse') return;
  assert.equal(decision.command.idempotencyKey, 'assist-key-1');
});

test('a persisted assist key for another opportunity or session is not reused', () => {
  assert.deepEqual(decidePendingAssist(savedAssist, 'session-1', 'opportunity-2'), { action: 'fresh' });
  assert.deepEqual(decidePendingAssist(savedAssist, 'session-2', 'opportunity-1'), { action: 'fresh' });
});

test('a persisted command of another kind is never mistaken for an assist key', () => {
  const submitCommand: PendingSessionCommand = {
    body: { client_elapsed_ms: 1200, submitted_value: '49' },
    createdAt: '2026-07-30T09:00:00.000Z',
    endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
    idempotencyKey: 'submit-key-1',
    itemOpportunityId: 'opportunity-1',
    kind: 'submit_response',
    sessionId: 'session-1',
  };
  assert.deepEqual(decidePendingAssist(submitCommand, 'session-1', 'opportunity-1'), { action: 'fresh' });
  assert.deepEqual(decidePendingAssist(null, 'session-1', 'opportunity-1'), { action: 'fresh' });
});
