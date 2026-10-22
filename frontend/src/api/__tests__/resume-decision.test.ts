import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';

import type { ActiveSessionResponse } from '@/src/api/generated/openapi-types';

// session-preparation-screen.tsx (and its transitive dependency tree — auth-context, supabase,
// secure-storage, app-text, learner-tab-bar) pulls in React Native, Expo, and Supabase modules
// that cannot load under the plain esbuild/tsx test runner `test:contract` uses (same problem as
// FE-0b's session-command-store test: React Native's entry file uses Flow's `import typeof`,
// which esbuild rejects outright). This batch is scoped to the screen file plus exactly one new
// test file — no third file to extract the pure resume-decision logic into — so
// `resolveResumableSessionId` is exported straight from the screen module and reached here the
// same way FE-0b's store test reached its target: `Module.prototype.require` is monkeypatched to
// stub every bare specifier the screen (transitively) needs at module-load time, none of which
// `resolveResumableSessionId` itself actually touches (it only calls the `api` parameter it is
// given). This affects only this file's module registry — `node --test` isolates each test file
// into its own worker/process. No rendering, no RNTL (that's Batch 15) — this is pure logic only.
type NodeRequire = (id: string) => unknown;
const originalRequire: NodeRequire = (
  Module.prototype as unknown as { require: NodeRequire }
).require;

const reactNativeStub = {
  ActivityIndicator: () => null,
  AppState: { addEventListener: () => ({ remove() {} }) },
  Platform: { OS: 'web' },
  Pressable: () => null,
  StyleSheet: { create: (styles: unknown) => styles },
  Text: () => null,
  View: () => null,
  useWindowDimensions: () => ({ height: 800, width: 400 }),
};

const secureStoreStub = {
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WHEN_UNLOCKED_THIS_DEVICE_ONLY',
  deleteItemAsync: async () => undefined,
  getItemAsync: async () => null,
  setItemAsync: async () => undefined,
};

const stubs: Record<string, unknown> = {
  '@expo/vector-icons': { Ionicons: () => null },
  'expo-blur': { BlurView: () => null },
  'expo-crypto': { randomUUID: () => 'stub-uuid' },
  'expo-image': { Image: () => null },
  'expo-router': { router: { replace: () => {} } },
  'expo-secure-store': secureStoreStub,
  'react-native': reactNativeStub,
  'react-native-safe-area-context': { SafeAreaView: () => null },
  'react-native-url-polyfill/auto': {},
};

const imageExtensionPattern = /\.(png|jpe?g|gif|webp)$/i;

(Module.prototype as unknown as { require: NodeRequire }).require = function patchedRequire(
  this: unknown,
  id: string,
) {
  if (id in stubs) return stubs[id];
  // Metro resolves `require('./foo.png')` to an asset module id; plain Node has no such loader,
  // and the screen (and learner-tab-bar, which it renders) requires several image assets directly.
  // Their actual contents are irrelevant here — this test never renders anything.
  if (imageExtensionPattern.test(id)) return 0;
  return originalRequire.call(this, id);
};

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { resolveResumableSessionId } = require('../../features/session/session-preparation-screen') as {
  resolveResumableSessionId: (
    api: { getActiveSession: (accessToken: string) => Promise<ActiveSessionResponse> },
    accessToken: string,
  ) => Promise<string | null>;
};

function fakeApi(getActiveSession: (accessToken: string) => Promise<ActiveSessionResponse>) {
  return { getActiveSession };
}

test('resolveResumableSessionId returns the session id when an active session exists (Resume)', async () => {
  const api = fakeApi(async () => ({
    request_id: 'req-1',
    session: {
      created_at_utc: '2026-07-29T00:00:00Z',
      row_version: 0,
      runtime_bundle_version: 'be3b-test-fixture-1.0',
      session_id: 'session-abc-123',
      state: 'active',
    },
  }));
  assert.equal(await resolveResumableSessionId(api, 'token'), 'session-abc-123');
});

test('resolveResumableSessionId returns null when there is no active session (Start)', async () => {
  const api = fakeApi(async () => ({ request_id: 'req-1', session: null }));
  assert.equal(await resolveResumableSessionId(api, 'token'), null);
});

test('resolveResumableSessionId returns null for a non-active session state (Start)', async () => {
  for (const state of ['completed', 'abandoned'] as const) {
    const api = fakeApi(async () => ({
      request_id: 'req-1',
      session: {
        created_at_utc: '2026-07-29T00:00:00Z',
        row_version: 0,
        runtime_bundle_version: 'be3b-test-fixture-1.0',
        session_id: 'session-abc-123',
        state,
      },
    }));
    assert.equal(await resolveResumableSessionId(api, 'token'), null, `state=${state} should resolve to Start`);
  }
});

test('resolveResumableSessionId returns null when the call throws (Start, degrades silently)', async () => {
  const api = fakeApi(async () => {
    throw new Error('network down');
  });
  assert.equal(await resolveResumableSessionId(api, 'token'), null);
});
