// The HTTP transport: one function that every API module sends through.
//
// It lived in client.ts until 2026-09-28. client.ts also exports `getAuthorizedLearner`, which
// needs `listLearnerClassrooms` from learner-onboarding-api.ts -- and that module needs the
// transport, so the two imported each other. Metro is right about what is wrong with a require
// cycle: "can result in uninitialized values". Splitting the transport out breaks it without
// either module giving anything up, because the transport never needed the orchestration.

import type { ApiErrorEnvelope } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import { isApiErrorEnvelope } from '@/src/api/runtime-validation';
import type { PublicConfig } from '@/src/config/env';
import { acceptLanguageHeader } from '@/src/config/locale';

const REQUEST_TIMEOUT_MS = 10_000;

export type RefreshAccessToken = () => Promise<string | null>;

type ApiRequestOptions<T> = {
  accessToken?: string;
  body?: unknown;
  idempotencyKey?: string;
  method: 'GET' | 'POST';
  path: string;
  validate: (value: unknown) => value is T;
};

function mapHttpError(status: number, envelope?: ApiErrorEnvelope) {
  const requestId = envelope?.error.request_id;
  if (status === 401) return new ApiClientError('unauthenticated', 'The session is no longer valid.', status, requestId, envelope);
  if (status === 403) return new ApiClientError('forbidden', 'This account is not approved for learner access.', status, requestId, envelope);
  if (status === 400 || status === 422) return new ApiClientError('invalid-request', 'The request could not be accepted.', status, requestId, envelope);
  if (status === 409 || status === 412) return new ApiClientError('conflict', 'The session state changed.', status, requestId, envelope);
  if (status === 429) return new ApiClientError('rate-limited', 'Please wait before trying again.', status, requestId, envelope);
  if (status === 503) return new ApiClientError('unavailable', 'Learning is temporarily unavailable.', status, requestId, envelope);
  return new ApiClientError('server', 'The server could not complete the request.', status, requestId, envelope);
}

export async function requestJson<T>(
  config: PublicConfig,
  options: ApiRequestOptions<T>,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;

  try {
    response = await fetch(`${config.apiBaseUrl}${options.path}`, {
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      headers: {
        Accept: 'application/json',
        // The language the learner reads questions in. Sent on every request rather than only the
        // one that serves a question, because it costs nothing and any future localised response
        // gets it for free. CORS-safelisted, so it needs no server allow-list entry, unlike
        // X-Mobile-App-Version below. See config/locale.ts -- English unless deliberately changed.
        'Accept-Language': acceptLanguageHeader(),
        ...(options.accessToken ? { Authorization: `Bearer ${options.accessToken}` } : {}),
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {}),
        'X-Mobile-App-Version': '1.0.0',
      },
      method: options.method,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiClientError('timeout', 'The server took too long to respond.');
    }
    throw new ApiClientError('network', 'The server could not be reached.');
  } finally {
    clearTimeout(timeout);
  }

  const headerRequestId = response.headers.get('x-request-id') ?? undefined;
  let body: unknown;
  try {
    body = JSON.parse(await response.text()) as unknown;
  } catch {
    throw new ApiClientError('invalid-response', 'The server returned an unsupported response.', response.status, headerRequestId);
  }

  if (!response.ok) {
    const envelope = isApiErrorEnvelope(body) ? body : undefined;
    const error = mapHttpError(response.status, envelope);
    if (!error.requestId && headerRequestId) {
      throw new ApiClientError(error.kind, error.message, error.status, headerRequestId, error.envelope);
    }
    throw error;
  }

  if (!options.validate(body)) {
    throw new ApiClientError('invalid-response', 'The server returned an unsupported response.', response.status, headerRequestId);
  }
  return body;
}

