// `getAuthorizedLearner` -- the three startup requests and their ORDER (FE-019, 2026-10-09).
//
// `/learner/profile` and `/learner/classrooms` used to run in series for no reason; they are now
// issued together and awaited in order. These tests exist because the obvious way to parallelise
// them -- `Promise.all` -- silently breaks the onboarding path, and nothing else in the suite would
// have caught it: a learner with no profile yet is exactly the learner whose `/learner/classrooms`
// fails (no learner link, so the server 404s), and under `Promise.all` that rejection would take
// the whole call down and send a first-run child to "unavailable" instead of to onboarding.
//
// So the first test pins the concurrency, and the rest pin the three outcomes that concurrency must
// not disturb.

import assert from 'node:assert/strict';
import test from 'node:test';

import { getAuthorizedLearner } from '@/src/api/client';
import { ApiClientError } from '@/src/api/errors';
import type { PublicConfig } from '@/src/config/env';

const config: PublicConfig = {
  apiBaseUrl: 'https://api.example.test',
  appEnvironment: 'development',
  supabasePublishableKey: 'test-key',
  supabaseUrl: 'https://supabase.example.test',
};

const principal = { user_id: 'subject-1', email: 'learner@example.test' };
// Must satisfy `isLearnerProfileResponse` in full -- a 200 that fails runtime validation is turned
// into an `invalid-response` error, which would make this test fail for the wrong reason.
const profile = {
  created_at_utc: '2026-10-09T00:00:00Z',
  email: 'learner@example.test',
  learner_id: 'learner-1',
  name: 'Test Learner',
  profile_type: 'LEARNER',
  request_id: 'req-profile',
  user_id: 'subject-1',
};
// Likewise must satisfy `isLearnerMembershipListResponse` in full. Note the field is
// `membership_id`, not `classroom_membership_id`.
const memberships = {
  memberships: [
    {
      classroom_id: 'classroom-1',
      classroom_name: 'Grade 2',
      decided_at_utc: '2026-10-09T00:00:00Z',
      grade: 'GRADE_2',
      membership_id: 'membership-1',
      requested_at_utc: '2026-10-09T00:00:00Z',
      state: 'APPROVED',
    },
  ],
  request_id: 'req-memberships',
};

const refresh = async () => null;

type Route = { status: number; body: unknown } | { reject: true };

/**
 * Records the order in which paths are REQUESTED (not resolved), so concurrency is observable.
 * `settle` is held open until the test releases it, which is what makes "both were in flight at
 * once" a real assertion rather than a timing coincidence.
 */
function stubRoutes(routes: Record<string, Route>) {
  const original = global.fetch;
  const started: string[] = [];
  const gates: Record<string, () => void> = {};

  global.fetch = (async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    const path = new URL(url).pathname;
    started.push(path);

    await new Promise<void>((resolve) => {
      gates[path] = resolve;
    });

    const route = routes[path];
    if (!route) throw new Error(`unstubbed path: ${path}`);
    if ('reject' in route) throw new TypeError('network down');
    return new Response(JSON.stringify(route.body), {
      headers: { 'x-request-id': 'req-stub' },
      status: route.status,
    });
  }) as typeof fetch;

  return {
    started,
    release: (path: string) => {
      const gate = gates[path];
      assert.ok(gate, `expected a request to ${path} to be in flight`);
      gate();
    },
    waitForStart: async (path: string) => {
      for (let i = 0; i < 50 && !started.includes(path); i += 1) {
        await new Promise((resolve) => setImmediate(resolve));
      }
      assert.ok(started.includes(path), `expected ${path} to have been requested`);
    },
    restore: () => {
      global.fetch = original;
    },
  };
}

