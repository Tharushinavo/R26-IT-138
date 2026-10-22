import * as Crypto from 'expo-crypto';

import { createComponentBApi, getComponentBDevelopmentFixture } from '@/src/api/component-b-api';
import { readPublicConfig } from '@/src/config/env';
import type { BSessionPrefetchResult } from '@/src/features/session/b-session-prefetch-cache';
import { resolveResumableSessionId } from '@/src/features/session/resumable-session';
import { saveActiveSessionId } from '@/src/features/session/session-command-store';

/**
 * Runs the same start-or-resume-then-select sequence the preparation screen and live session
 * screen would run in series, once, from Home's hero press -- so the question is in hand before
 * the child ever reaches the session screen. See b-session-prefetch-cache.ts for why this is safe
 * against duplicate opens, and for the 5-minute clock this deliberately keeps short.
 *
 * Returns `null` (never throws) for "nothing to hand off": no configured API, no access token, or
 * the development fixture, which does not implement the session loop at all. `null` is a real
 * cache value meaning "run your own normal path", not "something broke". A genuine API failure is
 * left to propagate so the caller can fall through to the unprefetched path, which is the existing
 * behaviour in full.
 *
 * `checkReadiness` is NOT called here. The preparation screen runs it in parallel on its own mount
 * and owns every readiness failure phase; duplicating it would only add a round trip to the one
 * path this exists to shorten.
 */
export async function prefetchBSessionBootstrap(
  subject: string | null,
  getAccessToken: (refresh?: boolean) => Promise<string | null>,
): Promise<BSessionPrefetchResult> {
  const configResult = readPublicConfig();
  const fixture = getComponentBDevelopmentFixture();
  // The fixture throws on every session-loop call by design, so there is nothing to prefetch.
  if (fixture) return null;
  if (!configResult.config) return null;
  const api = createComponentBApi(configResult.config);

  const accessToken = await getAccessToken();
  if (!accessToken) return null;

  // Resume wins over starting a new one, matching startAdventure's own order. POST /b/sessions is
  // safe either way (it returns any starting-or-active session for the learner regardless of
  // idempotency key, b_session_lifecycle.py), so this read is an optimisation, not a correctness
  // requirement.
  const resumableSessionId = await resolveResumableSessionId(api, accessToken);
  const sessionId =
    resumableSessionId ??
    (await (async () => {
      const response = await api.startSession(Crypto.randomUUID(), accessToken);
      if (response.state !== 'active') throw new Error('prefetch: session did not start active');
      return response.session_id;
    })());

  // Mirrors navigateToSession: a relaunch must be able to find this session again. Written before
  // the question is selected, so an app kill between the two still leaves a resumable session
  // rather than an orphan.
  await saveActiveSessionId(subject, sessionId);

  const presentation = await api.selectOpportunity(sessionId, accessToken);
  return { presentation, sessionId };
}
