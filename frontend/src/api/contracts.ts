import type {
  AuthenticatedPrincipal,
  InviteResolveResponse,
  InviteTokenRequest,
  LearnerMembershipListItem,
  LearnerMembershipListResponse,
  LearnerProfileResponse,
  MembershipRequestResponse,
  ProfileCreateRequest,
  ReadinessResponse,
  SessionCommandResponse,
} from '@/src/api/generated/openapi-types';

export type {
  AuthenticatedPrincipal,
  InviteResolveResponse,
  InviteTokenRequest,
  LearnerMembershipListItem,
  LearnerMembershipListResponse,
  LearnerProfileResponse,
  MembershipRequestResponse,
  ProfileCreateRequest,
  SessionCommandResponse,
};

// GET /api/v1/me returns only the bare principal. Role/profile resolution is a separate call
// (GET /api/v1/learner/profile); this app is child-facing only, so a null learnerProfile means
// "no learner profile yet" (onboarding), never a teacher/operator role check. classroomMembership
// is the most relevant membership (see pickMembership) from GET /api/v1/learner/classrooms; null
// means no membership has been requested yet. 'authorized' status requires both a profile and an
// APPROVED membership — see auth-context.tsx's authorizeSession.
export type AuthorizedLearner = {
  principal: AuthenticatedPrincipal;
  learnerProfile: LearnerProfileResponse | null;
  classroomMembership: LearnerMembershipListItem | null;
};

// Mirrors app/core/errors.py ErrorResponse/ErrorBody exactly, verified against the live
// handlers. `details` is `dict | list[dict] | None` server-side and is emitted with
// exclude_none=True, so it is ABSENT (never null) when unset. Its inner shape is
// per-handler and deliberately not narrowed here: the 422 handler emits
// [{location: string[], type: string}], other handlers pass through arbitrary dicts.
// Still absent from the frozen OpenAPI (FastAPI does not register custom exception-handler
// responses), so this is hand-written against observed behaviour — see Risk 3.
export type ApiErrorEnvelope = {
  schema_version: string;
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown> | Record<string, unknown>[];
  };
};

// Matches the live `/health/ready` contract exactly (generated from the frozen OpenAPI).
export type HealthReadyResponse = ReadinessResponse;

// Local offline-recovery persistence for in-flight B-session write commands, not a server DTO.
// Every variant carries its own `idempotencyKey`/`createdAt`; the backend fingerprints the
// request body into the idempotency record (see body_fingerprint at
// app/application/b_session_lifecycle.py:175 and app/application/attempt_submission.py:194), so a
// replay must resend the exact body it saved, never one reconstructed at replay time. This is why
// submit_response's `body` is required, not optional, and why `client_elapsed_ms` (unrecoverable
// after a relaunch) is persisted rather than recomputed.
export type PendingStartSessionCommandBase = {
  kind: 'start_session';
  endpoint: '/api/v1/b/sessions';
  idempotencyKey: string;
  createdAt: string;
};

export type PendingSubmitResponseCommand = {
  kind: 'submit_response';
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses';
  sessionId: string;
  itemOpportunityId: string;
  body: { submitted_value: string; client_elapsed_ms: number };
  idempotencyKey: string;
  createdAt: string;
};

export type PendingRequestAssistCommand = {
  kind: 'request_assist';
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/assists';
  sessionId: string;
  itemOpportunityId: string;
  idempotencyKey: string;
  createdAt: string;
};

export type PendingCompleteOpportunityCommand = {
  kind: 'complete_opportunity';
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/complete';
  sessionId: string;
  itemOpportunityId: string;
  idempotencyKey: string;
  createdAt: string;
};

export type PendingSessionCommand =
  | PendingStartSessionCommandBase
  | PendingSubmitResponseCommand
  | PendingRequestAssistCommand
  | PendingCompleteOpportunityCommand;

// Kept as an alias of the start_session member so existing start-session call sites
// (session-preparation-screen.tsx) keep compiling untouched.
export type PendingStartSessionCommand = PendingStartSessionCommandBase;
