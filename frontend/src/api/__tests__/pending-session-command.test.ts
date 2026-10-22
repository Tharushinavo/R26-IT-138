import { test } from 'node:test';
import assert from 'node:assert/strict';
import Module from 'node:module';

import type {
  PendingCompleteOpportunityCommand,
  PendingRequestAssistCommand,
  PendingStartSessionCommand,
  PendingSubmitResponseCommand,
} from '@/src/api/contracts';
import {
  isPendingCompleteOpportunityCommand,
  isPendingRequestAssistCommand,
  isPendingSessionCommand,
  isPendingStartSessionCommand,
  isPendingSubmitResponseCommand,
} from '@/src/api/runtime-validation';

// session-command-store.ts requires `react-native` (for Platform.OS) and `expo-secure-store` at
// module scope. Neither can load under the plain esbuild/tsx test runner used by `test:contract`
// (react-native's entry file uses Flow's `import typeof`, which esbuild rejects, and no test file
// in this suite has ever needed a React Native module before). There is no jest/RN test preset
// wired up for `test:contract`, and adding one is out of scope for this batch. Since the store's
// own web-vs-native branch is exactly what the "round-trip against the web Map backend" case
// needs to exercise, `Module.prototype.require` is monkeypatched to intercept those two bare
// specifiers before the store module is required, forcing `Platform.OS === 'web'` and stubbing
// SecureStore's unused-on-web exports. (A `node:module` ESM `register()` loader hook was tried
// first and does not work here: this file — and everything it pulls in — runs as CJS under tsx's
// default transform, since `frontend/package.json` has no `"type": "module"`, and ESM loader
// hooks never see CJS `require()` calls.) This affects only this file's module registry —
// `node --test` isolates each test file into its own worker/process.
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

// eslint-disable-next-line @typescript-eslint/no-require-imports
const commandStore: typeof import('@/src/features/session/session-command-store') = require('../../features/session/session-command-store');
const {
  clearActiveSessionId,
  clearPendingCommand,
  loadActiveSessionId,
  loadPendingCommand,
  saveActiveSessionId,
  savePendingCommand,
} = commandStore;

const startCommand: PendingStartSessionCommand = {
  createdAt: '2026-07-29T00:00:00.000Z',
  endpoint: '/api/v1/b/sessions',
  idempotencyKey: 'idem-start-1',
  kind: 'start_session',
};

const submitResponseCommand: PendingSubmitResponseCommand = {
  body: { client_elapsed_ms: 4231, submitted_value: '7' },
  createdAt: '2026-07-29T00:00:01.000Z',
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/responses',
  idempotencyKey: 'idem-submit-1',
  itemOpportunityId: 'opp-1',
  kind: 'submit_response',
  sessionId: 'session-1',
};

const requestAssistCommand: PendingRequestAssistCommand = {
  createdAt: '2026-07-29T00:00:02.000Z',
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/assists',
  idempotencyKey: 'idem-assist-1',
  itemOpportunityId: 'opp-1',
  kind: 'request_assist',
  sessionId: 'session-1',
};

const completeOpportunityCommand: PendingCompleteOpportunityCommand = {
  createdAt: '2026-07-29T00:00:03.000Z',
  endpoint: '/api/v1/b/sessions/{sessionId}/opportunities/{itemOpportunityId}/complete',
  idempotencyKey: 'idem-complete-1',
  itemOpportunityId: 'opp-1',
  kind: 'complete_opportunity',
  sessionId: 'session-1',
};

test('isPendingStartSessionCommand accepts a valid start_session command', () => {
  assert.equal(isPendingStartSessionCommand(startCommand), true);
  assert.equal(isPendingSessionCommand(startCommand), true);
});

test('isPendingSubmitResponseCommand accepts a valid submit_response command', () => {
  assert.equal(isPendingSubmitResponseCommand(submitResponseCommand), true);
  assert.equal(isPendingSessionCommand(submitResponseCommand), true);
});

test('isPendingSubmitResponseCommand accepts an empty-string submitted_value', () => {
  const command = {
    ...submitResponseCommand,
    body: { ...submitResponseCommand.body, submitted_value: '' },
  };
  assert.equal(isPendingSubmitResponseCommand(command), true);
});

