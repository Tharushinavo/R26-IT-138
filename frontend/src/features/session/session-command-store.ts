import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import type { PendingSessionCommand, PendingStartSessionCommand } from '@/src/api/contracts';
import { isPendingSessionCommand } from '@/src/api/runtime-validation';
import {
  listWebSessionKeys,
  readWebSessionValue,
  removeWebSessionValue,
  writeWebSessionValue,
} from '@/src/utils/web-session-storage';

/**
 * Local recovery records for Component B: the in-flight answer command, and the active session id.
 *
 * TWO CHANGES AT FE-018 / B3 (owner ruling, 2026-10-09), both of which the previous version got
 * wrong in ways that only showed on one platform each:
 *
 * 1. WEB NOW PERSISTS. This was a module-scoped `Map`, so a page reload lost the record whose whole
 *    purpose is surviving an interruption. It is now tab-lifetime `sessionStorage` (see
 *    src/utils/web-session-storage.ts). Android was always correct and is unchanged.
 *
 * 2. KEYS ARE SUBJECT-SCOPED. They were global -- `component_b.pending_start_session` for every
 *    learner on the device. On a shared classroom device that meant learner A's record was readable
 *    while learner B was signed in. It never produced a wrong SUBMISSION, because
 *    `decidePendingReplay` compares `sessionId` and `itemOpportunityId` and discards a mismatch --
 *    and that check stays exactly as it is, because key scoping is a second line of defence, not a
 *    replacement for it. But the record should not have been reachable at all.
 *
 * WHY `subject` IS A REQUIRED PARAMETER RATHER THAN READ FROM A CONTEXT HERE. Every one of these
 * functions is called from a screen that already knows the authenticated subject, and making it an
 * argument means the compiler refuses a call site that has not decided whose record it is. A module
 * that resolved the subject itself would be a second source of truth for identity.
 *
 * `null` is accepted and means "no durable record" -- a no-op write and a `null` read. The only
 * path that reaches these functions without a subject is the development preview
 * (`status === 'preview'`, where `me` is null), which does not implement the session loop. Writing
 * an unscoped record in that case is exactly the behaviour being removed, so it is refused instead.
 */

const PENDING_COMMAND_PREFIX = 'component_b.pending_start_session';
const ACTIVE_SESSION_PREFIX = 'component_b.active_session_id';

/**
 * The pre-B3 unscoped keys. Read by nothing any more; purged on first use so a device that ran an
 * older build does not keep one learner's record sitting on disk indefinitely.
 *
 * DELIBERATELY NOT MIGRATED to the current learner. The stored record carries `sessionId` and
 * `itemOpportunityId` but no subject, so there is no way to establish whose it was -- and adopting
 * an ambiguous record into the signed-in learner's scope is precisely the cross-learner leak this
 * change exists to close. Discarding it costs at most one replay of an interrupted answer on the
 * single launch after upgrading; `decidePendingReplay` would have discarded a mismatched one
 * anyway, and the server's idempotency record is the authority on whether that answer landed.
 */
const LEGACY_UNSCOPED_KEYS = [PENDING_COMMAND_PREFIX, ACTIVE_SESSION_PREFIX] as const;

/**
 * SecureStore accepts only alphanumerics, `.`, `-` and `_` in a key and THROWS on anything else
 * (the hazard `src/utils/adventure-charge.ts` documents having been bitten by). A Supabase subject
 * is a UUID, so it already satisfies that -- this guards against a future identity format that
 * does not, by refusing to build a key rather than throwing deep inside a storage call.
 */
const SAFE_SUBJECT = /^[A-Za-z0-9._-]+$/;

function scopedKey(prefix: string, subject: string): string | null {
  if (!SAFE_SUBJECT.test(subject)) return null;
  return `${prefix}.${subject}`;
}

async function read(key: string) {
  return Platform.OS === 'web' ? readWebSessionValue(key) : SecureStore.getItemAsync(key);
}

