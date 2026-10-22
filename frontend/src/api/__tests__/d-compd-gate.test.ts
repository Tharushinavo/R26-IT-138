// Component D (compD) entry: where the compD tab sends a learner, the per-learner state cache,
// which screens show the tab bar, and the sign-out wiring that keeps a shared device honest.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { ApiClientError } from '@/src/api/errors';
import {
  classifyGateFailure,
  COMPD_GATE_HREF,
  COMPD_HOME_HREF,
  COMPD_INTRO_HREF,
  compdEntryHref,
  destinationFor,
  introAlwaysShown,
} from '@/src/features/compd/compd-gate';
import {
  clearCompdLearnerStates,
  forgetCompdLearnerState,
  readCompdLearnerState,
  writeCompdLearnerState,
} from '@/src/features/compd/compd-state-cache';
import { compdHeaderVisible, tabBarFor } from '@/src/features/navigation/learner-tab-visibility';

// --- routing decisions -----------------------------------------------------------------------

test('first visit goes to the intro; a completed intro goes straight to compD home', () => {
  assert.equal(destinationFor({ intro_completed: false, language: 'en' }), COMPD_INTRO_HREF);
  assert.equal(destinationFor({ intro_completed: true, language: 'si' }), COMPD_HOME_HREF);
});

test('the tab skips the gate only when this session already knows the intro is done', () => {
  assert.equal(compdEntryHref(null), COMPD_GATE_HREF);
  assert.equal(compdEntryHref({ intro_completed: false, language: 'en' }), COMPD_GATE_HREF);
  assert.equal(compdEntryHref({ intro_completed: true, language: 'en' }), COMPD_HOME_HREF);
});

test('a failure is never mistaken for a first visit', () => {
  assert.equal(classifyGateFailure(new ApiClientError('unauthenticated', 'x', 401)), 'sign-in-needed');
  assert.equal(classifyGateFailure(new ApiClientError('forbidden', 'x', 403)), 'not-a-learner');
  // The host reports "no learner yet" as 404, which requestJson maps to kind 'server'.
  assert.equal(classifyGateFailure(new ApiClientError('server', 'x', 404)), 'not-a-learner');
  assert.equal(classifyGateFailure(new ApiClientError('server', 'x', 500)), 'unreachable');
  assert.equal(classifyGateFailure(new ApiClientError('network', 'x')), 'unreachable');
  assert.equal(classifyGateFailure(new ApiClientError('timeout', 'x')), 'unreachable');
  assert.equal(classifyGateFailure(new ApiClientError('invalid-response', 'x', 200)), 'unreachable');
  assert.equal(classifyGateFailure(new Error('boom')), 'unreachable');
});

// --- state cache -----------------------------------------------------------------------------

test('cache: unknown and signed-out learners read as nothing known', () => {
  clearCompdLearnerStates();
  assert.equal(readCompdLearnerState('subject-1'), null);
  assert.equal(readCompdLearnerState(null), null);
  writeCompdLearnerState(null, { intro_completed: true, language: 'en' });
  assert.equal(readCompdLearnerState(null), null);
});

test('cache: entries are per learner, so one child never inherits another child intro', () => {
  clearCompdLearnerStates();
  writeCompdLearnerState('subject-1', { intro_completed: true, language: 'si' });
  assert.deepEqual(readCompdLearnerState('subject-1'), { intro_completed: true, language: 'si' });
  assert.equal(readCompdLearnerState('subject-2'), null);
  forgetCompdLearnerState('subject-1');
  assert.equal(readCompdLearnerState('subject-1'), null);
});

test('cache: stores state only, not transport fields such as request_id', () => {
  clearCompdLearnerStates();
  writeCompdLearnerState('subject-1', { intro_completed: true, language: 'en', request_id: 'r' } as never);
  assert.deepEqual(readCompdLearnerState('subject-1'), { intro_completed: true, language: 'en' });
});

// --- tab bar visibility ----------------------------------------------------------------------

test('tab bar: hidden only while compD quiz questions are showing, which have their own confirm-before-leaving', () => {
  assert.deepEqual(tabBarFor('/compd/activity', true), { visible: false });
});

