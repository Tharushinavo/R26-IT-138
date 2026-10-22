import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  dropBSessionPrefetch,
  peekBSessionPrefetch,
  putBSessionPrefetch,
  takeBSessionPrefetch,
} from '@/src/features/session/b-session-prefetch-cache';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');
const read = (path: string) => readFileSync(resolve(frontendRoot, path), 'utf8');

const result = (sessionId: string) =>
  Promise.resolve({ sessionId, presentation: { request_id: 'r' } } as never);

// --- the cache ------------------------------------------------------------------------------------

test('take is single-use, so a relaunch or retry never reads a stale question', async () => {
  putBSessionPrefetch('subject-1', result('session-1'));
  const first = takeBSessionPrefetch('subject-1');
  assert.notEqual(first, null);
  assert.equal(takeBSessionPrefetch('subject-1'), null);
});

test('peek does not consume, so the prep screen can check without stealing the handoff', async () => {
  putBSessionPrefetch('subject-2', result('session-2'));
  assert.notEqual(peekBSessionPrefetch('subject-2'), null);
  assert.notEqual(peekBSessionPrefetch('subject-2'), null);
  assert.notEqual(takeBSessionPrefetch('subject-2'), null);
  assert.equal(peekBSessionPrefetch('subject-2'), null);
});

test('entries are per learner and droppable', async () => {
  putBSessionPrefetch('subject-a', result('session-a'));
  assert.equal(peekBSessionPrefetch('subject-b'), null);
  dropBSessionPrefetch('subject-a');
  assert.equal(peekBSessionPrefetch('subject-a'), null);
});

// --- the clock hazard this design exists to bound -------------------------------------------------
//
// The prefetch lights the question's 5-minute timeout, which a re-issue never resets. A child who
// overruns it has their first real answer written as a TIMEOUT with submitted_value = None and
// never graded. These pin the three things that keep that window app-paced.

test('the prep screen auto-advances only a prefetched, non-resume, ready fresh start', () => {
  const source = read('src/features/session/session-preparation-screen.tsx');
  const effect = source.slice(source.indexOf('// AUTO-ADVANCE'), source.indexOf('const scrollRef'));
  assert.ok(effect.length > 0, 'auto-advance effect must exist');
  // A resume keeps its tap: re-entering work already in progress is a real choice, and its
  // question was already presented once so its deadline is already anchored either way.
  assert.match(effect, /resumableSessionId/);
  // Auto-advance applies only to a prefetch that came from Home's own press. (The comment here
  // used to say "no prefetch means no lit clock"; corrected 2026-10-10 -- the deadline is anchored
  // at PRESENTATION, so no clock is running on this screen in either case. The gate stays because
  // a child who arrived directly never asked to be sent straight in.)
  assert.match(effect, /peekBSessionPrefetch\(subject\)/);
  // Only from 'ready' -- every failure phase keeps its own copy and retry.
  assert.match(effect, /phase !== 'ready'/);
  // Exactly once per mount.
  assert.match(effect, /autoAdvancedRef\.current/);
});

test('a preloaded question skips the loading phase; every other caller still shows it', () => {
  const source = read('src/features/session/live-session-screen.tsx');
  assert.match(source, /if \(!preloaded\) setPhase\(\{ kind: 'loading' \}\)/);
  // The network call is skipped only when a preloaded question is in hand.
  assert.match(source, /preloaded \?\? \(await withToken\(\(token\) => api\.selectOpportunity\(sessionId, token\)\)\)/);
  // The handoff is only honoured for the session actually being opened.
  assert.match(source, /result\.sessionId === sessionId/);
});

test('the prefetch never calls checkReadiness, which the prep screen owns', () => {
  const source = read('src/features/session/b-session-prefetch.ts');
  assert.doesNotMatch(source, /api\.checkReadiness\(/);
  // Resume is preferred over starting a new session, matching startAdventure's own order.
  assert.ok(
    source.indexOf('resolveResumableSessionId') < source.indexOf('startSession'),
    'resume must be resolved before starting a new session',
  );
  // A relaunch between starting the session and selecting the question must still find it.
  assert.ok(
    source.indexOf('saveActiveSessionId') < source.indexOf('selectOpportunity'),
    'the session id must be persisted before the question is selected',
  );
});

test('Home starts the prefetch on both entry points, and only with a known subject', () => {
  const source = read('src/features/home/learner-home-screen.tsx');
  const helper = source.slice(source.indexOf('const startBSessionPrefetch'), source.indexOf('const scrollRef'));
  assert.match(helper, /if \(!subject\) return;/);
  // Both the hero CTA and the "Your Session" resume control prime it.
  const calls = source.match(/startBSessionPrefetch\(\);/g) ?? [];
  assert.equal(calls.length, 2);
});

// --- Home warms Component B while it is open (owner instruction, 2026-10-10) -------------------

test('Home starts the Component B bootstrap on mount, not only on a press', () => {
  const source = read('src/features/home/learner-home-screen.tsx');
  // Deferred so the bootstrap spends idle time rather than competing with Home's first frame.
  assert.match(
    source,
    /InteractionManager\.runAfterInteractions\(\(\) => startBSessionPrefetch\(\)\)/,
    'Home must warm the session + first question once it has settled',
  );
  assert.match(source, /return \(\) => task\.cancel\(\);/, 'and cancel it if Home unmounts first');
});

test('the warm-up and a later press share one bootstrap instead of racing', () => {
  // The press used to overwrite the cache entry unconditionally. With Home warming early that
  // would discard a prefetch already most of the way done -- which is the whole benefit.
  const source = read('src/features/home/learner-home-screen.tsx');
  const fn = source.slice(
    source.indexOf('const startBSessionPrefetch'),
    source.indexOf('WARM COMPONENT B'),
  );
  const peekAt = fn.indexOf('peekBSessionPrefetch(subject)');
  const putAt = fn.indexOf('putBSessionPrefetch(subject');
  assert.notEqual(peekAt, -1, 'it must peek before putting');
  assert.notEqual(putAt, -1);
  assert.ok(peekAt < putAt, 'the peek guard must come before the put');
});

test('warming early does not spend the answering budget', () => {
  // The rule this reverses existed because `selectOpportunity` was believed to start the child's
  // five-minute clock. It does not -- `anchor_presentation` anchors at PRESENTATION -- and the
  // reasoning must stay recorded next to the code that depends on it.
  const source = read('src/features/home/learner-home-screen.tsx');
  assert.match(source, /anchor_presentation/, 'the retraction must be cited where it is relied on');
  assert.doesNotMatch(
    source,
    /prefetch starts the question's 5-minute answer clock/,
    'the retracted claim must not survive anywhere in this file',
  );
});
