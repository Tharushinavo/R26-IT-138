import type { HealthReadyResponse, SessionCommandResponse } from '@/src/api/contracts';
import { requestJson } from '@/src/api/request';
import { ApiClientError } from '@/src/api/errors';
import {
  isActiveSessionResponse,
  isAttemptResponse,
  isHealthReadyResponse,
  isHintRequestResponse,
  isLearnerSkillStatesResponse,
  isOpportunityAdvanceResponse,
  isPresentationAckResponse,
  isOpportunityPresentationResponse,
  isSessionCommandResponse,
  isSessionStandingResponse,
} from '@/src/api/runtime-validation';
import type {
  ActiveSessionResponse,
  AttemptResponse,
  HintRequestResponse,
  LearnerSkillStatesResponse,
  OpportunityAdvanceResponse,
  OpportunityPresentationResponse,
  PresentationAckResponse,
  SessionStandingResponse,
} from '@/src/api/generated/openapi-types';
import type { PublicConfig } from '@/src/config/env';

// Mirrors SubmitResponseRequest's own constraints (app/domain/b_attempt.py) exactly — not answer
// validation. The server alone judges correctness; this only stops a malformed request (one the
// server would 422 anyway) from leaving the device.
const SUBMITTED_VALUE_MIN_LENGTH = 1;
const SUBMITTED_VALUE_MAX_LENGTH = 255;
const CLIENT_ELAPSED_MS_MAX = 3_600_000;

export type SubmitResponseBody = {
  submitted_value: string;
  client_elapsed_ms?: number;
};

function normalizeSubmitResponseBody(body: SubmitResponseBody) {
  if (
    body.submitted_value.length < SUBMITTED_VALUE_MIN_LENGTH ||
    body.submitted_value.length > SUBMITTED_VALUE_MAX_LENGTH
  ) {
    throw new ApiClientError(
      'invalid-request',
      `submitted_value must be between ${SUBMITTED_VALUE_MIN_LENGTH} and ${SUBMITTED_VALUE_MAX_LENGTH} characters.`,
    );
  }
  if (body.client_elapsed_ms === undefined) {
    return { submitted_value: body.submitted_value };
  }
  const clientElapsedMs = Math.max(0, Math.min(body.client_elapsed_ms, CLIENT_ELAPSED_MS_MAX));
  return { client_elapsed_ms: clientElapsedMs, submitted_value: body.submitted_value };
}

type ComponentBApi = {
  checkReadiness: () => Promise<HealthReadyResponse>;
  startSession: (idempotencyKey: string, accessToken: string) => Promise<SessionCommandResponse>;
  getActiveSession: (accessToken: string) => Promise<ActiveSessionResponse>;
  getLearnerSkillStates: (accessToken: string) => Promise<LearnerSkillStatesResponse>;
  selectOpportunity: (sessionId: string, accessToken: string) => Promise<OpportunityPresentationResponse>;
  acknowledgePresentation: (
    sessionId: string,
    itemOpportunityId: string,
    accessToken: string,
  ) => Promise<PresentationAckResponse>;
  submitResponse: (
    sessionId: string,
    itemOpportunityId: string,
    idempotencyKey: string,
    body: SubmitResponseBody,
    accessToken: string,
  ) => Promise<AttemptResponse>;
  requestAssist: (
    sessionId: string,
    itemOpportunityId: string,
    idempotencyKey: string,
    accessToken: string,
  ) => Promise<HintRequestResponse>;
  completeOpportunity: (
    sessionId: string,
    itemOpportunityId: string,
    idempotencyKey: string,
    accessToken: string,
  ) => Promise<OpportunityAdvanceResponse>;
  getSessionSummary: (sessionId: string, accessToken: string) => Promise<SessionStandingResponse>;
};

const fixtureFailures = new Set<string>();

function getDevelopmentFixture(): string | null {
  if (process.env.EXPO_PUBLIC_APP_ENV !== 'development') return null;
  const fixture = process.env.EXPO_PUBLIC_COMPONENT_B_DEV_FIXTURE?.trim();
  return fixture || null;
}

async function fixtureDelay() {
  await new Promise((resolve) => setTimeout(resolve, 650));
}

