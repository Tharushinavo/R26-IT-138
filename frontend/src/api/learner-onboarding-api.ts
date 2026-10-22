import type {
  InviteResolveResponse,
  InviteTokenRequest,
  LearnerMembershipListResponse,
  LearnerProfileResponse,
  MembershipRequestResponse,
  ProfileCreateRequest,
} from '@/src/api/contracts';
import { requestJson } from '@/src/api/request';
import {
  isInviteResolveResponse,
  isLearnerMembershipListResponse,
  isLearnerProfileResponse,
  isMembershipRequestResponse,
} from '@/src/api/runtime-validation';
import type { PublicConfig } from '@/src/config/env';

export function createLearnerProfile(
  config: PublicConfig,
  accessToken: string,
  idempotencyKey: string,
  body: ProfileCreateRequest,
): Promise<LearnerProfileResponse> {
  return requestJson(config, {
    accessToken,
    body,
    idempotencyKey,
    method: 'POST',
    path: '/api/v1/learner/profile',
    validate: isLearnerProfileResponse,
  });
}

export function resolveClassroomInvite(
  config: PublicConfig,
  accessToken: string,
  idempotencyKey: string,
  body: InviteTokenRequest,
): Promise<InviteResolveResponse> {
  return requestJson(config, {
    accessToken,
    body,
    idempotencyKey,
    method: 'POST',
    path: '/api/v1/classroom-invites/resolve',
    validate: isInviteResolveResponse,
  });
}

export function requestClassroomMembership(
  config: PublicConfig,
  accessToken: string,
  idempotencyKey: string,
  body: InviteTokenRequest,
): Promise<MembershipRequestResponse> {
  return requestJson(config, {
    accessToken,
    body,
    idempotencyKey,
    method: 'POST',
    path: '/api/v1/classroom-memberships/requests',
    validate: isMembershipRequestResponse,
  });
}

export function listLearnerClassrooms(
  config: PublicConfig,
  accessToken: string,
): Promise<LearnerMembershipListResponse> {
  return requestJson(config, {
    accessToken,
    method: 'GET',
    path: '/api/v1/learner/classrooms',
    validate: isLearnerMembershipListResponse,
  });
}
