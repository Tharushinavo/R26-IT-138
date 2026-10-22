import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * The "adventure battery" that gates Component C ("Play"): a child fills it by completing real
 * Component B sessions, and only unlocks Play once it reads full. Local-only, on-device, keyed by
 * Supabase subject so two accounts on one device never share a gauge — there is no backend field
 * for this yet, and it is not meant to be a scored/reported value, only a motivational nudge.
 *
 * Daily decay is a real, PLANNED part of this mechanic (the owner's original spec: the level
 * counts down over time so a child has to keep playing Component B to keep Play unlocked) but is
 * NOT implemented here. The literal numbers as first stated -- max 4 levels, -3/day -- would empty
 * the gauge after a single missed day, which the owner asked to confirm before it ships. Charging
 * up currently has no corresponding way down other than the cap itself.
 */
export const ADVENTURE_CHARGE_MAX_LEVEL = 4;

type AdventureChargeState = { level: number; awardedSessionIds: string[] };

const EMPTY_STATE: AdventureChargeState = { level: 0, awardedSessionIds: [] };

// Bounds how many session ids are remembered for idempotency -- old ones age out; they only ever
// need to prevent a DOUBLE-award for a session still in view, never a lifetime ledger.
const MAX_REMEMBERED_SESSION_IDS = 50;

/**
 * SecureStore accepts only alphanumerics, ".", "-" and "_" in a key, and THROWS on anything else --
 * so the ":" this used everywhere made every native read reject, which surfaced as an uncaught
 * promise that took Home down before it could render. localStorage has no such rule, so the bug
 * was invisible on web and fatal on device.
 *
 * Web therefore keeps the historical ":" key, leaving existing browser gauges where they are.
 * Native uses "_", and orphans nothing: the colon threw before a single native value was ever
 * written, so there is no native data under the old spelling to migrate.
 */
function storageKey(subject: string): string {
  return `adventure-charge${Platform.OS === 'web' ? ':' : '_'}${subject}`;
}

/**
 * Storage failures are swallowed on purpose. This gauge is a local-only motivational nudge with no
 * backend field behind it (see the note above), so a device that refuses to read or write it should
 * cost the child their charge, never their app: it reads as empty and an award is dropped.
 */
async function readRaw(subject: string): Promise<string | null> {
  try {
    if (Platform.OS === 'web') return window.localStorage.getItem(storageKey(subject));
    return await SecureStore.getItemAsync(storageKey(subject));
  } catch {
    return null;
  }
}

async function writeRaw(subject: string, value: string): Promise<void> {
  try {
    if (Platform.OS === 'web') {
      window.localStorage.setItem(storageKey(subject), value);
      return;
    }
    await SecureStore.setItemAsync(storageKey(subject), value);
  } catch {
    /* see readRaw: a failed write loses one charge level, it does not break the session. */
  }
}

function parseState(raw: string | null): AdventureChargeState {
  if (!raw) return EMPTY_STATE;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null) return EMPTY_STATE;
    const record = parsed as Record<string, unknown>;
    const rawLevel = typeof record.level === 'number' ? record.level : 0;
    const level = Math.max(0, Math.min(ADVENTURE_CHARGE_MAX_LEVEL, Math.trunc(rawLevel)));
    const awardedSessionIds = Array.isArray(record.awardedSessionIds)
      ? record.awardedSessionIds.filter((id): id is string => typeof id === 'string')
      : [];
    return { level, awardedSessionIds };
  } catch {
    return EMPTY_STATE;
  }
}

/** Current charge level (0..ADVENTURE_CHARGE_MAX_LEVEL) for this account, on this device. */
export async function getAdventureChargeLevel(subject: string): Promise<number> {
  return parseState(await readRaw(subject)).level;
}

/**
 * Awards one charge level for a genuinely completed Component B session, capped at
 * ADVENTURE_CHARGE_MAX_LEVEL. Idempotent per `sessionId` -- calling this again for a session
 * already credited returns the unchanged level rather than awarding twice, so a remount or a
 * re-render of the same completed screen can never double-count one session.
 */
export async function awardAdventureCharge(subject: string, sessionId: string): Promise<number> {
  const state = parseState(await readRaw(subject));
  if (state.awardedSessionIds.includes(sessionId)) return state.level;

  const level = Math.min(ADVENTURE_CHARGE_MAX_LEVEL, state.level + 1);
  const awardedSessionIds = [...state.awardedSessionIds, sessionId].slice(-MAX_REMEMBERED_SESSION_IDS);
  await writeRaw(subject, JSON.stringify({ level, awardedSessionIds }));
  return level;
}
