import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';

import {
  clampCompleted,
  resultsView,
  type AttemptOutcome,
  type SessionProgress,
} from '@/src/features/session/live-session-logic';

const bound: SessionProgress = { completed: 5, totalBound: 5 };

// --- the clamp -----------------------------------------------------------------------------------

test('clampCompleted leaves the normal case untouched', () => {
  assert.equal(clampCompleted({ completed: 3, totalBound: 5 }), 3);
  assert.equal(clampCompleted(bound), 5);
  assert.equal(clampCompleted({ completed: 0, totalBound: 5 }), 0);
});

test('clampCompleted never lets a server anomaly render more than the bound', () => {
  // "6 of 5" must not reach a child.
  assert.equal(clampCompleted({ completed: 6, totalBound: 5 }), 5);
  assert.equal(clampCompleted({ completed: 99, totalBound: 5 }), 5);
});

test('clampCompleted floors at zero', () => {
  assert.equal(clampCompleted({ completed: -1, totalBound: 5 }), 0);
});

test('the clamp is applied to what is displayed, not just returned separately', () => {
  assert.equal(resultsView({ completed: 6, totalBound: 5 }).detail.includes('6'), false);
  assert.equal(resultsView({ completed: 6, totalBound: 5 }).detail, 'You finished 5 of 5 questions today.');
});

test('the bound is read from the response, whatever it is', () => {
  // No client-side session length exists to disagree with; the bound-literal guard in
  // session-advance.test.ts enforces that.
  assert.equal(resultsView({ completed: 7, totalBound: 12 }).detail, 'You finished 7 of 12 questions today.');
  assert.equal(resultsView({ completed: 1, totalBound: 1 }).detail, 'You finished 1 of 1 question today.');
});

// --- nothing evaluative leaks in -------------------------------------------------------------------

test('the results copy is identical for every possible outcome history', () => {
  // The strongest available guard that no score, count-correct, percentage or streak has crept in.
  // The client does see every response_matched during a session; accumulating them into a summary
  // would synthesise exactly the evaluative record the backend withholds from the child-facing
  // surface. A child who got everything wrong and a child who got everything right must see the
  // same screen — so these must all be byte-identical.
  const histories: readonly AttemptOutcome[][] = [
    [],
    ['correct', 'correct', 'correct', 'correct', 'correct'],
    ['incorrect', 'incorrect', 'incorrect', 'incorrect', 'incorrect'],
    ['correct', 'incorrect', 'timeout', 'correct', 'incorrect'],
    ['timeout', 'timeout', 'timeout', 'timeout', 'timeout'],
  ];
  const baseline = resultsView(bound);
  for (const history of histories) {
    assert.deepEqual(resultsView(bound, history), baseline, `history ${JSON.stringify(history)} changed the copy`);
  }
});

test('the results copy contains nothing evaluative', () => {
  const view = resultsView({ completed: 5, totalBound: 5 }, ['correct', 'incorrect', 'timeout']);
  const copy = `${view.headline} ${view.detail}`.toLowerCase();
  for (const forbidden of [
    'score', 'right', 'wrong', 'correct', 'incorrect', '%', 'percent', 'star',
    'streak', 'points', 'mastery', 'level', 'grade', 'best', 'perfect',
  ]) {
    assert.ok(!copy.includes(forbidden), `results copy must not mention "${forbidden}"`);
  }
});

test('resultsView is a pure function of the progress numbers', () => {
  // Same progress in, same copy out — no hidden accumulation between calls.
  assert.deepEqual(resultsView(bound), resultsView(bound));
});

// --- exit clears the stored active session id ---------------------------------------------------------

// The store reads Platform.OS and expo-secure-store at module scope, neither of which loads under
// the plain esbuild/tsx runner used by test:contract — same constraint, and the same fix, as
// pending-session-command.test.ts. Patching Module.prototype.require forces the web Map backend.
// This affects only this file's registry; node --test isolates each file into its own process.
type NodeRequire = (id: string) => unknown;
const originalRequire: NodeRequire = (
  Module.prototype as unknown as { require: NodeRequire }
).require;
(Module.prototype as unknown as { require: NodeRequire }).require = function patchedRequire(
  this: unknown,
  id: string,
) {
  if (id === 'react-native') return { Platform: { OS: 'web' } };
  if (id === 'expo-secure-store') {
    return {
      WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WHEN_UNLOCKED_THIS_DEVICE_ONLY',
      deleteItemAsync: async () => undefined,
      getItemAsync: async () => null,
      setItemAsync: async () => undefined,
    };
  }
  return originalRequire.call(this, id);
};

// eslint-disable-next-line @typescript-eslint/no-require-imports
const store: typeof import('@/src/features/session/session-command-store') = require('../../features/session/session-command-store');

test('exiting a finished session clears the stored active session id', async () => {
  // Left behind, it would let a later launch offer "Resume" and then try to resume a session the
  // server has already completed.
  const subject = 'subject-results-0000-1111-2222-333333333333';
  await store.saveActiveSessionId(subject, 'finished-session-1');
  assert.equal(await store.loadActiveSessionId(subject), 'finished-session-1');

  await store.clearActiveSessionId(subject);
  assert.equal(await store.loadActiveSessionId(subject), null);
});
