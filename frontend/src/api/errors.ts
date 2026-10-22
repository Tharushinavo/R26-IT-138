import type { ApiErrorEnvelope } from '@/src/api/contracts';

export type ApiErrorKind =
  | 'conflict'
  | 'forbidden'
  | 'invalid-request'
  | 'invalid-response'
  | 'network'
  | 'rate-limited'
  | 'server'
  | 'timeout'
  | 'unauthenticated'
  | 'unavailable';

export class ApiClientError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    message: string,
    public readonly status?: number,
    public readonly requestId?: string,
    public readonly envelope?: ApiErrorEnvelope,
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}
