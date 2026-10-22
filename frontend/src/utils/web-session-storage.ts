/**
 * Tab-lifetime storage for the web target, with an in-memory fallback.
 *
 * WHY THIS EXISTS (FE-018, owner ruling 2026-10-09). Two separate stores -- the Supabase auth
 * session (`src/auth/secure-storage.ts`) and the pending-answer command
 * (`src/features/session/session-command-store.ts`) -- each kept a private `Map` on web, so a page
 * reload signed the learner out AND dropped the record that protects an in-flight answer. Android
 * was never affected: it uses SecureStore and persists properly.
 *
 * WHY `sessionStorage` AND NOT `localStorage`. The requirement is "survive a page reload", not
 * "survive closing the browser". `sessionStorage` is scoped to the tab, so a reload keeps the
 * session while walking away from a shared classroom machine does not leave a learner's tokens
 * sitting at rest for the next child. `localStorage` would have given the second property away for
 * nothing the requirement asked for.
 *
 * WHAT THIS IS NOT. It is **not** an XSS mitigation, and must never be described as one. Script
 * running in this origin can read `sessionStorage`, and can equally read the live Supabase client's
 * in-memory session or simply act through the authenticated session -- so the in-memory `Map` this
 * replaces was not protecting against that either. The only thing the choice of backing store
 * changes is **exposure at rest**: how long a token outlives the child's use of the tab.
 *
 * Trade-off accepted with the ruling: a NEW TAB starts signed out, because `sessionStorage` is
 * per-tab by definition. That is the intended behaviour, not a defect.
 *
 * SCOPE: web only. Nothing here is reachable on native -- both callers branch on `Platform.OS`
 * before using it, and native keeps SecureStore untouched.
 */

/**
 * The fallback. Used when `sessionStorage` is missing or throws -- Safari private mode, blocked
 * site data, an embedded webview with storage disabled, or a quota failure. Behaviour then is
 * exactly what both stores did before FE-018: it works for the life of the page and does not
 * survive a reload. Degrading to the old behaviour is the right failure mode; throwing would take
 * authentication initialisation or sign-out down with it.
 */
const memoryFallback = new Map<string, string>();

/**
 * The two operations that can throw are the ones that touch the store, so availability is probed
 * by USE rather than cached. A cached verdict would be wrong in both directions: storage can be
 * blocked after first use, and a transient quota failure would permanently demote an otherwise
 * working store.
 *
 * Reads prefer `sessionStorage` and fall back to memory, so a value written during a failed period
 * is still found afterwards.
 */
function sessionStore(): Storage | null {
  try {
    if (typeof globalThis === 'undefined') return null;
    const candidate = (globalThis as { sessionStorage?: Storage }).sessionStorage;
    return candidate ?? null;
  } catch {
    // Accessing the property itself can throw when site data is blocked.
    return null;
  }
}

export function readWebSessionValue(key: string): string | null {
  const store = sessionStore();
  if (store) {
    try {
      const value = store.getItem(key);
      if (value !== null) return value;
    } catch {
      // fall through to the in-memory copy
    }
  }
  return memoryFallback.get(key) ?? null;
}

export function writeWebSessionValue(key: string, value: string): void {
  const store = sessionStore();
  if (store) {
    try {
      store.setItem(key, value);
      // Keep the fallback clean so a later read cannot resurrect a stale duplicate from memory
      // after a successful write.
      memoryFallback.delete(key);
      return;
    } catch {
      // Quota, private mode, or blocked site data -- keep the value for this page at least.
    }
  }
  memoryFallback.set(key, value);
}

export function removeWebSessionValue(key: string): void {
  const store = sessionStore();
  if (store) {
    try {
      store.removeItem(key);
    } catch {
      // Nothing to do; the memory delete below still runs.
    }
  }
  memoryFallback.delete(key);
}

/**
 * Every key this module currently holds, for sign-out cleanup that must not guess at key shapes.
 * Only keys written through `writeWebSessionValue` are reported; the in-memory fallback is included
 * so a sign-out during blocked storage still clears what it wrote.
 */
export function listWebSessionKeys(prefix: string): string[] {
  const keys = new Set<string>();
  const store = sessionStore();
  if (store) {
    try {
      for (let index = 0; index < store.length; index += 1) {
        const key = store.key(index);
        if (key !== null && key.startsWith(prefix)) keys.add(key);
      }
    } catch {
      // fall through to the in-memory keys
    }
  }
  for (const key of memoryFallback.keys()) {
    if (key.startsWith(prefix)) keys.add(key);
  }
  return [...keys];
}

/** Test-only: drops the in-memory fallback so one case cannot leak into the next. */
export function __resetWebSessionFallbackForTests(): void {
  memoryFallback.clear();
}
