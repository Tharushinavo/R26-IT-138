// Component C's pre-advance: fetching the next task while the child reads their verdict.
// FE-004, 2026-10-09.
//
// Component B has pre-advanced since 2026-09-27; C never did, so every "Next" press paid a full
// `next_task` round trip the child sat and watched. The reason this needed care rather than a
// copy-paste is that the two components' hazards run in OPPOSITE directions:
//
//   B must not pre-advance on a wrong answer, because advancing CLOSES the opportunity and the
//   child may still TRY AGAIN on it.
//
//   C's `retryTask` stays on the same instance and makes no network call, so there is nothing to
//   close -- but only `completed_correct` writes a terminal event, so after a WRONG answer the
//   instance is still unterminated and `next_task` resumes it, handing back the task already on
//   screen. Pre-advancing there is useless rather than dangerous.
//
// Either way the rule is the same -- matched answers only -- and these tests pin it, plus the
// keying that stops a stale prefetch being served for the wrong task.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const SCREEN_PATH = 'src/features/c-session/c-session-screen.tsx';
const screenSource = readFileSync(SCREEN_PATH, 'utf8');

type Parked = { cSessionId: string; afterInstanceId: string; promise: Promise<string> } | null;

/**
 * The resolution rule `loadNextTask` implements, in isolation: use the parked promise only when it
 * belongs to this session, fall back to a fresh request on a mismatch OR a rejection, and consume
 * the entry either way.
 */
async function resolveNextTask(
  parked: Parked,
  cSessionId: string,
  fresh: () => Promise<string>,
): Promise<{ task: string; usedPrefetch: boolean }> {
  if (parked && parked.cSessionId === cSessionId) {
    try {
      return { task: await parked.promise, usedPrefetch: true };
    } catch {
      return { task: await fresh(), usedPrefetch: false };
    }
  }
  return { task: await fresh(), usedPrefetch: false };
}

test('a matched answer is the only thing that pre-advances', () => {
  // The decision, as the effect expresses it. `feedback === null` is the surface still being
  // answered; `matched: false` is a wrong answer the child may retry on this same instance.
  const shouldPreAdvance = (feedback: { matched: boolean } | null) => feedback?.matched === true;

  assert.equal(shouldPreAdvance(null), false, 'not while the child is still answering');
  assert.equal(shouldPreAdvance({ matched: false }), false, 'not on a wrong answer -- retry stays here');
  assert.equal(shouldPreAdvance({ matched: true }), true, 'yes once the task is genuinely finished');
});

test('a parked prefetch is used, and consumed, for the session it belongs to', async () => {
  let freshCalls = 0;
  const fresh = async () => {
    freshCalls += 1;
    return 'fresh-task';
  };
  const parked: Parked = {
    afterInstanceId: 'instance-1',
    cSessionId: 'session-1',
    promise: Promise.resolve('prefetched-task'),
  };

  const result = await resolveNextTask(parked, 'session-1', fresh);
  assert.equal(result.task, 'prefetched-task');
  assert.equal(result.usedPrefetch, true);
  assert.equal(freshCalls, 0, 'the round trip must not be repeated when it is already in hand');
});

test('a prefetch from a different session is never served', async () => {
  const parked: Parked = {
    afterInstanceId: 'instance-1',
    cSessionId: 'session-OLD',
    promise: Promise.resolve('stale-task'),
  };

  const result = await resolveNextTask(parked, 'session-NEW', async () => 'fresh-task');
  assert.equal(result.task, 'fresh-task', 'a stale entry must not be handed to the child');
  assert.equal(result.usedPrefetch, false);
});

test('a rejected prefetch falls back to a fresh request rather than failing the child', async () => {
  const parked: Parked = {
    afterInstanceId: 'instance-1',
    cSessionId: 'session-1',
    promise: Promise.reject(new Error('network died')),
  };
  parked.promise.catch(() => undefined);

  const result = await resolveNextTask(parked, 'session-1', async () => 'fresh-task');
  assert.equal(result.task, 'fresh-task', 'a failed pre-advance must cost nothing');
  assert.equal(result.usedPrefetch, false);
});

// Structural guards: the logic above is the right shape, these prove the screen still has it.
test('the screen pre-advances only on a matched verdict', () => {
  assert.match(
    screenSource,
    /phase\.feedback\?\.matched !== true\) return;/,
    `${SCREEN_PATH} must restrict the pre-advance to a matched answer`,
  );
});

test('the prefetch is keyed by the instance it was fetched after', () => {
  assert.match(
    screenSource,
    /afterInstanceId: string;/,
    'the parked entry must record which instance it follows, or a stale task can be served',
  );
  assert.match(
    screenSource,
    /nextTaskPrefetchRef\.current\?\.afterInstanceId === afterInstanceId\) return;/,
    'the effect must not re-fire for an instance it has already prefetched',
  );
});

test('loadNextTask consumes the parked entry and tolerates a rejection', () => {
  assert.match(
    screenSource,
    /nextTaskPrefetchRef\.current = null;/,
    'the entry must be consumed, so a later re-entry re-fetches rather than reading stale data',
  );
  assert.match(
    screenSource,
    /parked\.promise\.catch\(\(\) => api\.nextTask\(cSessionId, accessToken\)\)/,
    'a rejected pre-advance must fall back to a fresh request',
  );
});
