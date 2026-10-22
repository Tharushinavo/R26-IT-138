import { test } from 'node:test';
import assert from 'node:assert/strict';

import { isApiErrorEnvelope } from '@/src/api/runtime-validation';
import { requestJson } from '@/src/api/client';
import { ApiClientError } from '@/src/api/errors';
import type { PublicConfig } from '@/src/config/env';

const config: PublicConfig = {
  apiBaseUrl: 'https://api.example.test',
  appEnvironment: 'development',
  supabasePublishableKey: 'test-key',
  supabaseUrl: 'https://supabase.example.test',
};

function stubFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  const original = global.fetch;
  global.fetch = (async () =>
    new Response(JSON.stringify(body), {
      headers,
      status,
    })) as typeof fetch;
  return () => {
    global.fetch = original;
  };
}

test('isApiErrorEnvelope accepts a real captured 409 envelope', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: { code: 'CONFLICT', message: 'The request conflicts with the current resource state.', request_id: 'req-409' },
      schema_version: '1.0',
    }),
    true,
  );
});

test('isApiErrorEnvelope accepts a real captured 422 with array details', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: {
        code: 'REQUEST_VALIDATION_FAILED',
        details: [{ location: ['body', 'name'], type: 'missing' }],
        message: 'The request is invalid.',
        request_id: 'req-422',
      },
      schema_version: '1.0',
    }),
    true,
  );
});

test('isApiErrorEnvelope accepts object-form details', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: {
        code: 'APPLICATION_ERROR',
        details: { reason: 'stale_row_version' },
        message: 'The request could not be completed.',
        request_id: 'req-1',
      },
      schema_version: '1.0',
    }),
    true,
  );
});

test('isApiErrorEnvelope rejects the old flat shape', () => {
  assert.equal(
    isApiErrorEnvelope({
      code: 'CONFLICT',
      message: 'The session state changed.',
      request_id: 'req-1',
      retryable: false,
    }),
    false,
  );
});

test('isApiErrorEnvelope rejects an empty error object', () => {
  assert.equal(isApiErrorEnvelope({ error: {}, schema_version: '1.0' }), false);
});

test('isApiErrorEnvelope rejects a missing schema_version', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: { code: 'CONFLICT', message: 'x', request_id: 'req-1' },
    }),
    false,
  );
});

test('isApiErrorEnvelope rejects a non-object, non-array details value', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: { code: 'CONFLICT', details: 'nope', message: 'x', request_id: 'req-1' },
      schema_version: '1.0',
    }),
    false,
  );
});

test('isApiErrorEnvelope rejects a details array with non-record elements', () => {
  assert.equal(
    isApiErrorEnvelope({
      error: { code: 'CONFLICT', details: [1, 2], message: 'x', request_id: 'req-1' },
      schema_version: '1.0',
    }),
    false,
  );
});

test('isApiErrorEnvelope rejects a null error field', () => {
  assert.equal(isApiErrorEnvelope({ error: null, schema_version: '1.0' }), false);
});

test('requestJson takes the surfaced request id from the envelope body, not the header', async () => {
  const restore = stubFetch(
    409,
    {
      error: {
        code: 'CONFLICT',
        message: 'The request conflicts with the current resource state.',
        request_id: 'req-from-body',
      },
      schema_version: '1.0',
    },
    { 'x-request-id': 'req-from-header' },
  );
  try {
    await assert.rejects(
      requestJson(config, {
        method: 'GET',
        path: '/api/v1/b/sessions',
        validate: (value: unknown): value is unknown => true,
      }),
      (error: unknown) => {
        assert.ok(error instanceof ApiClientError);
        assert.equal(error.requestId, 'req-from-body');
        assert.equal(error.kind, 'conflict');
        assert.equal(error.envelope?.error.request_id, 'req-from-body');
        return true;
      },
    );
  } finally {
    restore();
  }
});
