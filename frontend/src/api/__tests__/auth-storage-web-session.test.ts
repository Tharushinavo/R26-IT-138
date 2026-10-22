// `authStorage` -- the storage Supabase persists its auth session into. FE-018, 2026-10-10.
//
// WHAT WAS WRONG. `createClient` is configured with `persistSession: true` and
// `storage: authStorage` (src/auth/supabase.ts), and `autoRefreshToken: true`. The client was
// therefore faithfully persisting the session on every sign-in and every token refresh -- into a
// module-scoped `Map` that could not outlive the page. A reload signed the learner out.
//
// WHAT IS VERIFIED HERE: that the storage INTERFACE Supabase is handed now survives a reload, and
// degrades safely when browser storage is blocked. What is NOT verified here is a real browser
// reload driving the real Supabase client -- that needs a running web bundle and live credentials,
// and is recorded as outstanding rather than implied. The client-side configuration it depends on
// (`persistSession`, `storage`, `autoRefreshToken`) was read and confirmed, and is asserted below
// so it cannot regress silently.
//
// NOT A SECURITY BOUNDARY. `sessionStorage` is a persistence-lifetime choice. Script running in
// this origin can read it, and could equally read the live client's in-memory session -- so this is
// not an XSS mitigation and must never be described as one.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import Module from 'node:module';
import { beforeEach, test } from 'node:test';

// Same module-registry patch as pending-session-command.test.ts, for the same reason; forcing
// `Platform.OS === 'web'` is what puts these cases on the sessionStorage branch.
type NodeRequire = (id: string) => unknown;
const originalRequire: NodeRequire = (
  Module.prototype as unknown as { require: NodeRequire }
).require;
(Module.prototype as unknown as { require: NodeRequire }).require = function patchedRequire(
  this: unknown,
  id: string,
) {
  if (id === 'react-native') return { Platform: { OS: 'web' } };
  if (id === 'expo-secure-store') {
    return {
      WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'WHEN_UNLOCKED_THIS_DEVICE_ONLY',
      deleteItemAsync: async () => undefined,
      getItemAsync: async () => null,
      setItemAsync: async () => undefined,
    };
  }
  return originalRequire.call(this, id);
};

class SessionStorageShim implements Storage {
  private readonly map = new Map<string, string>();
  get length() {
    return this.map.size;
  }
  clear() {
    this.map.clear();
  }
  getItem(key: string) {
    return this.map.get(key) ?? null;
  }
  key(index: number) {
    return [...this.map.keys()][index] ?? null;
  }
  removeItem(key: string) {
    this.map.delete(key);
  }
  setItem(key: string, value: string) {
    this.map.set(key, String(value));
  }
}

Object.defineProperty(globalThis, 'sessionStorage', {
  configurable: true,
  value: new SessionStorageShim(),
  writable: true,
});

/* eslint-disable @typescript-eslint/no-require-imports */
const { authStorage }: typeof import('@/src/auth/secure-storage') = require('../../auth/secure-storage');
const webStorage: typeof import('@/src/utils/web-session-storage') = require('../../utils/web-session-storage');
/* eslint-enable @typescript-eslint/no-require-imports */

// The shape supabase-js actually stores: a JSON session envelope under its own key.
const SUPABASE_KEY = 'sb-hliyqkmmghheoxvdxjbv-auth-token';
const SESSION_VALUE = JSON.stringify({
  access_token: 'header.payload.signature',
  expires_at: 1900000000,
  refresh_token: 'refresh-token-value',
  token_type: 'bearer',
});

beforeEach(() => {
  globalThis.sessionStorage?.clear();
  webStorage.__resetWebSessionFallbackForTests();
});

