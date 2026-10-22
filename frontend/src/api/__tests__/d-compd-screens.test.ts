// Component D (compD) screens moved into MathMingo (FE-3b). The behavioural parts (route mapping,
// local hint) are exercised directly; the screen-level rules are guarded structurally, the way
// home-session-state-cache.test.ts guards learner-home-screen.tsx, because these screens have no
// render harness under `test:contract`.

import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';

import { hrefFor } from '@/src/features/compd/compd-routes';
import { localMathHint } from '@/src/features/compd/utils/local-hint';

const COMPD_DIR = 'src/features/compd';
const read = (relative: string) => readFileSync(join(COMPD_DIR, relative), 'utf8');

function compdSources(dir = COMPD_DIR): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) return compdSources(path);
    return /\.(ts|tsx)$/.test(entry) ? [path] : [];
  });
}

const activity = read('screens/math-activity-screen.tsx');
const languageSelect = read('screens/language-select-screen.tsx');
const logo = read('screens/logo-screen.tsx');

// --- route mapping ---------------------------------------------------------------------------

test('compD screen names map onto the compD routes', () => {
  assert.equal(hrefFor('Splash', undefined), '/(learner)/compd/intro/splash');
  assert.equal(hrefFor('LanguageSelect', undefined), '/(learner)/compd/intro/language');
  assert.equal(hrefFor('StudentActivity', undefined), '/(learner)/compd/activity');
  assert.equal(hrefFor('MathActivity', undefined), '/(learner)/compd/activity');
  assert.equal(hrefFor('ProfileHistory', undefined), '/(learner)/compd/history');
  assert.equal(hrefFor('StudentTabs', { screen: 'StudentHome' }), '/(learner)/compd/home');
});

test('only sessionId travels as a route parameter -- never a learner id', () => {
  assert.deepEqual(hrefFor('ProfileResult', { sessionId: 's-1' }), {
    params: { sessionId: 's-1' },
    pathname: '/(learner)/compd/result',
  });
  assert.deepEqual(
    hrefFor('MathActivity', { studentId: 'learner-1' } as never),
    '/(learner)/compd/activity',
  );
});

test('the learning-path button opens MathMingo Home, the real learning path', () => {
  assert.equal(hrefFor('LearningPath', undefined), '/(learner)/home');
});

test('an unknown or teacher-only screen name lands on compD home, never a dead route', () => {
  assert.equal(hrefFor('TeacherDashboard', undefined), '/(learner)/compd/home');
  assert.equal(hrefFor('Login', undefined), '/(learner)/compd/home');
});

// --- hints are local only (plan v5, N2) ------------------------------------------------------

test('the hint is chosen from the topic, in the child language', () => {
  assert.match(localMathHint('Addition', 'en').text, /counting up/i);
  assert.match(localMathHint('Division', 'en').text, /equal groups/i);
  assert.notEqual(localMathHint('Addition', 'si').text, localMathHint('Addition', 'en').text);
  assert.ok(localMathHint('Unknown topic', 'en').text.length > 0);
});

test('no compD module calls an AI service or reads a client-side AI key', () => {
  for (const file of compdSources()) {
    const source = readFileSync(file, 'utf8');
    assert.equal(/generativelanguage\.googleapis|GEMINI_API_KEY|openai\.com/i.test(source), false, file);
  }
});

// --- storage and logging ---------------------------------------------------------------------

test('compD keeps no device storage of its own (theme is fixed, language lives on the server)', () => {
  for (const file of compdSources()) {
    const source = readFileSync(file, 'utf8');
    assert.equal(/async-storage|AsyncStorage|localStorage|SecureStore/.test(source), false, file);
  }
});

test('compD screens log nothing (compD used to log learner and session ids)', () => {
  for (const file of compdSources()) {
    assert.equal(/console\.(log|info|debug)\(/.test(readFileSync(file, 'utf8')), false, file);
  }
});

// --- the quiz -------------------------------------------------------------------------------

test('quiz: a new session id for every run, not one per screen mount (backlog B1)', () => {
  const startQuiz = activity.slice(activity.indexOf('const startQuiz = useCallback'));
  assert.match(startQuiz.slice(0, 800), /setSessionId\(Crypto\.randomUUID\(\)\)/);
  assert.equal(activity.includes('useMemo(() => `math_'), false);
});

test('quiz: an event carries no learner id, session id or answer text', () => {
  const build = activity.slice(activity.indexOf('function buildEvent('), activity.indexOf('async function finishQuestion'));
  for (const field of ['student_id', 'session_id', 'expected_answer', 'given_answer']) {
    assert.equal(build.includes(`${field}:`), false, field);
  }
});

test('quiz: the final submission is held and re-sent unchanged, with no Alert (web cannot show one)', () => {
  assert.equal(/Alert\.alert\(/.test(activity), false);
  assert.equal(/import \{[^}]*\bAlert\b[^}]*\} from 'react-native'/.test(activity), false);
  assert.match(activity, /pendingSubmitRef\.current = \{ sessionId, body: \{ language: lang, events: nextEvents \} \}/);
  assert.match(activity, /api\.createSessionProfile\(pending\.sessionId, pending\.body, accessToken\)/);
});

test('quiz: once the run is waiting to send, Submit and Skip cannot add the last answer again', () => {
  assert.match(activity, /async function handleSubmit\(\) \{\n\s+if \(pendingSubmitRef\.current \|\|/);
  assert.match(activity, /async function handleSkip\(\) \{\n\s+if \(pendingSubmitRef\.current \|\|/);
});

test('quiz: leaving a running quiz asks first, from the X and from Android back alike', () => {
  assert.match(activity, /if \(quizGateRef\.current === 'active'\) openLeaveRef\.current\(\)/);
  assert.match(activity, /onPress=\{openLeaveConfirm\}/);
  // Leaving happens only from the popup's own Leave button.
  assert.match(activity, /<LeaveQuizPopup lang=\{lang\} onKeepPlaying=\{keepPlaying\} onLeave=\{\(\) => navigation\.replace\('StudentHome'\)\} \/>/);
  assert.equal(activity.includes('TopBackButton'), false);
});

// --- the intro ------------------------------------------------------------------------------

test('intro: Confirm saves the intro as done on the server, then opens compD home', () => {
  assert.match(languageSelect, /api\.updateLearnerState\(\{ intro_completed: true, language: lang \}, accessToken\)/);
  assert.match(languageSelect, /writeCompdLearnerState\(subject, state\);\n\s+navigation\.replace\('StudentHome'\)/);
  assert.equal(languageSelect.includes("navigation.replace('Login')"), false);
});

test('intro: the logo no longer checks a compD login, and stops its timers when it closes', () => {
  assert.equal(/getStoredToken|getStoredUser|isTokenExpired/.test(logo), false);
  assert.match(logo, /navigation\.replace\('Splash'\)/);
  assert.match(logo, /timers\.forEach\(clearTimeout\);\n\s+loops\.forEach\(\(loop\) => loop\.stop\(\)\);/);
});
