import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  isActiveSessionResponse,
  isAttemptResponse,
  isHintRequestResponse,
  isOpportunityAdvanceResponse,
  isOpportunityPresentationResponse,
  isSessionStandingResponse,
} from '@/src/api/runtime-validation';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const openapiPath = resolve(repoRoot, 'backend', 'contract', 'openapi.v1.json');
const openapi = JSON.parse(readFileSync(openapiPath, 'utf-8'));
const schemas = openapi.components.schemas;

function requiredFieldsOf(schemaName: string): string[] {
  return schemas[schemaName].required;
}

function assertRequiredFieldsPresent(sample: Record<string, unknown>, schemaName: string) {
  for (const field of requiredFieldsOf(schemaName)) {
    assert.ok(field in sample, `sample for ${schemaName} is missing required field ${field}`);
  }
}

function assertRejectsEachDroppedRequiredField(
  sample: Record<string, unknown>,
  schemaName: string,
  validate: (value: unknown) => boolean,
) {
  for (const field of requiredFieldsOf(schemaName)) {
    const mutated = { ...sample };
    delete mutated[field];
    assert.equal(
      validate(mutated),
      false,
      `dropping required field ${field} from ${schemaName} should fail closed`,
    );
  }
}

// --- isActiveSessionResponse -------------------------------------------------------------

const validSessionFields = {
  created_at_utc: '2026-07-29T00:00:00Z',
  row_version: 1,
  runtime_bundle_version: 'be3b-test-fixture-1.0',
  session_id: 'session-1',
  state: 'active',
};

test('isActiveSessionResponse accepts the live shape (session present) and fails closed on drift', () => {
  const validSample = { request_id: 'req-1', session: validSessionFields };
  assertRequiredFieldsPresent(validSample, 'ActiveSessionResponse');
  assert.equal(isActiveSessionResponse(validSample), true);
  assertRejectsEachDroppedRequiredField(validSample, 'ActiveSessionResponse', isActiveSessionResponse);
});

test('isActiveSessionResponse accepts a null session (no active session)', () => {
  assert.equal(isActiveSessionResponse({ request_id: 'req-1', session: null }), true);
});

test('isActiveSessionResponse rejects a malformed nested session', () => {
  const { state: _state, ...sessionWithoutState } = validSessionFields;
  assert.equal(
    isActiveSessionResponse({ request_id: 'req-1', session: sessionWithoutState }),
    false,
  );
});

// --- isOpportunityPresentationResponse ---------------------------------------------------

const validOpportunityPresentation = {
  difficulty_level: 'easy',
  grade: 2,
  item_instance_id: 'instance-1',
  item_opportunity_id: 'opportunity-1',
  presentation_token: 'token-1',
  presented_choices: ['2', '3', '4'],
  prompt: { stem: 'What is 2 + 2?' },
  representation_type: 'text',
  request_id: 'req-1',
  response_format: 'multiple_choice',
  server_timeout_deadline_utc: '2026-07-29T00:05:00Z',
  skill_id: 'counting',
};

test('isOpportunityPresentationResponse accepts the live shape and fails closed on drift', () => {
  assertRequiredFieldsPresent(validOpportunityPresentation, 'OpportunityPresentationResponse');
  assert.equal(isOpportunityPresentationResponse(validOpportunityPresentation), true);
  assertRejectsEachDroppedRequiredField(
    validOpportunityPresentation,
    'OpportunityPresentationResponse',
    isOpportunityPresentationResponse,
  );
});

test('isOpportunityPresentationResponse accepts an empty presented_choices array (free-entry formats have none)', () => {
  assert.equal(
    isOpportunityPresentationResponse({ ...validOpportunityPresentation, presented_choices: [] }),
    true,
  );
});

test('isOpportunityPresentationResponse accepts an unknown response_format string (format rejection lives in the registry, not here)', () => {
  assert.equal(
    isOpportunityPresentationResponse({
      ...validOpportunityPresentation,
      response_format: 'some_future_format_not_yet_known',
    }),
    true,
  );
});

test('isOpportunityPresentationResponse rejects a prompt with an empty stem', () => {
  assert.equal(
    isOpportunityPresentationResponse({
      ...validOpportunityPresentation,
      prompt: { stem: '' },
    }),
    false,
  );
});

test('isOpportunityPresentationResponse rejects a server_timeout_deadline_utc that does not parse as a date', () => {
  assert.equal(
    isOpportunityPresentationResponse({
      ...validOpportunityPresentation,
      server_timeout_deadline_utc: 'not-a-date',
    }),
    false,
  );
});

// --- isAttemptResponse ---------------------------------------------------------------------

