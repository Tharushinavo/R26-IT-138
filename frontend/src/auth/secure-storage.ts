import type { SupportedStorage } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import {
  readWebSessionValue,
  removeWebSessionValue,
  writeWebSessionValue,
} from '@/src/utils/web-session-storage';

/**
 * The storage Supabase persists its auth session into.
 *
 * Native uses the keychain/keystore. Web uses TAB-LIFETIME storage (FE-018, owner ruling
 * 2026-10-09): it was a module-scoped `Map`, so every page reload signed the learner out even
 * though `persistSession: true` was set on the client -- the client was faithfully persisting into
 * something that could not outlive the page.
 *
 * `sessionStorage`, deliberately not `localStorage`: a reload keeps the session, closing the tab
 * does not. See src/utils/web-session-storage.ts for the full reasoning, the in-memory fallback
 * when browser storage is blocked, and the explicit note that this is a persistence-lifetime
 * decision and **not** an XSS mitigation.
 *
 * Nothing about token validation changes. The backend still verifies every request's bearer token
 * against Supabase's JWKS (`app/infrastructure/auth.py`); where the client keeps its copy between
 * requests is not part of that check.
 */
export const authStorage: SupportedStorage = {
  async getItem(key) {
    if (Platform.OS === 'web') return readWebSessionValue(key);
    return SecureStore.getItemAsync(key);
  },
  async removeItem(key) {
    if (Platform.OS === 'web') {
      removeWebSessionValue(key);
      return;
    }
    await SecureStore.deleteItemAsync(key);
  },
  async setItem(key, value) {
    if (Platform.OS === 'web') {
      writeWebSessionValue(key, value);
      return;
    }
    await SecureStore.setItemAsync(key, value, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
  },
};
