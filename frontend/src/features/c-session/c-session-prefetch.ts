import { createComponentCApi, getComponentCDevelopmentFixture } from '@/src/api/component-c-api';
import { decideSessionBootstrap } from '@/src/features/c-session/c-session-logic';
import { readPublicConfig } from '@/src/config/env';
import type { CSessionPrefetchResult } from '@/src/features/c-session/c-session-prefetch-cache';

/**
 * Runs the SAME resume-or-create-then-next-task sequence `c-session-screen.tsx`'s own
 * `bootstrap()` runs, so `requestPlay` (adventure-charge-context.tsx) can do it once, before
 * navigating, while Home shows its own blurred-loading state -- see c-session-prefetch-cache.ts
 * for why calling `nextTask` from here is safe rather than a duplicate-open risk.
 *
 * Returns `null` (never throws) for "nothing to hand off" -- no configured API, no access token,
 * or `decideSessionBootstrap` returning `not-ready` (grade/sessionMode not accepted). `null` is a
 * real, valid cache value: it tells the consumer "run your own normal bootstrap," not "something
 * broke." A genuine network/API failure (a thrown `ApiClientError`) is left to propagate, exactly
 * as `requestPlay`'s own caller already expects to catch and fall back on.
 */
export async function prefetchCSessionBootstrap(
  grade: number,
  getAccessToken: (refresh?: boolean) => Promise<string | null>,
): Promise<CSessionPrefetchResult> {
  const configResult = readPublicConfig();
  const api = configResult.config
    ? createComponentCApi(configResult.config)
    : getComponentCDevelopmentFixture()
      ? createComponentCApi()
      : null;
  if (!api) return null;

  const accessToken = await getAccessToken();
  if (!accessToken) return null;

  const active = await api.getActiveSession(accessToken);
  const decision = decideSessionBootstrap(active, grade, 'c_only');
  if (decision.action === 'not-ready') return null;

  const cSessionId =
    decision.action === 'resume' ? decision.cSessionId : (await api.createSession(decision.body, accessToken)).c_session_id;
  const task = await api.nextTask(cSessionId, accessToken);
  return { cSessionId, task };
}
