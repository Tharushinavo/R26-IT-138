import type { AuthenticatedPrincipal, AuthorizedLearner } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import { listLearnerClassrooms } from '@/src/api/learner-onboarding-api';
import { pickMembership } from '@/src/api/membership-selection';
import { requestJson, type RefreshAccessToken } from '@/src/api/request';
import {
  isAuthenticatedPrincipal,
  isLearnerProfileResponse,
} from '@/src/api/runtime-validation';
import type { PublicConfig } from '@/src/config/env';

const SAFE_GET_RETRY_DELAY_MS = 300;

async function wait(milliseconds: number) {
  await new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function requestMeOnce(config: PublicConfig, accessToken: string) {
  return requestJson(config, {
    accessToken,
    method: 'GET',
    path: '/api/v1/me',
    validate: isAuthenticatedPrincipal,
  });
}

async function requestLearnerProfileOnce(config: PublicConfig, accessToken: string) {
  return requestJson(config, {
    accessToken,
    method: 'GET',
    path: '/api/v1/learner/profile',
    validate: isLearnerProfileResponse,
  });
}

async function fetchPrincipal(
  config: PublicConfig,
  accessToken: string,
  refreshAccessToken: RefreshAccessToken,
): Promise<{ principal: AuthenticatedPrincipal; accessToken: string }> {
  try {
    return { accessToken, principal: await requestMeOnce(config, accessToken) };
  } catch (error) {
    if (!(error instanceof ApiClientError)) throw error;
    if (error.kind === 'unauthenticated') {
      const refreshedAccessToken = await refreshAccessToken();
      if (!refreshedAccessToken) throw error;
      return { accessToken: refreshedAccessToken, principal: await requestMeOnce(config, refreshedAccessToken) };
    }
    if (error.kind === 'network' || error.kind === 'timeout' || (error.kind === 'server' && (error.status ?? 0) >= 500)) {
      await wait(SAFE_GET_RETRY_DELAY_MS);
      return { accessToken, principal: await requestMeOnce(config, accessToken) };
    }
    throw error;
  }
}

async function getLearnerProfileOrNull(config: PublicConfig, accessToken: string) {
  try {
    return await requestLearnerProfileOnce(config, accessToken);
  } catch (error) {
    if (!(error instanceof ApiClientError)) throw error;
    // A clean 404 means "no learner profile yet" -> onboarding. Anything else (network,
    // 5xx, unexpected 4xx) fails closed as unavailable rather than guessing at onboarding.
    if (error.status === 404) return null;
    if (error.kind === 'unauthenticated' || error.kind === 'forbidden') throw error;
    throw new ApiClientError(
      'unavailable',
      'We could not verify the learner profile.',
      error.status,
      error.requestId,
      error.envelope,
    );
  }
}

async function getClassroomMembershipOrNull(config: PublicConfig, accessToken: string) {
  try {
    const response = await listLearnerClassrooms(config, accessToken);
    // An empty list is a legitimate "no membership requested yet" state, not an error.
    return pickMembership(response.memberships);
  } catch (error) {
    if (!(error instanceof ApiClientError)) throw error;
    if (error.kind === 'unauthenticated' || error.kind === 'forbidden') throw error;
    throw new ApiClientError(
      'unavailable',
      'We could not verify the classroom membership.',
      error.status,
      error.requestId,
      error.envelope,
    );
  }
}

// Re-exported so existing importers keep working; the transport itself now lives in
// request.ts, which imports nothing from this file. See that file for the cycle this broke.
export { requestJson, type RefreshAccessToken };

export async function getAuthorizedLearner(
  config: PublicConfig,
  accessToken: string,
  refreshAccessToken: RefreshAccessToken,
): Promise<AuthorizedLearner> {
  const { accessToken: verifiedAccessToken, principal } = await fetchPrincipal(
    config,
    accessToken,
    refreshAccessToken,
  );

  // The profile and the membership are issued TOGETHER and awaited in order (FE-019, 2026-10-09).
  // They were sequential, and nothing required that: neither request is an input to the other, and
  // each took ~0.5s against the hosted database, so startup spent a second of a child's attention
  // on two round trips that could have overlapped. `/me` still goes first and alone, because it
  // owns the token-refresh retry and these two must use the token it verified.
  //
  // AWAITED IN ORDER, NOT `Promise.all`. The three outcomes below have to stay exactly what they
  // were, and `Promise.all` would break the middle one:
  //
  //   - profile REJECTS      -> propagate, as before. The membership rejection (if any) is parked
  //                             by the no-op catch below so discarding it cannot surface as an
  //                             unhandled rejection.
  //   - profile is NULL      -> onboarding, and the membership result is DISCARDED unread. This is
  //                             the case `Promise.all` would get wrong: a learner with no profile
  //                             yet is the exact learner whose `/learner/classrooms` fails (no
  //                             learner link, so the server 404s, which
  //                             `getClassroomMembershipOrNull` turns into a thrown `unavailable`).
  //                             Under `Promise.all` that rejection would take the whole call down
  //                             and send a first-run child to the "unavailable" screen instead of
  //                             to onboarding.
  //   - profile RESOLVES     -> await the membership and let its failure propagate, as before.
  //
  // The cost is one discarded GET for a learner who has no profile yet -- a first-run-only path.
  const learnerProfilePromise = getLearnerProfileOrNull(config, verifiedAccessToken);
  const classroomMembershipPromise = getClassroomMembershipOrNull(config, verifiedAccessToken);
  classroomMembershipPromise.catch(() => undefined);

  const learnerProfile = await learnerProfilePromise;
  if (!learnerProfile) return { classroomMembership: null, learnerProfile: null, principal };

  const classroomMembership = await classroomMembershipPromise;
  return { classroomMembership, learnerProfile, principal };
}