test('tab bar: the quiz Start/Resume page keeps it, because that page has no Back control', () => {
  // Owner request 2026-10-21 removed Back there; the bar is the child way out on iOS and web.
  assert.deepEqual(tabBarFor('/compd/activity'), { activePressEnabled: true, activeTab: 'compd', visible: true });
  assert.deepEqual(tabBarFor('/compd/activity', false), { activePressEnabled: true, activeTab: 'compd', visible: true });
});

test('tab bar: the gate and intro open inside the chrome, compD current, and re-pressing it does nothing', () => {
  // Owner request 2026-10-21: header and tab bar stay, the intro fills the space between them.
  for (const path of ['/compd', '/compd/', '/compd/intro/logo', '/compd/intro/splash', '/compd/intro/language']) {
    assert.deepEqual(tabBarFor(path), { activePressEnabled: false, activeTab: 'compd', visible: true }, path);
  }
});

test('header: on every compD page except the quiz', () => {
  for (const path of ['/compd', '/compd/intro/logo', '/compd/intro/language', '/compd/home', '/compd/result', '/compd/history']) {
    assert.equal(compdHeaderVisible(path), true, path);
  }
  assert.equal(compdHeaderVisible('/compd/activity'), false);
});

test('preview switch: replays the intro in development only, and is off by default', () => {
  const saved = { ...process.env };
  const done = { intro_completed: true, language: 'en' } as const;
  delete process.env.EXPO_PUBLIC_COMPONENT_D_ALWAYS_SHOW_INTRO;
  process.env.EXPO_PUBLIC_APP_ENV = 'development';
  assert.equal(introAlwaysShown(), false);
  assert.equal(destinationFor(done), COMPD_HOME_HREF);

  process.env.EXPO_PUBLIC_COMPONENT_D_ALWAYS_SHOW_INTRO = 'true';
  assert.equal(introAlwaysShown(), true);
  assert.equal(destinationFor(done), COMPD_INTRO_HREF);
  assert.equal(compdEntryHref(done), COMPD_GATE_HREF);

  process.env.EXPO_PUBLIC_APP_ENV = 'production';
  assert.equal(introAlwaysShown(), false, 'must be inert outside development');
  assert.equal(destinationFor(done), COMPD_HOME_HREF);
  process.env = saved;
});

test('tab bar: other compD pages show compD current; pressing it returns to compD home', () => {
  assert.deepEqual(tabBarFor('/compd/home'), { activePressEnabled: false, activeTab: 'compd', visible: true });
  assert.deepEqual(tabBarFor('/compd/history'), { activePressEnabled: true, activeTab: 'compd', visible: true });
  assert.deepEqual(tabBarFor('/compd/result'), { activePressEnabled: true, activeTab: 'compd', visible: true });
});

test('tab bar: the learner profile keeps the bar with no tab current', () => {
  assert.deepEqual(tabBarFor('/profile'), { activePressEnabled: false, activeTab: null, visible: true });
});

test('tab bar: Home behaviour is unchanged, and game surfaces stay bar-free', () => {
  assert.deepEqual(tabBarFor('/home'), { activePressEnabled: false, activeTab: 'home', visible: true });
  assert.deepEqual(tabBarFor('/prepare'), { activePressEnabled: true, activeTab: 'home', visible: true });
  assert.deepEqual(tabBarFor('/c-session'), { visible: false });
  assert.deepEqual(tabBarFor('/session/abc'), { visible: false });
});

// --- wiring (structural, as home-session-state-cache.test.ts does) ---------------------------

const authSource = readFileSync('src/auth/auth-context.tsx', 'utf8');
const tabBarSource = readFileSync('src/features/navigation/learner-tab-bar.tsx', 'utf8');

test('sign-out forgets the outgoing learner compD state', () => {
  const signOut = authSource.slice(authSource.indexOf('const signOut = useCallback'));
  assert.match(signOut.slice(0, signOut.indexOf('}, [config, me]')), /forgetCompdLearnerState\(me\?\.principal\.user_id \?\? null\)/);
});

test('an expired token (clearLocalSession) is not a change of learner and keeps the cache', () => {
  const start = authSource.indexOf('const clearLocalSession');
  const clearLocal = authSource.slice(start, authSource.indexOf('}, []);', start));
  assert.equal(clearLocal.includes('forgetCompdLearnerState'), false);
});

test('the compD tab reads the cache at press time, not render time', () => {
  assert.match(tabBarSource, /onPress=\{\(\) => router\.replace\(compdEntryHref\(readCompdLearnerState\(/);
});