async function write(key: string, value: string) {
  if (Platform.OS === 'web') {
    writeWebSessionValue(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value, {
    keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
}

async function remove(key: string) {
  if (Platform.OS === 'web') {
    removeWebSessionValue(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

let legacyPurged = false;

/**
 * Best-effort, once per app run. A failure here must never surface: the only consequence of not
 * purging is that a stale pre-B3 record stays on disk unread, which is no worse than before.
 */
async function purgeLegacyUnscopedKeys(): Promise<void> {
  if (legacyPurged) return;
  legacyPurged = true;
  for (const key of LEGACY_UNSCOPED_KEYS) {
    try {
      await remove(key);
    } catch {
      // Ignored deliberately -- see above.
    }
  }
}

export async function loadPendingCommand(subject: string | null): Promise<PendingSessionCommand | null> {
  await purgeLegacyUnscopedKeys();
  if (subject === null) return null;
  const key = scopedKey(PENDING_COMMAND_PREFIX, subject);
  if (key === null) return null;
  const stored = await read(key);
  if (!stored) return null;
  try {
    const parsed: unknown = JSON.parse(stored);
    if (isPendingSessionCommand(parsed)) return parsed;
  } catch {
    // Invalid local recovery data is discarded below and never sent.
  }
  await remove(key);
  return null;
}

export async function savePendingCommand(subject: string | null, command: PendingSessionCommand) {
  await purgeLegacyUnscopedKeys();
  if (subject === null) return;
  const key = scopedKey(PENDING_COMMAND_PREFIX, subject);
  if (key === null) return;
  await write(key, JSON.stringify(command));
}

export async function clearPendingCommand(subject: string | null) {
  if (subject === null) return;
  const key = scopedKey(PENDING_COMMAND_PREFIX, subject);
  if (key === null) return;
  await remove(key);
}

export async function loadPendingStartCommand(
  subject: string | null,
): Promise<PendingStartSessionCommand | null> {
  const pending = await loadPendingCommand(subject);
  return pending?.kind === 'start_session' ? pending : null;
}

export async function savePendingStartCommand(subject: string | null, command: PendingStartSessionCommand) {
  await savePendingCommand(subject, command);
}

export async function clearPendingStartCommand(subject: string | null) {
  await clearPendingCommand(subject);
}

export async function saveActiveSessionId(subject: string | null, sessionId: string) {
  await purgeLegacyUnscopedKeys();
  if (subject === null) return;
  const key = scopedKey(ACTIVE_SESSION_PREFIX, subject);
  if (key === null) return;
  await write(key, sessionId);
}

export async function loadActiveSessionId(subject: string | null): Promise<string | null> {
  await purgeLegacyUnscopedKeys();
  if (subject === null) return null;
  const key = scopedKey(ACTIVE_SESSION_PREFIX, subject);
  if (key === null) return null;
  const stored = await read(key);
  if (typeof stored === 'string' && stored.trim().length > 0) return stored;
  await remove(key);
  return null;
}

export async function clearActiveSessionId(subject: string | null) {
  if (subject === null) return;
  const key = scopedKey(ACTIVE_SESSION_PREFIX, subject);
  if (key === null) return;
  await remove(key);
}

/**
 * Sign-out cleanup (B3). Clears ONE learner's records, never everybody's: a shared device may hold
 * a second learner's interrupted answer, and signing out of this account is not a reason to destroy
 * it. `clearPendingCommand`/`clearActiveSessionId` are already no-ops for a null subject, so a
 * sign-out that happens with no resolvable subject -- a configuration failure, or a session that
 * expired before `me` ever loaded -- is safe rather than a thrown error inside `signOut`.
 *
 * Every step is independently guarded. Sign-out must complete even if storage is unavailable:
 * leaving a record behind is recoverable, failing to sign out is not.
 */
export async function clearLearnerSessionRecords(subject: string | null): Promise<void> {
  try {
    await clearPendingCommand(subject);
  } catch {
    // see above
  }
  try {
    await clearActiveSessionId(subject);
  } catch {
    // see above
  }
}

/** Test-only: the key shape, so a test can assert scoping without duplicating the format string. */
export function __scopedKeysForTests(subject: string) {
  return {
    activeSession: scopedKey(ACTIVE_SESSION_PREFIX, subject),
    legacy: [...LEGACY_UNSCOPED_KEYS],
    pendingCommand: scopedKey(PENDING_COMMAND_PREFIX, subject),
  };
}

/** Test-only: re-arms the one-shot legacy purge. */
export function __resetLegacyPurgeForTests() {
  legacyPurged = false;
}

/** Test-only: web keys currently held, for asserting sign-out cleanup. */
export function __webKeysForTests(): string[] {
  return [
    ...listWebSessionKeys(PENDING_COMMAND_PREFIX),
    ...listWebSessionKeys(ACTIVE_SESSION_PREFIX),
  ];
}