const validAttemptResponseWithMatch = {
  attempt_index: 0,
  event_kind: 'RESPONSE',
  item_opportunity_id: 'opportunity-1',
  request_id: 'req-1',
  response_matched: true,
  server_submitted_at_utc: '2026-07-29T00:00:00Z',
};

test('isAttemptResponse accepts the live RESPONSE shape and fails closed on drift', () => {
  assertRequiredFieldsPresent(validAttemptResponseWithMatch, 'AttemptResponse');
  assert.equal(isAttemptResponse(validAttemptResponseWithMatch), true);
  assertRejectsEachDroppedRequiredField(
    validAttemptResponseWithMatch,
    'AttemptResponse',
    isAttemptResponse,
  );
});

test('isAttemptResponse accepts a TIMEOUT with a null response_matched', () => {
  assert.equal(
    isAttemptResponse({
      ...validAttemptResponseWithMatch,
      event_kind: 'TIMEOUT',
      response_matched: null,
    }),
    true,
  );
});

test('isAttemptResponse rejects a TIMEOUT carrying a boolean response_matched', () => {
  assert.equal(
    isAttemptResponse({
      ...validAttemptResponseWithMatch,
      event_kind: 'TIMEOUT',
      response_matched: false,
    }),
    false,
  );
});

test('isAttemptResponse rejects a RESPONSE carrying a null response_matched', () => {
  assert.equal(
    isAttemptResponse({
      ...validAttemptResponseWithMatch,
      event_kind: 'RESPONSE',
      response_matched: null,
    }),
    false,
  );
});

// --- isHintRequestResponse -------------------------------------------------------------------

const validHintRequestResponse = {
  catalogue_checksum: 'sha256:abc123',
  catalogue_version: 'catalogue-1.0',
  content: 'Try counting on your fingers!',
  content_id: 'hint-content-1',
  hint_level: 1,
  item_opportunity_id: 'opportunity-1',
  request_id: 'req-1',
};

test('isHintRequestResponse accepts the live shape and fails closed on drift', () => {
  assertRequiredFieldsPresent(validHintRequestResponse, 'HintRequestResponse');
  assert.equal(isHintRequestResponse(validHintRequestResponse), true);
  assertRejectsEachDroppedRequiredField(
    validHintRequestResponse,
    'HintRequestResponse',
    isHintRequestResponse,
  );
});

// --- isOpportunityAdvanceResponse -------------------------------------------------------------

const validOpportunityAdvanceResponse = {
  item_opportunity_id: 'opportunity-1',
  next_opportunity: null,
  opportunities_completed: 3,
  opportunities_total_bound: 10,
  request_id: 'req-1',
  session_state: 'active',
};

test('isOpportunityAdvanceResponse accepts the live shape (next_opportunity null) and fails closed on drift', () => {
  assertRequiredFieldsPresent(validOpportunityAdvanceResponse, 'OpportunityAdvanceResponse');
  assert.equal(isOpportunityAdvanceResponse(validOpportunityAdvanceResponse), true);
  assertRejectsEachDroppedRequiredField(
    validOpportunityAdvanceResponse,
    'OpportunityAdvanceResponse',
    isOpportunityAdvanceResponse,
  );
});

test('isOpportunityAdvanceResponse accepts a non-null next_opportunity that recurses into the presentation fields check', () => {
  const { request_id: _requestId, ...opportunityPresentationFields } = validOpportunityPresentation;
  assert.equal(
    isOpportunityAdvanceResponse({
      ...validOpportunityAdvanceResponse,
      next_opportunity: opportunityPresentationFields,
    }),
    true,
  );
});

test('isOpportunityAdvanceResponse rejects a malformed non-null next_opportunity', () => {
  const { request_id: _requestId, skill_id: _skillId, ...malformed } = validOpportunityPresentation;
  assert.equal(
    isOpportunityAdvanceResponse({
      ...validOpportunityAdvanceResponse,
      next_opportunity: malformed,
    }),
    false,
  );
});

// --- isSessionStandingResponse -----------------------------------------------------------------

const validSessionStandingResponse = {
  opportunities_completed: 3,
  opportunities_total_bound: 10,
  request_id: 'req-1',
  session_id: 'session-1',
  session_state: 'active',
};

test('isSessionStandingResponse accepts the live shape and fails closed on drift', () => {
  assertRequiredFieldsPresent(validSessionStandingResponse, 'SessionStandingResponse');
  assert.equal(isSessionStandingResponse(validSessionStandingResponse), true);
  assertRejectsEachDroppedRequiredField(
    validSessionStandingResponse,
    'SessionStandingResponse',
    isSessionStandingResponse,
  );
});
