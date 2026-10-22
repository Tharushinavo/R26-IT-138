// Component D (compD) client: request shape, client-side contract limits, the single token-refresh
// retry, response validation, and the development fixture standing in for the server until the
// backend's `/api/v1/d/*` routes are Live (compD/plan/03-api-contract.md).

import assert from 'node:assert/strict';
import test from 'node:test';

import { ApiClientError } from '@/src/api/errors';
import type { PublicConfig } from '@/src/config/env';
import {
  createCompdApi,
  createCompdFixtureApi,
  D_EVENTS_MAX,
  getCompdDevelopmentFixture,
  withAccessToken,
} from '@/src/features/compd/api/compd-api';
import type { DCognitiveProfile, DInteractionEvent } from '@/src/features/compd/api/compd-types';
import {
  isDCognitiveProfileResponse,
  isDLatestProfileResponse,
  isDLearnerStateResponse,
  isDProfileListResponse,
} from '@/src/features/compd/api/compd-validation';

const SESSION_ID = '3f2b8c1e-9a4d-4e7b-8c2a-1d5e6f7a8b9c';

const config: PublicConfig = {
  apiBaseUrl: 'http://api.test',
  appEnvironment: 'development',
  supabasePublishableKey: 'test-key',
  supabaseUrl: 'http://supabase.test',
};

const event = (questionId: string): DInteractionEvent => ({
  attempts: 1,
  click_count: 2,
  difficulty: 'Easy',
  error_type: 'none',
  assist_used: false,
  response_matched: true,
  question_id: questionId,
  response_time_sec: 4.2,
  session_time_sec: 30,
  time_between_actions: 1.1,
  topic: 'Addition',
});

const profile = (overrides: Partial<DCognitiveProfile> = {}): DCognitiveProfile => ({
  attention_level: 'high',
  confidence_score: 0.7,
  features: {
    accuracy: 0.8,
    mean_clicks_per_question: 0.2,
    avg_attempts: 1.1,
    avg_response_time_ms: 5000,
    hint_rate: 0.1,
    response_time_std_ms: 900,
    retry_rate: 0.1,
    total_questions: 10,
  },
  generated_at: '2026-10-20T10:00:00Z',
  memory_level: 'medium',
  model_version: 'rule-based-v1',
  number_sense_level: 'low',
  processing_speed_level: 'Moderate',
  recommendation: 'Keep practising.',
  session_id: SESSION_ID,
  ...overrides,
});

type Captured = { url: string; init: RequestInit };

function stubFetch(status: number, body: unknown): Captured[] {
  const calls: Captured[] = [];
  globalThis.fetch = (async (url: string, init: RequestInit) => {
    calls.push({ init, url });
    return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' }, status });
  }) as typeof fetch;
  return calls;
}

function headersOf(call: Captured) {
  return call.init.headers as Record<string, string>;
}

// --- validators ------------------------------------------------------------------------------

test('learner state: accepts the contract shape and rejects drift', () => {
  assert.equal(isDLearnerStateResponse({ intro_completed: false, language: 'en', request_id: 'r' }), true);
  assert.equal(isDLearnerStateResponse({ intro_completed: 'no', language: 'en', request_id: 'r' }), false);
  assert.equal(isDLearnerStateResponse({ intro_completed: true, language: 'fr', request_id: 'r' }), false);
  assert.equal(isDLearnerStateResponse({ intro_completed: true, language: 'si' }), false);
});

test('profile: every level, speed and feature is checked', () => {
  assert.equal(isDCognitiveProfileResponse({ profile: profile(), request_id: 'r' }), true);
  // The contract wraps the profile (M-BE-013); the old flat shape must now be refused.
  assert.equal(isDCognitiveProfileResponse({ ...profile(), request_id: 'r' }), false);
  assert.equal(isDCognitiveProfileResponse({ profile: null, request_id: 'r' }), false);
  assert.equal(isDCognitiveProfileResponse({ profile: profile({ memory_level: 'Low' as never }), request_id: 'r' }), false);
  assert.equal(
    isDCognitiveProfileResponse({ profile: profile({ processing_speed_level: 'slow' as never }), request_id: 'r' }),
    false,
  );
  const missingFeature = profile();
  delete (missingFeature.features as Partial<DCognitiveProfile['features']>).total_questions;
  assert.equal(isDCognitiveProfileResponse({ profile: missingFeature, request_id: 'r' }), false);
});