test('a persisted session survives a page reload in the same tab', async () => {
  await authStorage.setItem(SUPABASE_KEY, SESSION_VALUE);

  // A reload destroys the JS heap but not sessionStorage. Clearing the in-memory fallback models
  // exactly that: whatever comes back must have come from sessionStorage.
  webStorage.__resetWebSessionFallbackForTests();

  assert.equal(await authStorage.getItem(SUPABASE_KEY), SESSION_VALUE);
});

test('a new tab does not inherit the previous tab\'s session', async () => {
  await authStorage.setItem(SUPABASE_KEY, SESSION_VALUE);

  // A new tab gets empty sessionStorage. This is the accepted trade-off of the ruling: tab
  // lifetime is what bounds at-rest exposure on a shared classroom device.
  globalThis.sessionStorage?.clear();
  webStorage.__resetWebSessionFallbackForTests();

  assert.equal(await authStorage.getItem(SUPABASE_KEY), null);
});

test('a refreshed token overwrites the stored session rather than accumulating', async () => {
  // `autoRefreshToken: true` means setItem is called repeatedly for the same key.
  await authStorage.setItem(SUPABASE_KEY, SESSION_VALUE);
  const refreshed = JSON.stringify({ ...JSON.parse(SESSION_VALUE), access_token: 'new.token.sig' });
  await authStorage.setItem(SUPABASE_KEY, refreshed);

  assert.equal(await authStorage.getItem(SUPABASE_KEY), refreshed);
  assert.equal(globalThis.sessionStorage?.length, 1, 'one key, overwritten in place');
});

test('sign-out removes the stored session', async () => {
  await authStorage.setItem(SUPABASE_KEY, SESSION_VALUE);
  await authStorage.removeItem(SUPABASE_KEY);

  assert.equal(await authStorage.getItem(SUPABASE_KEY), null);
  assert.equal(globalThis.sessionStorage?.getItem(SUPABASE_KEY), null, 'and not left at rest');
});

test('a missing key reads as null rather than throwing', async () => {
  assert.equal(await authStorage.getItem('sb-never-written-auth-token'), null);
});

test('blocked browser storage does not break sign-in, refresh or sign-out', async () => {
  const real = globalThis.sessionStorage;
  // Safari private mode / blocked site data: touching the property throws.
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    get() {
      throw new Error('site data blocked');
    },
  });

  try {
    // None of the three may reject -- a storage failure must not take authentication
    // initialisation or sign-out down with it.
    // Wrapped in async thunks: `SupportedStorage` is typed `MaybePromisify<T>`, so the values
    // themselves are not necessarily promises.
    await assert.doesNotReject(async () => authStorage.setItem(SUPABASE_KEY, SESSION_VALUE));
    await assert.doesNotReject(async () => authStorage.getItem(SUPABASE_KEY));
    // And it still works for the life of the page, which is the pre-FE-018 behaviour.
    assert.equal(await authStorage.getItem(SUPABASE_KEY), SESSION_VALUE);
    await assert.doesNotReject(async () => authStorage.removeItem(SUPABASE_KEY));
    assert.equal(await authStorage.getItem(SUPABASE_KEY), null);
  } finally {
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: real });
  }
});

test('the Supabase client still asks for persistence through this storage', () => {
  // The whole defect was a client configured to persist into something that could not persist.
  // If any of these three change, the reload behaviour above stops meaning anything.
  const source = readFileSync('src/auth/supabase.ts', 'utf8');
  assert.match(source, /persistSession: true/);
  assert.match(source, /storage: authStorage/);
  assert.match(source, /autoRefreshToken: true/);
});

test('the native branch is unchanged and web never reaches localStorage', () => {
  const code = readFileSync('src/auth/secure-storage.ts', 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
  assert.match(code, /SecureStore\.getItemAsync\(key\)/, 'native still uses SecureStore');
  assert.match(code, /keychainAccessible: SecureStore\.WHEN_UNLOCKED_THIS_DEVICE_ONLY/);
  assert.doesNotMatch(code, /localStorage/, 'web auth tokens must not be persisted to localStorage');
});
