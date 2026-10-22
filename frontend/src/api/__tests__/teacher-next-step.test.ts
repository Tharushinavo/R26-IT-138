// The learner-facing view of a teacher's decision (spec §4 steps 6-8).
//
// The spec asks Component 3 to prove its own filter with tests ("a filter is one WHERE clause away
// from being lost in a refactor"). These are the student-app half of that discipline: the rules
// this side owns are step 7 (a null decision renders NOTHING), step 8 (never cached, never
// persisted), §3.1 (no student id is ever sent) and §3.3 (wording is rendered verbatim, never
// mapped here). Each is asserted rather than described.
//
// The fetch behaviour is exercised directly against a stubbed `fetch`; the UI rules are structural
// checks on the screen's source, the same approach presentation-ack-retry.test.ts takes for a
// component with no render harness in `test:contract`.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test, { afterEach, beforeEach } from 'node:test';

import { fetchTeacherNextStep } from '@/src/api/teacher-next-step-api';

const SCREEN = 'src/features/profile/learner-profile-screen.tsx';
const API = 'src/api/teacher-next-step-api.ts';
const screenSource = readFileSync(SCREEN, 'utf8');
const apiSource = readFileSync(API, 'utf8');

/**
 * Comments stripped before matching. These files legitimately QUOTE the spec -- including the very
 * field names and vocabulary the rules forbid in code -- so scanning raw source would flag the
 * prose that documents the rule. The subject of every check below is what the code DOES.
 */
const stripComments = (src: string) =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1');

const BASE = 'https://component-three.test';
const originalFetch = globalThis.fetch;
let calls: { url: string; init: RequestInit | undefined }[] = [];

