import { createClient, processLock, type SupabaseClient } from '@supabase/supabase-js';
import { AppState, Platform } from 'react-native';
import 'react-native-url-polyfill/auto';

import { authStorage } from '@/src/auth/secure-storage';
import type { PublicConfig } from '@/src/config/env';

let client: SupabaseClient | null = null;
let appStateListenerInstalled = false;

export function getSupabaseClient(config: PublicConfig) {
  if (!client) {
    client = createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: {
        autoRefreshToken: true,
        detectSessionInUrl: false,
        flowType: 'pkce',
        lock: processLock,
        persistSession: true,
        storage: authStorage,
      },
    });
  }

  if (Platform.OS !== 'web' && !appStateListenerInstalled) {
    appStateListenerInstalled = true;
    AppState.addEventListener('change', (state) => {
      if (state === 'active') client?.auth.startAutoRefresh();
      else client?.auth.stopAutoRefresh();
    });
  }

  return client;
}
