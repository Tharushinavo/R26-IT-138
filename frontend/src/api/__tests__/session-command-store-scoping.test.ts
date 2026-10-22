// Subject-scoped storage keys, sign-out cleanup, legacy-key handling, and web tab-lifetime
// persistence. FE-018 + B3, owner ruling 2026-10-09.
//
// WHAT WAS WRONG. Two independent defects, one per platform:
//
//   Keys were GLOBAL -- `component_b.pending_start_session` for every learner on the device. On a
//   shared classroom device learner A's interrupted-answer record was readable while learner B was
//   signed in, and nothing cleared it on sign-out. It never caused a wrong SUBMISSION, because
//   `decidePendingReplay` compares `sessionId`/`itemOpportunityId` and discards a mismatch, but the
//   record should not have been reachable. Android was the worse case: SecureStore is durable and
//   device-wide.
//
//   WEB did not persist at all -- a module-scoped `Map`, so a page reload lost the very record whose
//   purpose is surviving an interruption.
//
// WHAT IS NOT CLAIMED HERE. Key scoping is a second line of defence, not a replacement for the
// server. Non-duplication is guaranteed by the backend's idempotency record (fingerprint + key,
// with `attempt_index == 1` gating the BKT observation), never by browser storage. And
// `sessionStorage` is a persistence-LIFETIME choice, not an XSS mitigation: script in this origin
// can read it, and could equally read the live Supabase client's in-memory session.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import Module from 'node:module';
import { beforeEach, test } from 'node:test';

import type { PendingSessionCommand } from '@/src/api/contracts';

// Same module-registry patch, and for the same reason, as pending-session-command.test.ts -- see
// that file's header for the full account of why a loader hook does not work here. Forcing
// `Platform.OS === 'web'` is the point: these cases exercise the sessionStorage-backed branch.
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

/**
 * Node has no Web Storage by default, so the browser API the implementation targets is supplied
 * here. Deliberately a real implementation rather than a spy: the behaviours under test are
 * "survives a reload", "a new tab starts empty" and "a throwing store degrades", all of which need
 * storage that actually stores.
 */
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
const store: typeof import('@/src/features/session/session-command-store') = require('../../features/session/session-command-store');
const webStorage: typeof import('@/src/utils/web-session-storage') = require('../../utils/web-session-storage');
/* eslint-enable @typescript-eslint/no-require-imports */

const LEARNER_A = 'aaaaaaaa-1111-2222-3333-444444444444';
const LEARNER_B = 'bbbbbbbb-5555-6666-7777-888888888888';

function submitCommand(sessionId: string, itemOpportunityId: string): PendingSessionCommand {
  return {
    body: { client_elapsed_ms: 1200, submitted_value: '7' },
    createdAt: '2026-10-09T00:00:00.000Z',
    endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
    idempotencyKey: 'key-for-one-answer',
    itemOpportunityId,
    kind: 'submit_response',
    sessionId,
  };
}

beforeEach(() => {
  // A fresh tab for every case: clear both the real sessionStorage shim and the in-memory fallback.
  globalThis.sessionStorage?.clear();
  webStorage.__resetWebSessionFallbackForTests();
  store.__resetLegacyPurgeForTests();
});

// --- scoping ---------------------------------------------------------------------------------

test('two different subjects produce distinct keys', () => {
  const a = store.__scopedKeysForTests(LEARNER_A);
  const b = store.__scopedKeysForTests(LEARNER_B);

  assert.notEqual(a.pendingCommand, b.pendingCommand);
  assert.notEqual(a.activeSession, b.activeSession);
  assert.ok(a.pendingCommand?.includes(LEARNER_A));
  assert.ok(b.pendingCommand?.includes(LEARNER_B));
  // SecureStore accepts only alphanumerics, '.', '-' and '_' and THROWS otherwise, so the built
  // key must stay inside that set on every platform.
  assert.match(a.pendingCommand ?? '', /^[A-Za-z0-9._-]+$/);
});

test('an identity that would be unsafe as a storage key is refused, not thrown on', () => {
  // Guards a future identity format that is not a UUID. Refusing to build a key is safe; throwing
  // from inside SecureStore during sign-out would not be.
  assert.equal(store.__scopedKeysForTests('has spaces/and:slashes').pendingCommand, null);
});

test("learner B cannot load learner A's pending command", async () => {
  await store.savePendingCommand(LEARNER_A, submitCommand('session-A', 'opportunity-A'));

  assert.equal(await store.loadPendingCommand(LEARNER_B), null, "B must not see A's record");
  const forA = await store.loadPendingCommand(LEARNER_A);
  assert.ok(forA && forA.kind === 'submit_response');
  assert.equal(forA.sessionId, 'session-A', "A's own record is still there");
});

