import { useCallback, useMemo } from 'react';

import { useAuth } from '@/src/auth/auth-context';
import { readPublicConfig } from '@/src/config/env';
import { createCompdApi, withAccessToken, type CompdApi } from '@/src/features/compd/api/compd-api';

/**
 * What every compD screen needs to talk to `/api/v1/d/*`: the learner's subject (cache key) and a
 * `call` that supplies the access token with one refresh retry. A missing config is not thrown at
 * render time -- `createCompdApi` throws inside `call`, so the screen shows its own
 * "can't reach" state instead of crashing the tree.
 */
export function useCompdApi() {
  const { getAccessToken, me } = useAuth();
  const config = useMemo(() => readPublicConfig().config, []);
  const subject = me?.principal.user_id ?? null;

  const call = useCallback(
    <T,>(run: (api: CompdApi, accessToken: string) => Promise<T>) =>
      withAccessToken(getAccessToken, (accessToken) => run(createCompdApi(config), accessToken)),
    [config, getAccessToken],
  );

  return { call, subject };
}