function createFixtureApi(fixture: string): ComponentBApi {
  return {
    async checkReadiness() {
      await fixtureDelay();
      if (fixture === 'readiness-failure') {
        throw new ApiClientError('unavailable', 'Development readiness fixture is unavailable.', 503, 'dev-ready-503');
      }
      return {
        status: 'ready',
        stage: 'infrastructure',
        request_id: 'dev-ready-ok',
        checks: {
          api_process: 'ok',
          database_connection: 'ok',
          generator: 'not_checked',
          catalogue: 'not_checked',
          runtime_bundle: 'not_checked',
          migrations: 'not_checked',
          authentication: 'not_checked',
        },
      };
    },
    async startSession(idempotencyKey) {
      await fixtureDelay();
      if (fixture === 'network-failure-once' && !fixtureFailures.has(idempotencyKey)) {
        fixtureFailures.add(idempotencyKey);
        throw new ApiClientError('network', 'Development fixture dropped the response.');
      }
      if (fixture === 'access-denied') {
        throw new ApiClientError('forbidden', 'Development access fixture denied the request.', 403, 'dev-forbidden');
      }
      return {
        created_at_utc: '2026-07-22T12:00:00Z',
        request_id: 'dev-start-ok',
        row_version: 1,
        runtime_bundle_version: 'development-fixture-only',
        session_id: 'dev-session-new-opaque',
        state: 'active',
      };
    },
    // The fixture covers the prep screen's readiness/start path only. The session loop itself
    // (opportunity selection, response submission, hints, completion, standing) is deliberately
    // left unimplemented — an immediate throw, no delay, no fake payload — so a fixture run can
    // never masquerade as a real session past the prep screen.
    async getActiveSession() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement session recovery.');
    },
    async getLearnerSkillStates() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement skill states.');
    },
    async acknowledgePresentation() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement presentation acknowledgement.');
    },
    async selectOpportunity() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement opportunity selection.');
    },
    async submitResponse() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement response submission.');
    },
    async requestAssist() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement hint requests.');
    },
    async completeOpportunity() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement opportunity completion.');
    },
    async getSessionSummary() {
      throw new ApiClientError('unavailable', 'The development fixture does not implement session standing.');
    },
  };
}

export function createComponentBApi(config?: PublicConfig): ComponentBApi {
  const fixture = getDevelopmentFixture();
  if (fixture) return createFixtureApi(fixture);
  if (!config) {
    throw new ApiClientError('unavailable', 'The Component B API is not configured.');
  }

  return {
    checkReadiness: () => requestJson(config, { method: 'GET', path: '/health/ready', validate: isHealthReadyResponse }),
    startSession: (idempotencyKey, accessToken) =>
      requestJson(config, {
        accessToken,
        idempotencyKey,
        method: 'POST',
        path: '/api/v1/b/sessions',
        validate: isSessionCommandResponse,
      }),
    getActiveSession: (accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'GET',
        path: '/api/v1/b/sessions/active',
        validate: isActiveSessionResponse,
      }),
    acknowledgePresentation: (sessionId, itemOpportunityId, accessToken) =>
      // No idempotency key and no body, matching the route: the first call anchors the clock and
      // every later one returns that same deadline, so a retry is safe by construction.
      requestJson(config, {
        accessToken,
        method: 'POST',
        path: `/api/v1/b/sessions/${sessionId}/opportunities/${itemOpportunityId}/presented`,
        validate: isPresentationAckResponse,
      }),
    getLearnerSkillStates: (accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'GET',
        path: '/api/v1/b/learner/skill-states',
        validate: isLearnerSkillStatesResponse,
      }),
    selectOpportunity: (sessionId, accessToken) =>
      // No idempotency key and no body, deliberately: this re-issues the session's already-OPEN
      // opportunity rather than creating a new one whenever one exists
      // (app/application/opportunity_selection.py's reissue_presentation_for_open_opportunity) —
      // that's what makes it the crash-recovery path. Calling it again after an app restart or a
      // dropped response returns the same open question instead of minting a second one.
      requestJson(config, {
        accessToken,
        method: 'POST',
        path: `/api/v1/b/sessions/${sessionId}/opportunities`,
        validate: isOpportunityPresentationResponse,
      }),
    submitResponse: (sessionId, itemOpportunityId, idempotencyKey, body, accessToken) =>
      requestJson(config, {
        accessToken,
        body: normalizeSubmitResponseBody(body),
        idempotencyKey,
        method: 'POST',
        path: `/api/v1/b/sessions/${sessionId}/opportunities/${itemOpportunityId}/responses`,
        validate: isAttemptResponse,
      }),
    requestAssist: (sessionId, itemOpportunityId, idempotencyKey, accessToken) =>
      requestJson(config, {
        accessToken,
        idempotencyKey,
        method: 'POST',
        path: `/api/v1/b/sessions/${sessionId}/opportunities/${itemOpportunityId}/assists`,
        validate: isHintRequestResponse,
      }),
    completeOpportunity: (sessionId, itemOpportunityId, idempotencyKey, accessToken) =>
      requestJson(config, {
        accessToken,
        idempotencyKey,
        method: 'POST',
        path: `/api/v1/b/sessions/${sessionId}/opportunities/${itemOpportunityId}/complete`,
        validate: isOpportunityAdvanceResponse,
      }),
    // Built but intentionally unused, not an oversight: FE-3f's results screen reads its counts off
    // the completion response it already holds, so calling this would add a round trip for numbers
    // in hand — and would import its `session_state` behaviour, where abandoned, expired and
    // technical_failed all report as "active" (session_completion.py:550), so it can never tell a
    // caller that a session ended badly.
    getSessionSummary: (sessionId, accessToken) =>
      requestJson(config, {
        accessToken,
        method: 'GET',
        path: `/api/v1/b/sessions/${sessionId}/summary`,
        validate: isSessionStandingResponse,
      }),
  };
}

export function getComponentBDevelopmentFixture() {
  return getDevelopmentFixture();
}