function stubFetch(status: number, body: unknown) {
  calls = [];
  globalThis.fetch = (async (url: string, init?: RequestInit) => {
    calls.push({ init, url: String(url) });
    return {
      json: async () => body,
      ok: status >= 200 && status < 300,
      status,
    };
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  process.env.EXPO_PUBLIC_T3_API_BASE_URL = BASE;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  delete process.env.EXPO_PUBLIC_T3_API_BASE_URL;
});

// --- what is sent ------------------------------------------------------------------------------

test('the learner token is sent, and NO student id ever is', async () => {
  // §3.1: "there is no student_id parameter, by design. The identity comes from the token."
  // §5: a student_id added "for testing" "becomes the way one child reads another's".
  stubFetch(200, { next_step: null });
  await fetchTeacherNextStep('learner-token-abc');

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${BASE}/api/v1/t3/me/next-step`);
  assert.doesNotMatch(calls[0].url, /student|learner_id|user_id|\?/i, 'no identity may ride in the URL');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers.Authorization, 'Bearer learner-token-abc');
  assert.equal(calls[0].init?.method, 'GET', 'reading a decision must never be a write');
});

test('no request is made at all when Component 3 is not configured', async () => {
  // The endpoint does not exist yet. An unset base URL must be silent, not a failed call per mount.
  delete process.env.EXPO_PUBLIC_T3_API_BASE_URL;
  stubFetch(200, { next_step: { headline: 'h', detail: 'd' } });
  assert.equal(await fetchTeacherNextStep('token'), null);
  assert.equal(calls.length, 0);
});

test('an empty token makes no request', async () => {
  stubFetch(200, { next_step: { headline: 'h', detail: 'd' } });
  assert.equal(await fetchTeacherNextStep(''), null);
  assert.equal(calls.length, 0);
});

// --- what comes back ---------------------------------------------------------------------------

test('a real decision is returned with its wording untouched', async () => {
  // §3.3: finished sentences, rendered verbatim. Nothing here may trim, re-case or reword.
  const headline = 'Your teacher picked something for you to practise';
  const detail = 'More practice on taking away';
  stubFetch(200, { next_step: { chosen_at: '2026-10-10', detail, headline, source: 'teacher' }, disclosure: 'Not clinical evidence.' });

  const result = await fetchTeacherNextStep('token');
  assert.deepEqual(result, { detail, disclosure: 'Not clinical evidence.', headline });
});

test('the common case -- next_step null -- resolves to null', async () => {
  stubFetch(200, { disclosure: 'x', next_step: null });
  assert.equal(await fetchTeacherNextStep('token'), null);
});

test('every failure resolves to null rather than surfacing an error to a child', async () => {
  // 404 is TODAY's behaviour: Component 3 has not built the endpoint. It must be indistinguishable
  // from "no decision", because the two render identically (§4 step 7).
  for (const status of [401, 403, 404, 500, 503]) {
    stubFetch(status, { detail: 'should be ignored' });
    assert.equal(await fetchTeacherNextStep('token'), null, `status ${status} must be silent`);
  }
});

test('a network failure resolves to null', async () => {
  globalThis.fetch = (async () => {
    throw new Error('offline');
  }) as unknown as typeof fetch;
  assert.equal(await fetchTeacherNextStep('token'), null);
});

test('a malformed or partial body resolves to null, never a half-rendered popup', async () => {
  const bad = [
    null,
    'a string',
    {},
    { next_step: 'not an object' },
    { next_step: { detail: 'only detail' } },
    { next_step: { headline: 'only headline' } },
    { next_step: { detail: 'd', headline: '   ' } }, // whitespace is not a headline
    { next_step: { detail: '', headline: 'h' } },
  ];
  for (const body of bad) {
    stubFetch(200, body);
    assert.equal(await fetchTeacherNextStep('token'), null, `${JSON.stringify(body)} must be rejected`);
  }
});

// --- the rules this side owns --------------------------------------------------------------------

test('nothing is cached or persisted -- step 8', () => {
  // A cached decision about one child appearing in another child's profile on a shared classroom
  // device is this feature's worst failure. The guard is that no storage of any kind is reachable
  // from this module, and that it holds no module-level mutable state.
  assert.doesNotMatch(apiSource, /AsyncStorage|SecureStore|localStorage|sessionStorage|writeWebSessionValue/);
  assert.doesNotMatch(apiSource, /^(const|let)\s+\w*[Cc]ache/m, 'no module-level cache');
  assert.doesNotMatch(apiSource, /new Map\(|new Set\(/, 'no module-level store');
});

test('the screen holds the decision in component state, not a module variable', () => {
  assert.match(screenSource, /const \[nextStep, setNextStep\] = useState<TeacherNextStep \| null>\(null\)/);
  // Refetched when the signed-in learner changes, so one account's decision cannot be left on
  // screen for the next.
  assert.match(screenSource, /me\?\.principal\.user_id/);
});

test('the dot renders ONLY when a decision exists -- step 7', () => {
  assert.match(
    screenSource,
    /\{nextStep \? <View style=\{styles\.avatarDot\} \/> : null\}/,
    'a null decision must render no dot at all -- no placeholder, no greyed-out badge',
  );
});

test('the message is opened by long press only, never a tap', () => {
  // The ethics of §2 in one gesture: reachable by an adult, not put in front of the child.
  assert.match(screenSource, /onLongPress=\{\(\) => setParentNotice\(nextStep \? 'message' : 'none'\)\}/);
  const avatar = screenSource.slice(
    screenSource.indexOf('accessibilityLabel="Profile picture"'),
    screenSource.indexOf('<AppText style={styles.avatarName}>'),
  );
  assert.ok(avatar.length > 0);
  assert.doesNotMatch(avatar, /\sonPress=/, 'a tap must not open it');
});

test('the wording is rendered verbatim -- no client-side mapping', () => {
  // §3.3: Component 3 owns the text "so it can be reviewed in one place".
  assert.match(screenSource, /\{nextStep\.headline\}/);
  assert.match(screenSource, /\{nextStep\.detail\}/);
  // No local vocabulary table that could drift from theirs: the screen must never see a raw code,
  // let alone translate one. Checked against CODE, since the comments quote §3.3 by name.
  assert.doesNotMatch(
    stripComments(screenSource),
    /proposed_action|teacher_modified_action|teacher_status/,
    'the screen must not handle Component 3 status codes at all',
  );
});

test('neither the screen nor the client carries forbidden vocabulary -- §3.4', () => {
  // "No screen may say diagnose, detect, screen, disorder, deficit, disability or impairment",
  // and a child-facing surface must not say why the system flagged anyone.
  for (const [name, src] of [[SCREEN, screenSource], [API, apiSource]] as const) {
    const code = stripComments(src);
    for (const word of ['diagnos', 'disorder', 'deficit', 'disabilit', 'impairment', 'dyscalculia', 'risk score', 'at risk']) {
      assert.doesNotMatch(code, new RegExp(word, 'i'), `${name} must not say "${word}"`);
    }
  }
});

test('the student app never reaches for Component 3 tables directly -- §5', () => {
  assert.doesNotMatch(stripComments(apiSource), /t3_recommendations|t3_recommendation_transitions/);
  assert.match(apiSource, /\/api\/v1\/t3\/me\/next-step/, 'it must go through the endpoint');
});