test('a null subject never writes an unscoped record, and reads as empty', async () => {
  // The only path that reaches the store without a subject is the development preview, which does
  // not implement the session loop. Writing an unscoped record there is the defect being removed.
  await store.savePendingCommand(null, submitCommand('session-X', 'opportunity-X'));
  assert.equal(await store.loadPendingCommand(null), null);
  assert.deepEqual(store.__webKeysForTests(), [], 'nothing may be persisted without a subject');
});

// --- web tab-lifetime persistence -------------------------------------------------------------

test('a pending command survives a page reload (same tab)', async () => {
  const command = submitCommand('session-reload', 'opportunity-reload');
  await store.savePendingCommand(LEARNER_A, command);

  // A reload destroys the JS heap but not sessionStorage. Dropping the in-memory fallback models
  // exactly that: anything that survives must have come from sessionStorage.
  webStorage.__resetWebSessionFallbackForTests();

  const restored = await store.loadPendingCommand(LEARNER_A);
  assert.deepEqual(restored, command, 'the record must survive a reload');
  assert.equal(
    restored?.idempotencyKey,
    command.idempotencyKey,
    'the SAME idempotency key must come back -- a refresh must not mint a new submission',
  );
});

test('a new tab does not inherit the previous tab\'s sessionStorage', async () => {
  await store.savePendingCommand(LEARNER_A, submitCommand('session-tab1', 'opportunity-tab1'));

  // A new tab starts with empty sessionStorage. That is the accepted trade-off of the ruling, not
  // a defect: tab-lifetime is what bounds at-rest exposure on a shared device.
  globalThis.sessionStorage?.clear();
  webStorage.__resetWebSessionFallbackForTests();

  assert.equal(await store.loadPendingCommand(LEARNER_A), null);
});

test('the command body survives a reload byte-identical (fingerprint-critical)', async () => {
  // The server fingerprints the BODY against the idempotency key, so a replay must resend exactly
  // what was stored -- a reconstructed body would fail the fingerprint check.
  const command = submitCommand('session-fp', 'opportunity-fp');
  await store.savePendingCommand(LEARNER_A, command);
  webStorage.__resetWebSessionFallbackForTests();

  const restored = await store.loadPendingCommand(LEARNER_A);
  assert.ok(restored && restored.kind === 'submit_response');
  assert.ok(command.kind === 'submit_response');
  assert.equal(JSON.stringify(restored.body), JSON.stringify(command.body));
});

// --- malformed and unavailable storage --------------------------------------------------------

test('a malformed stored record is discarded, never replayed', async () => {
  const keys = store.__scopedKeysForTests(LEARNER_A);
  globalThis.sessionStorage?.setItem(keys.pendingCommand ?? '', '{not json');

  assert.equal(await store.loadPendingCommand(LEARNER_A), null);
});

test('a record of an unrecognised shape is discarded and the slot cleared', async () => {
  const keys = store.__scopedKeysForTests(LEARNER_A);
  globalThis.sessionStorage?.setItem(keys.pendingCommand ?? '', JSON.stringify({ kind: 'nope' }));

  assert.equal(await store.loadPendingCommand(LEARNER_A), null);
  assert.equal(await store.loadPendingCommand(LEARNER_A), null, 'and stays discarded');
});

test('storage that throws degrades to in-memory rather than crashing', async () => {
  const real = globalThis.sessionStorage;
  // Models blocked site data / Safari private mode: every accessor throws.
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    get() {
      throw new Error('site data blocked');
    },
  });

  try {
    const command = submitCommand('session-blocked', 'opportunity-blocked');
    await assert.doesNotReject(store.savePendingCommand(LEARNER_A, command));
    // Still works for the life of the page -- which is exactly the pre-FE-018 behaviour.
    assert.deepEqual(await store.loadPendingCommand(LEARNER_A), command);
  } finally {
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: real });
  }
});

// --- sign-out cleanup ------------------------------------------------------------------------

test('sign-out clears only the signing-out learner, never the other learner', async () => {
  await store.savePendingCommand(LEARNER_A, submitCommand('session-A', 'opportunity-A'));
  await store.saveActiveSessionId(LEARNER_A, 'session-A');
  await store.savePendingCommand(LEARNER_B, submitCommand('session-B', 'opportunity-B'));
  await store.saveActiveSessionId(LEARNER_B, 'session-B');

  await store.clearLearnerSessionRecords(LEARNER_A);

  assert.equal(await store.loadPendingCommand(LEARNER_A), null, "A's record is gone");
  assert.equal(await store.loadActiveSessionId(LEARNER_A), null, "A's session id is gone");
  // The point of scoping: a shared device may hold a second learner's interrupted answer, and
  // signing out of this account is not a reason to destroy it.
  assert.ok(await store.loadPendingCommand(LEARNER_B), "B's record must survive A's sign-out");
  assert.equal(await store.loadActiveSessionId(LEARNER_B), 'session-B');
});

