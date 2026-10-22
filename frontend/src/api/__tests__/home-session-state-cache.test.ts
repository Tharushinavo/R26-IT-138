// Home's stale-while-revalidate progress cache (owner report, 2026-10-10).
//
// THE BUG. Home unmounts on every navigation and seeded its state with `not-in-progress`, so
// returning from Component C or Profile repainted "Ready to Play" / question 1 "Start here" until
// two sequential reads finished, then snapped to the real "Your Session" panel. The slower the
// link, the longer a child looks at a screen telling them they have not started a session they are
// halfway through.
//
// The behavioural half (cache semantics) is exercised directly. The wiring half is guarded
// structurally, because learner-home-screen.tsx is a large component with no render harness in
// `test:contract` -- the same approach presentation-ack-retry.test.ts already takes.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  clearHomeSessionStates,
  forgetHomeSessionState,
  readHomeSessionState,
  writeHomeSessionState,
} from '@/src/features/home/home-session-state-cache';
import type { HomeSessionState } from '@/src/features/home/session-progress';

const HOME = 'src/features/home/learner-home-screen.tsx';
const AUTH = 'src/auth/auth-context.tsx';
const homeSource = readFileSync(HOME, 'utf8');
const authSource = readFileSync(AUTH, 'utf8');

const inProgress = (completed: number): HomeSessionState => ({
  kind: 'in-progress',
  sessionId: 'session-1',
  completed,
  totalBound: 5,
});

// --- cache semantics -----------------------------------------------------------------------

test('an unknown learner reads as nothing known, so a cold start is unchanged', () => {
  clearHomeSessionStates();
  assert.equal(readHomeSessionState('subject-unknown'), null);
});

test('a written state is read back, which is what makes the next return instant', () => {
  clearHomeSessionStates();
  writeHomeSessionState('subject-1', inProgress(2));
  assert.deepEqual(readHomeSessionState('subject-1'), inProgress(2));
});

test('entries are per learner: a shared device never shows one child another child progress', () => {
  clearHomeSessionStates();
  writeHomeSessionState('subject-1', inProgress(3));
  assert.equal(readHomeSessionState('subject-2'), null);
});

test('a definitive not-in-progress overwrites a cached in-progress', () => {
  // The finished-session case. If this did not overwrite, a child who completed a session would
  // keep seeing it as in progress for the rest of the app session.
  clearHomeSessionStates();
  writeHomeSessionState('subject-1', inProgress(4));
  writeHomeSessionState('subject-1', { kind: 'not-in-progress' });
  assert.deepEqual(readHomeSessionState('subject-1'), { kind: 'not-in-progress' });
});

test('forget drops one learner and leaves others alone', () => {
  clearHomeSessionStates();
  writeHomeSessionState('subject-1', inProgress(1));
  writeHomeSessionState('subject-2', inProgress(2));
  forgetHomeSessionState('subject-1');
  assert.equal(readHomeSessionState('subject-1'), null);
  assert.deepEqual(readHomeSessionState('subject-2'), inProgress(2));
});

test('a null subject is a no-op in every direction, never a shared bucket', () => {
  clearHomeSessionStates();
  writeHomeSessionState(null, inProgress(1));
  assert.equal(readHomeSessionState(null), null);
  // And must not have created an entry some other lookup could collide with.
  assert.equal(readHomeSessionState('null'), null);
  assert.equal(readHomeSessionState('undefined'), null);
  forgetHomeSessionState(null); // must not throw
});

// --- wiring guards -------------------------------------------------------------------------

test('Home seeds its state from the cache rather than always from the neutral state', () => {
  assert.match(
    homeSource,
    /readHomeSessionState\(subject\) \?\? \{ kind: 'not-in-progress' \}/,
    `${HOME} must seed from the last resolved state, falling back to neutral`,
  );
  // Lazy initialiser, so the lookup happens on mount rather than on every render.
  assert.match(homeSource, /useState<HomeSessionState>\(\s*\(\) =>/);
});

test('the definitive "no active session" answer is cached, not silently skipped', () => {
  // This branch used to `return` without touching state, which was only safe because the state
  // always started neutral. With a seeded cache it is what lets a finished session clear.
  const branch = homeSource.slice(
    homeSource.indexOf("if (!session || session.state !== 'active')"),
    homeSource.indexOf('const summary = await api.getSessionSummary'),
  );
  assert.ok(branch.length > 0, 'the no-active-session branch must still exist');
  assert.match(
    branch,
    /applyResolvedSessionState\(\{ kind: 'not-in-progress' \}\)/,
    'a definitive "nothing in progress" must be recorded, or a finished session never clears',
  );
});

test('a FAILED read does not overwrite the last confirmed state', () => {
  // The whole point of the cache: an error is not an answer. Caching a neutral state on failure
  // would reintroduce the flash on any flaky request.
  const catchBlock = homeSource.slice(
    homeSource.indexOf('} catch {', homeSource.indexOf('getSessionSummary')),
  );
  const firstBlock = catchBlock.slice(0, catchBlock.indexOf('}, ['));
  assert.doesNotMatch(
    firstBlock,
    /writeHomeSessionState|applyResolvedSessionState|setSessionState/,
    'the catch path must leave the last server-confirmed state on screen',
  );
});

test('the cache write is not gated on the component still being mounted', () => {
  // Navigating away mid-read is exactly when remembering the answer matters most -- it is what
  // makes the NEXT return instant. Only setState is mount-guarded.
  const fn = homeSource.slice(
    homeSource.indexOf('const applyResolvedSessionState'),
    homeSource.indexOf('// Two best-effort reads'),
  );
  const writeAt = fn.indexOf('writeHomeSessionState(subject, next)');
  const guardAt = fn.indexOf('if (!mountedRef.current) return;');
  assert.notEqual(writeAt, -1);
  assert.notEqual(guardAt, -1);
  assert.ok(writeAt < guardAt, 'the cache write must precede the mounted guard');
});

test('sign-out forgets the cached progress, scoped to the outgoing learner', () => {
  assert.match(
    authSource,
    /forgetHomeSessionState\(me\?\.principal\.user_id \?\? null\)/,
    `${AUTH} must drop Home progress on sign-out, scoped like clearLearnerSessionRecords`,
  );
  // Scoped, never a blanket sweep -- a shared classroom device may hold a second learner's entry.
  assert.doesNotMatch(authSource, /clearHomeSessionStates\(\)/);
});

test('the expired-token path deliberately does NOT forget', () => {
  // An expired token is not a change of learner -- the same rule clearLearnerSessionRecords
  // already follows, stated here so the two cannot drift apart.
  const clearLocal = authSource.slice(
    authSource.indexOf('const clearLocalSession'),
    authSource.indexOf('const signOut'),
  );
  assert.ok(clearLocal.length > 0, 'clearLocalSession must still be findable');
  assert.doesNotMatch(clearLocal, /forgetHomeSessionState/);
});