test('profile and classrooms are in flight at the same time, after /me', async () => {
  const stub = stubRoutes({
    '/api/v1/me': { status: 200, body: principal },
    '/api/v1/learner/profile': { status: 200, body: profile },
    '/api/v1/learner/classrooms': { status: 200, body: memberships },
  });

  try {
    const pending = getAuthorizedLearner(config, 'token', refresh);

    // /me alone first: the other two must not have been issued yet, because they have to use the
    // token /me verified.
    await stub.waitForStart('/api/v1/me');
    assert.deepEqual(stub.started, ['/api/v1/me'], '/me must be issued on its own');
    stub.release('/api/v1/me');

    await stub.waitForStart('/api/v1/learner/profile');
    await stub.waitForStart('/api/v1/learner/classrooms');
    assert.deepEqual(
      stub.started.slice(1).sort(),
      ['/api/v1/learner/classrooms', '/api/v1/learner/profile'],
      'profile and classrooms must both be in flight before either has resolved',
    );

    stub.release('/api/v1/learner/profile');
    stub.release('/api/v1/learner/classrooms');

    const result = await pending;
    assert.equal(result.learnerProfile?.learner_id, 'learner-1');
    assert.equal(result.classroomMembership?.state, 'APPROVED');
    assert.equal(result.principal.user_id, 'subject-1');
  } finally {
    stub.restore();
  }
});

test('a 404 profile yields onboarding even when classrooms fails outright', async () => {
  // THE REGRESSION THIS FILE EXISTS FOR. Both of these are what a genuine first-run learner gets,
  // and the result must still be onboarding, not an error.
  const stub = stubRoutes({
    '/api/v1/me': { status: 200, body: principal },
    '/api/v1/learner/profile': {
      status: 404,
      body: { error: { code: 'RESOURCE_NOT_FOUND', message: 'nope', request_id: 'r' }, schema_version: '1.0' },
    },
    '/api/v1/learner/classrooms': { reject: true },
  });

  try {
    const pending = getAuthorizedLearner(config, 'token', refresh);
    await stub.waitForStart('/api/v1/me');
    stub.release('/api/v1/me');
    await stub.waitForStart('/api/v1/learner/profile');
    await stub.waitForStart('/api/v1/learner/classrooms');
    stub.release('/api/v1/learner/classrooms');
    stub.release('/api/v1/learner/profile');

    const result = await pending;
    assert.equal(result.learnerProfile, null, 'no profile yet');
    assert.equal(result.classroomMembership, null, 'the discarded membership must not leak through');
  } finally {
    stub.restore();
  }
});

test('a failing classrooms still propagates when the learner DOES have a profile', async () => {
  const stub = stubRoutes({
    '/api/v1/me': { status: 200, body: principal },
    '/api/v1/learner/profile': { status: 200, body: profile },
    '/api/v1/learner/classrooms': { reject: true },
  });

  try {
    const pending = getAuthorizedLearner(config, 'token', refresh);
    await stub.waitForStart('/api/v1/me');
    stub.release('/api/v1/me');
    await stub.waitForStart('/api/v1/learner/profile');
    await stub.waitForStart('/api/v1/learner/classrooms');
    stub.release('/api/v1/learner/profile');
    stub.release('/api/v1/learner/classrooms');

    await assert.rejects(pending, (error: unknown) => {
      assert.ok(error instanceof ApiClientError, 'must stay an ApiClientError');
      assert.equal(error.kind, 'unavailable', 'fails closed rather than guessing at no membership');
      return true;
    });
  } finally {
    stub.restore();
  }
});

test('a failing profile propagates and the parked classrooms rejection is swallowed', async () => {
  const unhandled: unknown[] = [];
  const onUnhandled = (reason: unknown) => unhandled.push(reason);
  process.on('unhandledRejection', onUnhandled);

  const stub = stubRoutes({
    '/api/v1/me': { status: 200, body: principal },
    '/api/v1/learner/profile': { status: 500, body: { nope: true } },
    '/api/v1/learner/classrooms': { reject: true },
  });

  try {
    const pending = getAuthorizedLearner(config, 'token', refresh);
    await stub.waitForStart('/api/v1/me');
    stub.release('/api/v1/me');
    await stub.waitForStart('/api/v1/learner/profile');
    await stub.waitForStart('/api/v1/learner/classrooms');
    stub.release('/api/v1/learner/classrooms');
    stub.release('/api/v1/learner/profile');

    await assert.rejects(pending);
    // Let any unhandled rejection surface before asserting none did.
    await new Promise((resolve) => setImmediate(resolve));
    assert.deepEqual(unhandled, [], 'the discarded membership promise must not warn');
  } finally {
    stub.restore();
    process.off('unhandledRejection', onUnhandled);
  }
});