test('latest: a null profile is a valid "no profile yet", never an error', () => {
  assert.equal(isDLatestProfileResponse({ profile: null, request_id: 'r' }), true);
  assert.equal(isDLatestProfileResponse({ profile: profile(), request_id: 'r' }), true);
  assert.equal(isDLatestProfileResponse({ request_id: 'r' }), false);
});

test('history: one malformed item rejects the whole list', () => {
  assert.equal(isDProfileListResponse({ items: [profile()], request_id: 'r' }), true);
  assert.equal(isDProfileListResponse({ items: [profile(), { session_id: 'x' }], request_id: 'r' }), false);
});

// --- real client: request shape --------------------------------------------------------------

test('reads go to /api/v1/d with the token and the language as a query parameter', async () => {
  const calls = stubFetch(200, { profile: null, request_id: 'r' });
  const result = await createCompdApi(config).getLatestProfile('si', 'token-1');
  assert.deepEqual(result, { profile: null, request_id: 'r' });
  assert.equal(calls[0].url, 'http://api.test/api/v1/d/learner/profiles/latest?language=si');
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(headersOf(calls[0]).Authorization, 'Bearer token-1');
});

test('the profile is POSTed to the session path with no learner identifier in the body', async () => {
  const calls = stubFetch(200, { profile: profile(), request_id: 'r' });
  await createCompdApi(config).createSessionProfile(SESSION_ID, { events: [event('Q1')], language: 'en' }, 't');
  assert.equal(calls[0].url, `http://api.test/api/v1/d/sessions/${SESSION_ID}/profile`);
  assert.equal(calls[0].init.method, 'POST');
  const body = JSON.parse(String(calls[0].init.body));
  assert.deepEqual(Object.keys(body).sort(), ['events', 'language']);
  for (const key of ['student_id', 'user_id', 'learner_id', 'session_id']) {
    assert.equal(key in body.events[0], false, `${key} must not be sent`);
  }
});

test('the learner state is saved with POST, never PUT (the host transport is GET/POST only)', async () => {
  const calls = stubFetch(200, { intro_completed: true, language: 'en', request_id: 'r' });
  await createCompdApi(config).updateLearnerState({ intro_completed: true }, 't');
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].url, 'http://api.test/api/v1/d/learner/state');
});

test('a response that breaks the contract is rejected as invalid-response', async () => {
  stubFetch(200, { intro_completed: true });
  await assert.rejects(createCompdApi(config).getLearnerState('t'), (error: unknown) => {
    return error instanceof ApiClientError && error.kind === 'invalid-response';
  });
});

test('no config and no fixture fails as unavailable instead of crashing', () => {
  assert.throws(() => createCompdApi(null), (error: unknown) => {
    return error instanceof ApiClientError && error.kind === 'unavailable';
  });
});

// --- client-side contract limits -------------------------------------------------------------

test('requests the server would 422 never leave the device', async () => {
  const calls = stubFetch(200, {});
  const api = createCompdApi(config);
  assert.throws(() => api.updateLearnerState({}, 't'));
  assert.throws(() => api.createSessionProfile('not-a-uuid', { events: [event('Q1')], language: 'en' }, 't'));
  assert.throws(() => api.createSessionProfile(SESSION_ID, { events: [], language: 'en' }, 't'));
  const tooMany = Array.from({ length: D_EVENTS_MAX + 1 }, (_, index) => event(`Q${index}`));
  assert.throws(() => api.createSessionProfile(SESSION_ID, { events: tooMany, language: 'en' }, 't'));
  assert.throws(() => api.createSessionProfile(SESSION_ID, { events: [event('Q1'), event('Q1')], language: 'en' }, 't'));
  assert.throws(() => api.listProfiles(0, 'en', 't'));
  assert.throws(() => api.listProfiles(101, 'en', 't'));
  assert.equal(calls.length, 0);
});