test('sign-out with no resolvable subject is safe and does not throw', async () => {
  await store.savePendingCommand(LEARNER_A, submitCommand('session-A', 'opportunity-A'));

  await assert.doesNotReject(store.clearLearnerSessionRecords(null));
  // And it must not have swept anything: an unscoped sweep is the bug, not the fix.
  assert.ok(await store.loadPendingCommand(LEARNER_A), 'a null-subject sign-out clears nothing');
});

test('sign-out completes even when storage throws', async () => {
  const real = globalThis.sessionStorage;
  Object.defineProperty(globalThis, 'sessionStorage', {
    configurable: true,
    get() {
      throw new Error('site data blocked');
    },
  });
  try {
    // Leaving a record behind is recoverable; failing to sign out is not.
    await assert.doesNotReject(store.clearLearnerSessionRecords(LEARNER_A));
  } finally {
    Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: real });
  }
});

// --- legacy unscoped keys ---------------------------------------------------------------------

test('a pre-B3 unscoped record is purged, never adopted by the current learner', async () => {
  const keys = store.__scopedKeysForTests(LEARNER_A);
  const legacyPendingKey = keys.legacy[0];
  globalThis.sessionStorage?.setItem(
    legacyPendingKey,
    JSON.stringify(submitCommand('someones-session', 'someones-opportunity')),
  );

  // The legacy record carries no subject, so there is no way to establish whose it was. Adopting an
  // ambiguous record into the signed-in learner's scope is precisely the cross-learner leak this
  // change closes, so it is discarded rather than migrated.
  const loaded = await store.loadPendingCommand(LEARNER_A);

  assert.equal(loaded, null, 'the ambiguous record must not be served to this learner');
  assert.equal(
    globalThis.sessionStorage?.getItem(legacyPendingKey) ?? null,
    null,
    'and it must not be left sitting in storage',
  );
});

test('the legacy purge runs once per app run, not on every call', async () => {
  const keys = store.__scopedKeysForTests(LEARNER_A);
  await store.loadPendingCommand(LEARNER_A); // triggers the purge

  // A legacy key written AFTER the one-shot purge is not re-purged. This pins the "once" property;
  // nothing reads that key any more either way, so a survivor is inert.
  globalThis.sessionStorage?.setItem(keys.legacy[0], 'written-after-purge');
  await store.loadPendingCommand(LEARNER_A);
  assert.equal(globalThis.sessionStorage?.getItem(keys.legacy[0]), 'written-after-purge');
});

// --- the platform abstraction is intact -------------------------------------------------------

test('the native path still uses SecureStore, with the device-only keychain option', () => {
  // These cases force the web branch, so the native branch is asserted structurally rather than
  // left unverified. Android behaviour is explicitly unchanged by FE-018.
  const source = readFileSync('src/features/session/session-command-store.ts', 'utf8');
  assert.match(source, /SecureStore\.setItemAsync\(key, value, \{/);
  assert.match(source, /keychainAccessible: SecureStore\.WHEN_UNLOCKED_THIS_DEVICE_ONLY/);
  assert.match(source, /SecureStore\.getItemAsync\(key\)/);
  assert.match(source, /SecureStore\.deleteItemAsync\(key\)/);
});

/**
 * Both files DISCUSS `localStorage` at length -- explaining why it was rejected -- so an assertion
 * about it has to be about code, not prose. Comments are stripped first; what remains is what
 * actually executes.
 */
function executableSource(path: string): string {
  return readFileSync(path, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
}

test('auth storage keeps the same native path and uses sessionStorage on web', () => {
  const code = executableSource('src/auth/secure-storage.ts');
  assert.match(code, /keychainAccessible: SecureStore\.WHEN_UNLOCKED_THIS_DEVICE_ONLY/);
  assert.match(code, /readWebSessionValue/);
  assert.doesNotMatch(code, /localStorage/, 'web auth tokens must not go to localStorage');
});

test('the web storage helper never reaches for localStorage', () => {
  const code = executableSource('src/utils/web-session-storage.ts');
  assert.doesNotMatch(code, /localStorage/, 'the helper must only ever touch sessionStorage');
  assert.match(code, /sessionStorage/);
});