test('isPendingSubmitResponseCommand rejects a non-finite client_elapsed_ms', () => {
  const command = {
    ...submitResponseCommand,
    body: { ...submitResponseCommand.body, client_elapsed_ms: Infinity },
  };
  assert.equal(isPendingSubmitResponseCommand(command), false);
});

test('isPendingSubmitResponseCommand rejects a negative client_elapsed_ms', () => {
  const command = {
    ...submitResponseCommand,
    body: { ...submitResponseCommand.body, client_elapsed_ms: -1 },
  };
  assert.equal(isPendingSubmitResponseCommand(command), false);
});

test('isPendingRequestAssistCommand accepts a valid request_assist command', () => {
  assert.equal(isPendingRequestAssistCommand(requestAssistCommand), true);
  assert.equal(isPendingSessionCommand(requestAssistCommand), true);
});

test('isPendingCompleteOpportunityCommand accepts a valid complete_opportunity command', () => {
  assert.equal(isPendingCompleteOpportunityCommand(completeOpportunityCommand), true);
  assert.equal(isPendingSessionCommand(completeOpportunityCommand), true);
});

test('isPendingSessionCommand fails closed on an unknown kind', () => {
  assert.equal(isPendingSessionCommand({ ...startCommand, kind: 'unknown_kind' }), false);
});

test('isPendingSessionCommand fails closed when kind is absent entirely', () => {
  const { kind: _kind, ...withoutKind } = startCommand;
  assert.equal(isPendingSessionCommand(withoutKind), false);
});

// Every store call is now subject-scoped (B3). A fixed subject keeps these cases testing what they
// always tested -- round-tripping and corruption handling -- while the scoping behaviour itself is
// covered by session-command-store-scoping.test.ts.
const SUBJECT = 'subject-aaaaaaaa-1111-2222-3333-444444444444';

const variants: {
  name: string;
  command:
    | PendingStartSessionCommand
    | PendingSubmitResponseCommand
    | PendingRequestAssistCommand
    | PendingCompleteOpportunityCommand;
}[] = [
  { command: startCommand, name: 'start_session' },
  { command: submitResponseCommand, name: 'submit_response' },
  { command: requestAssistCommand, name: 'request_assist' },
  { command: completeOpportunityCommand, name: 'complete_opportunity' },
];

for (const { command, name } of variants) {
  test(`pending command store round-trips a ${name} command via the web Map backend`, async () => {
    await clearPendingCommand(SUBJECT);
    await savePendingCommand(SUBJECT, command);
    const loaded = await loadPendingCommand(SUBJECT);
    assert.deepEqual(loaded, command);
    await clearPendingCommand(SUBJECT);
    assert.equal(await loadPendingCommand(SUBJECT), null);
  });
}

test('a submit_response body survives save -> load byte-identical (fingerprint-critical)', async () => {
  await clearPendingCommand(SUBJECT);
  await savePendingCommand(SUBJECT, submitResponseCommand);
  const loaded = await loadPendingCommand(SUBJECT);
  assert.ok(loaded && loaded.kind === 'submit_response');
  assert.deepEqual(loaded.body, submitResponseCommand.body);
  assert.equal(JSON.stringify(loaded.body), JSON.stringify(submitResponseCommand.body));
  await clearPendingCommand(SUBJECT);
});

for (const { command, name } of variants) {
  test(`pending command store discards a corrupt stored ${name} payload rather than replaying it`, async () => {
    await clearPendingCommand(SUBJECT);
    const corrupted = { ...command, kind: 'not_a_real_kind' };
    await savePendingCommand(SUBJECT, corrupted as never);
    const loaded = await loadPendingCommand(SUBJECT);
    assert.equal(loaded, null);
  });
}

test('loadActiveSessionId round-trips a saved session id', async () => {
  await clearActiveSessionId(SUBJECT);
  await saveActiveSessionId(SUBJECT, 'session-abc-123');
  assert.equal(await loadActiveSessionId(SUBJECT), 'session-abc-123');
  await clearActiveSessionId(SUBJECT);
  assert.equal(await loadActiveSessionId(SUBJECT), null);
});

test('loadActiveSessionId discards a corrupt (empty-string) stored value', async () => {
  await clearActiveSessionId(SUBJECT);
  await saveActiveSessionId(SUBJECT, '');
  assert.equal(await loadActiveSessionId(SUBJECT), null);
});