// --- token handling --------------------------------------------------------------------------

test('a 401 is retried exactly once with a refreshed token', async () => {
  const tokensAsked: boolean[] = [];
  const used: string[] = [];
  const result = await withAccessToken(
    async (refresh = false) => {
      tokensAsked.push(refresh);
      return refresh ? 'fresh' : 'stale';
    },
    async (token) => {
      used.push(token);
      if (token === 'stale') throw new ApiClientError('unauthenticated', 'expired', 401);
      return 'ok';
    },
  );
  assert.equal(result, 'ok');
  assert.deepEqual(tokensAsked, [false, true]);
  assert.deepEqual(used, ['stale', 'fresh']);
});

test('no session at all is reported as unauthenticated without calling the server', async () => {
  let called = false;
  await assert.rejects(
    withAccessToken(async () => null, async () => {
      called = true;
    }),
    (error: unknown) => error instanceof ApiClientError && error.kind === 'unauthenticated',
  );
  assert.equal(called, false);
});

test('other failures are not retried', async () => {
  let attempts = 0;
  await assert.rejects(
    withAccessToken(async () => 't', async () => {
      attempts += 1;
      throw new ApiClientError('network', 'down');
    }),
  );
  assert.equal(attempts, 1);
});

// --- development fixture ---------------------------------------------------------------------

test('the fixture is inert outside a development build', () => {
  const saved = { ...process.env };
  process.env.EXPO_PUBLIC_COMPONENT_D_DEV_FIXTURE = 'returning';
  process.env.EXPO_PUBLIC_APP_ENV = 'production';
  assert.equal(getCompdDevelopmentFixture(), null);
  process.env.EXPO_PUBLIC_APP_ENV = 'development';
  assert.equal(getCompdDevelopmentFixture(), 'returning');
  process.env.EXPO_PUBLIC_COMPONENT_D_DEV_FIXTURE = 'made-up';
  assert.equal(getCompdDevelopmentFixture(), null);
  process.env = saved;
});

test('fixture first visit: intro not done, no profile; completing it sticks', async () => {
  const api = createCompdFixtureApi('first-visit', 0);
  assert.equal((await api.getLearnerState('t')).intro_completed, false);
  assert.equal((await api.getLatestProfile('en', 't')).profile, null);
  await api.updateLearnerState({ intro_completed: true, language: 'si' }, 't');
  const state = await api.getLearnerState('t');
  assert.equal(state.intro_completed, true);
  assert.equal(state.language, 'si');
  // A language-only update can never un-complete the intro.
  await api.updateLearnerState({ language: 'en' }, 't');
  assert.equal((await api.getLearnerState('t')).intro_completed, true);
});

test('fixture: a repeated profile POST for one session returns the same profile', async () => {
  const api = createCompdFixtureApi('first-visit', 0);
  const first = await api.createSessionProfile(SESSION_ID, { events: [event('Q1')], language: 'en' }, 't');
  const again = await api.createSessionProfile(SESSION_ID, { events: [event('Q1')], language: 'en' }, 't');
  assert.equal(again.profile.generated_at, first.profile.generated_at);
  assert.equal((await api.listProfiles(20, 'en', 't')).items.length, 1);
});

test('fixture failure modes map to the error kinds the gate handles', async () => {
  await assert.rejects(createCompdFixtureApi('unavailable', 0).getLearnerState('t'), (error: unknown) => {
    return error instanceof ApiClientError && error.kind === 'unavailable';
  });
  await assert.rejects(createCompdFixtureApi('not-a-learner', 0).getLearnerState('t'), (error: unknown) => {
    return error instanceof ApiClientError && error.kind === 'forbidden';
  });
});
