// Component D (compD) API client: `/api/v1/d/*` on the host backend, through the same
// `requestJson` transport every other component uses (10 s timeout, error-envelope mapping,
// Accept-Language), in the shape of src/api/component-b-api.ts.
//
// DEVELOPMENT FIXTURE. Until the backend marks these routes Live (compD/plan/03-api-contract.md),
// `EXPO_PUBLIC_COMPONENT_D_DEV_FIXTURE` substitutes response DATA in development builds only --
// the same rule as EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE: it never changes an authorization
// decision, and it is inert unless EXPO_PUBLIC_APP_ENV is 'development'.

import { ApiClientError } from '@/src/api/errors';
import { requestJson } from '@/src/api/request';
import type { PublicConfig } from '@/src/config/env';
import type {
  DCognitiveProfile,
  DCognitiveProfileResponse,
  DLanguage,
  DLatestProfileResponse,
  DLearnerStateResponse,
  DLearnerStateUpdateRequest,
  DProfileCreateRequest,
  DProfileListResponse,
} from '@/src/features/compd/api/compd-types';
import {
  isDCognitiveProfileResponse,
  isDLatestProfileResponse,
  isDLearnerStateResponse,
  isDProfileListResponse,
} from '@/src/features/compd/api/compd-validation';

// Mirrors the contract's request constraints, so a request the server would 422 never leaves the
// device. The server stays the only judge of anything beyond shape.
export const D_EVENTS_MIN = 1;
export const D_EVENTS_MAX = 50;
export const D_HISTORY_LIMIT_MIN = 1;
export const D_HISTORY_LIMIT_MAX = 100;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type CompdApi = {
  getLearnerState: (accessToken: string) => Promise<DLearnerStateResponse>;
  updateLearnerState: (body: DLearnerStateUpdateRequest, accessToken: string) => Promise<DLearnerStateResponse>;
  createSessionProfile: (
    sessionId: string,
    body: DProfileCreateRequest,
    accessToken: string,
  ) => Promise<DCognitiveProfileResponse>;
  getSessionProfile: (sessionId: string, language: DLanguage, accessToken: string) => Promise<DCognitiveProfileResponse>;
  getLatestProfile: (language: DLanguage, accessToken: string) => Promise<DLatestProfileResponse>;
  listProfiles: (limit: number, language: DLanguage, accessToken: string) => Promise<DProfileListResponse>;
};

function invalid(message: string): never {
  throw new ApiClientError('invalid-request', message);
}

export function assertStateUpdate(body: DLearnerStateUpdateRequest) {
  if (body.intro_completed === undefined && body.language === undefined) {
    invalid('A learner-state update needs intro_completed or language.');
  }
  if (body.intro_completed !== undefined && body.intro_completed !== true) {
    invalid('intro_completed can only be set to true.');
  }
}

export function assertSessionId(sessionId: string) {
  if (!UUID_PATTERN.test(sessionId)) invalid('session_id must be a UUID.');
}

export function assertProfileCreate(body: DProfileCreateRequest) {
  const count = body.events.length;
  if (count < D_EVENTS_MIN || count > D_EVENTS_MAX) {
    invalid(`A profile needs between ${D_EVENTS_MIN} and ${D_EVENTS_MAX} events.`);
  }
  const questionIds = new Set(body.events.map((event) => event.question_id));
  if (questionIds.size !== count) invalid('Each question may appear only once per session.');
}

export function assertHistoryLimit(limit: number) {
  if (!Number.isInteger(limit) || limit < D_HISTORY_LIMIT_MIN || limit > D_HISTORY_LIMIT_MAX) {
    invalid(`limit must be between ${D_HISTORY_LIMIT_MIN} and ${D_HISTORY_LIMIT_MAX}.`);
  }
}

/**
 * Runs `call` with the learner's access token, refreshing once on a 401 -- the same single retry
 * src/api/client.ts makes for /me. No token at all is reported as 'unauthenticated' so screens can
 * show "please sign in again" and leave sign-out itself to the host.
 */
export async function withAccessToken<T>(
  getAccessToken: (refresh?: boolean) => Promise<string | null>,
  call: (accessToken: string) => Promise<T>,
): Promise<T> {
  const accessToken = await getAccessToken();
  if (!accessToken) throw new ApiClientError('unauthenticated', 'There is no signed-in session.');
  try {
    return await call(accessToken);
  } catch (error) {
    if (!(error instanceof ApiClientError) || error.kind !== 'unauthenticated') throw error;
    const refreshed = await getAccessToken(true);
    if (!refreshed) throw error;
    return call(refreshed);
  }
}

// --- development fixture ---------------------------------------------------------------------

export type CompdFixture = 'first-visit' | 'returning' | 'unavailable' | 'not-a-learner';
const FIXTURES: ReadonlySet<string> = new Set(['first-visit', 'returning', 'unavailable', 'not-a-learner']);

export function getCompdDevelopmentFixture(): CompdFixture | null {
  if (process.env.EXPO_PUBLIC_APP_ENV !== 'development') return null;
  const fixture = process.env.EXPO_PUBLIC_COMPONENT_D_DEV_FIXTURE?.trim();
  return fixture && FIXTURES.has(fixture) ? (fixture as CompdFixture) : null;
}

const FIXTURE_DELAY_MS = 400;

function fixtureProfile(sessionId: string, language: DLanguage, generatedAt: string): DCognitiveProfile {
  return {
    session_id: sessionId,
    memory_level: 'medium',
    attention_level: 'high',
    number_sense_level: 'medium',
    processing_speed_level: 'Moderate',
    confidence_score: 0.7,
    recommendation:
      language === 'si'
        ? 'සංවර්ධන දත්ත පමණි (dev fixture).'
        : 'Development fixture data only -- not a real profile.',
    model_version: 'dev-fixture',
    features: {
      accuracy: 0.7,
      avg_response_time_ms: 6200,
      response_time_std_ms: 1800,
      avg_attempts: 1.2,
      retry_rate: 0.2,
      hint_rate: 0.1,
      mean_clicks_per_question: 0.3,
      total_questions: 10,
    },
    generated_at: generatedAt,
  };
}

/** Exported for tests; the app reaches it only through `createCompdApi` in development. */
export function createCompdFixtureApi(fixture: CompdFixture, delayMs = FIXTURE_DELAY_MS): CompdApi {
  let state = { intro_completed: fixture === 'returning', language: 'en' as DLanguage };
  const profiles = new Map<string, string>();
  if (fixture === 'returning') profiles.set('00000000-0000-4000-8000-000000000001', '2026-10-19T09:00:00.000Z');

  async function settle() {
    if (delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
    if (fixture === 'unavailable') {
      throw new ApiClientError('unavailable', 'Development fixture: Component D is unavailable.', 503, 'dev-d-503');
    }
    if (fixture === 'not-a-learner') {
      throw new ApiClientError('forbidden', 'Development fixture: not a learner.', 403, 'dev-d-403');
    }
  }

  const newest = (language: DLanguage) =>
    [...profiles.entries()]
      .sort(([, a], [, b]) => b.localeCompare(a))
      .map(([id, at]) => fixtureProfile(id, language, at));

  return {
    async getLearnerState() {
      await settle();
      return { ...state, request_id: 'dev-d-state' };
    },
    async updateLearnerState(body) {
      assertStateUpdate(body);
      await settle();
      state = {
        intro_completed: state.intro_completed || body.intro_completed === true,
        language: body.language ?? state.language,
      };
      return { ...state, request_id: 'dev-d-state-update' };
    },
    async createSessionProfile(sessionId, body) {
      assertSessionId(sessionId);
      assertProfileCreate(body);
      await settle();
      if (!profiles.has(sessionId)) profiles.set(sessionId, new Date().toISOString());
      return { profile: fixtureProfile(sessionId, body.language, profiles.get(sessionId)!), request_id: 'dev-d-profile' };
    },
    async getSessionProfile(sessionId, language) {
      assertSessionId(sessionId);
      await settle();
      const at = profiles.get(sessionId);
      if (!at) throw new ApiClientError('server', 'Development fixture: no such session.', 404, 'dev-d-404');
      return { profile: fixtureProfile(sessionId, language, at), request_id: 'dev-d-profile' };
    },
    async getLatestProfile(language) {
      await settle();
      return { profile: newest(language)[0] ?? null, request_id: 'dev-d-latest' };
    },
    async listProfiles(limit, language) {
      assertHistoryLimit(limit);
      await settle();
      return { items: newest(language).slice(0, limit), request_id: 'dev-d-list' };
    },
  };
}

// --- real client -----------------------------------------------------------------------------

let fixtureApi: CompdApi | null = null;

export function createCompdApi(config: PublicConfig | null): CompdApi {
  const fixture = getCompdDevelopmentFixture();
  if (fixture) {
    // One shared fixture instance per app session, so an intro completed on one screen is still
    // completed on the next -- the fixture stands in for a server, and a server remembers.
    fixtureApi ??= createCompdFixtureApi(fixture);
    return fixtureApi;
  }
  if (!config) throw new ApiClientError('unavailable', 'The app is not configured to reach the server.');

  const q = (language: DLanguage) => `language=${encodeURIComponent(language)}`;

  return {
    getLearnerState: (accessToken) =>
      requestJson(config, { accessToken, method: 'GET', path: '/api/v1/d/learner/state', validate: isDLearnerStateResponse }),
    updateLearnerState: (body, accessToken) => {
      assertStateUpdate(body);
      return requestJson(config, {
        accessToken,
        body,
        method: 'POST',
        path: '/api/v1/d/learner/state',
        validate: isDLearnerStateResponse,
      });
    },
    createSessionProfile: (sessionId, body, accessToken) => {
      assertSessionId(sessionId);
      assertProfileCreate(body);
      return requestJson(config, {
        accessToken,
        body,
        method: 'POST',
        path: `/api/v1/d/sessions/${encodeURIComponent(sessionId)}/profile`,
        validate: isDCognitiveProfileResponse,
      });
    },
    getSessionProfile: (sessionId, language, accessToken) => {
      assertSessionId(sessionId);
      return requestJson(config, {
        accessToken,
        method: 'GET',
        path: `/api/v1/d/sessions/${encodeURIComponent(sessionId)}/profile?${q(language)}`,
        validate: isDCognitiveProfileResponse,
      });
    },
    getLatestProfile: (language, accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'GET',
        path: `/api/v1/d/learner/profiles/latest?${q(language)}`,
        validate: isDLatestProfileResponse,
      }),
    listProfiles: (limit, language, accessToken) => {
      assertHistoryLimit(limit);
      return requestJson(config, {
        accessToken,
        method: 'GET',
        path: `/api/v1/d/learner/profiles?limit=${limit}&${q(language)}`,
        validate: isDProfileListResponse,
      });
    },
  };
}
