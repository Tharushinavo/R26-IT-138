import type { Session } from '@supabase/supabase-js';
import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import { getAuthorizedLearner } from '@/src/api/client';
import type { AuthorizedLearner } from '@/src/api/contracts';
import { ApiClientError } from '@/src/api/errors';
import { getSupabaseClient } from '@/src/auth/supabase';
import { forgetCompdLearnerState } from '@/src/features/compd/compd-state-cache';
import { forgetHomeSessionState } from '@/src/features/home/home-session-state-cache';
import { clearLearnerSessionRecords } from '@/src/features/session/session-command-store';
import { readPublicConfig, type PublicConfig } from '@/src/config/env';

export type Gender = 'female' | 'male';

export type RegistrationInput = {
  displayName: string;
  email: string;
  gender: Gender;
  password: string;
};

export type AuthStatus =
  | 'access-denied'
  | 'authorized'
  | 'checking'
  | 'configuration-error'
  | 'onboarding'
  | 'preview'
  | 'signed-out'
  | 'unavailable';

type AuthActionResult =
  | { ok: true; requiresEmailConfirmation?: boolean }
  | { ok: false; message: string };

type AuthContextValue = {
  me: AuthorizedLearner | null;
  notice: string | null;
  profileGender: Gender | null;
  profileName: string | null;
  status: AuthStatus;
  continueToComponentBPreview: () => void;
  getAccessToken: (refresh?: boolean) => Promise<string | null>;
  retryAuthorization: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<AuthActionResult>;
  signOut: () => Promise<void>;
  signUpWithEmail: (input: RegistrationInput) => Promise<AuthActionResult>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readDisplayName(session: Session) {
  const value = session.user.user_metadata.display_name;
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

// The backend's own LearnerProfileResponse carries no gender field — it is captured once at
// sign-up (see signUpWithEmail's own `options.data.gender`) and stored only in Supabase's
// user_metadata, the same place display_name lives, read back the same way.
function readGender(session: Session): Gender | null {
  const value = session.user.user_metadata.gender;
  return value === 'female' || value === 'male' ? value : null;
}

function safeNotice(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.kind === 'forbidden') {
      return 'This account does not have learner access. Please ask a supervisor for help.';
    }
    if (error.kind === 'unauthenticated') return 'Your session expired. Please sign in again.';
    return error.requestId
      ? `We could not verify learner access. Support code: ${error.requestId}`
      : 'We could not verify learner access. Check the connection and try again.';
  }
  return 'Something went wrong while signing in. Please try again.';
}

// Supabase Auth returns a stable `code` field (see @supabase/auth-js's AuthError, and
// fetch.js reading the API's own `error_code`) alongside the human-readable `message` —
// matching on `code` is exact and is used for both the sign-in and sign-up paths below.
// Deliberately not more specific than "invalid_credentials" on sign-in: telling the user
// which of email/password was wrong would let an attacker enumerate registered emails.
function signInErrorMessage(code: string | undefined): string {
  if (code === 'invalid_credentials') {
    return 'That email or password is not right. Please re-enter your password and try again.';
  }
  if (code === 'over_request_rate_limit') {
    return 'Too many attempts. Please wait a moment and try again.';
  }
  if (code === 'email_not_confirmed') {
    return 'Please confirm your email address before signing in.';
  }
  return 'The sign-in service could not complete the request. Please try again.';
}

function signUpErrorMessage(code: string | undefined): string {
  if (code === 'user_already_exists') {
    return 'An account with this email already exists. Try signing in instead.';
  }
  if (code === 'weak_password') {
    return 'That password is too weak. Please choose a stronger one.';
  }
  if (code === 'over_email_send_rate_limit' || code === 'over_request_rate_limit') {
    return 'Too many attempts. Please wait a moment and try again.';
  }
  if (code === 'email_address_invalid') {
    return 'That email address is not valid.';
  }
  return 'We could not create the account. Check the details and try again.';
}

export function AuthProvider({ children }: PropsWithChildren) {
  const configResult = useMemo(() => readPublicConfig(), []);
  const config = configResult.config;
  const [status, setStatus] = useState<AuthStatus>('checking');
  const [me, setMe] = useState<AuthorizedLearner | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [profileGender, setProfileGender] = useState<Gender | null>(null);
  const [profileName, setProfileName] = useState<string | null>(null);
  const operationRef = useRef(0);

  const clearLocalSession = useCallback(async (resolvedConfig: PublicConfig, message?: string) => {
    await getSupabaseClient(resolvedConfig).auth.signOut({ scope: 'local' });
    setMe(null);
    setProfileGender(null);
    setProfileName(null);
    setStatus('signed-out');
    setNotice(message ?? null);
  }, []);

  const authorizeSession = useCallback(
    async (session: Session, resolvedConfig: PublicConfig) => {
      const operation = ++operationRef.current;
      const supabase = getSupabaseClient(resolvedConfig);
      setStatus('checking');
      setNotice(null);
      setProfileName(readDisplayName(session));
      setProfileGender(readGender(session));

      try {
        const authorizedUser = await getAuthorizedLearner(
          resolvedConfig,
          session.access_token,
          async () => {
            const { data, error } = await supabase.auth.refreshSession();
            return error ? null : (data.session?.access_token ?? null);
          },
        );

        if (operation !== operationRef.current) return;

        const membershipApproved = authorizedUser.classroomMembership?.state === 'APPROVED';
        if (!authorizedUser.learnerProfile || !membershipApproved) {
          setMe(authorizedUser);
          setStatus('onboarding');
          return;
        }

        setMe(authorizedUser);
        setProfileName(authorizedUser.learnerProfile.name.trim() || readDisplayName(session));
        setStatus('authorized');
      } catch (error) {
        if (operation !== operationRef.current) return;

        if (error instanceof ApiClientError && error.kind === 'unauthenticated') {
          await clearLocalSession(resolvedConfig, 'Your session expired. Please sign in again.');
          return;
        }

        setMe(null);
        setStatus(
          error instanceof ApiClientError && error.kind === 'forbidden'
            ? 'access-denied'
            : 'unavailable',
        );
        setNotice(safeNotice(error));
      }
    },
    [clearLocalSession],
  );

  useEffect(() => {
    if (!config) {
      setStatus('configuration-error');
      setNotice(configResult.error);
      return;
    }

    const supabase = getSupabaseClient(config);
    let mounted = true;

    void (async () => {
      try {
        const { data, error } = await supabase.auth.getSession();
        if (!mounted) return;

        if (error) {
          setStatus('unavailable');
          setNotice('Secure sign-in could not be restored. Please try again.');
        } else if (data.session) {
          await authorizeSession(data.session, config);
        } else {
          setStatus('signed-out');
        }
      } catch {
        if (!mounted) return;
        setStatus('unavailable');
        setNotice('Secure sign-in could not be restored. Please try again.');
      }
    })();

    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      if (!mounted) return;
      if (event === 'SIGNED_OUT' || !session) {
        operationRef.current += 1;
        setMe(null);
        setProfileGender(null);
        setProfileName(null);
        setStatus('signed-out');
      }
    });

    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, [authorizeSession, config, configResult.error]);

  const retryAuthorization = useCallback(async () => {
    if (!config) return;
    try {
      const { data, error } = await getSupabaseClient(config).auth.getSession();
      if (error) {
        setStatus('unavailable');
        setNotice('Secure sign-in could not be restored. Please try again.');
      } else if (data.session) {
        await authorizeSession(data.session, config);
      } else {
        setStatus('signed-out');
        setNotice(null);
      }
    } catch {
      setStatus('unavailable');
      setNotice('Secure sign-in could not be restored. Please try again.');
    }
  }, [authorizeSession, config]);

  const signInWithEmail = useCallback(
    async (email: string, password: string): Promise<AuthActionResult> => {
      if (!config) return { ok: false, message: 'The app is not configured for sign-in yet.' };
      setStatus('checking');
      setNotice(null);

      try {
        const { data, error } = await getSupabaseClient(config).auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (error || !data.session) {
          setStatus('signed-out');
          return {
            ok: false,
            message: signInErrorMessage(error?.code),
          };
        }

        await authorizeSession(data.session, config);
        return { ok: true };
      } catch {
        setStatus('signed-out');
        return { ok: false, message: 'The sign-in service could not be reached. Please try again.' };
      }
    },
    [authorizeSession, config],
  );

  const signUpWithEmail = useCallback(
    async (input: RegistrationInput): Promise<AuthActionResult> => {
      if (!config) return { ok: false, message: 'The app is not configured for sign-up yet.' };
      setStatus('checking');
      setNotice(null);

      try {
        const { data, error } = await getSupabaseClient(config).auth.signUp({
          email: input.email.trim(),
          password: input.password,
          options: {
            data: {
              display_name: input.displayName.trim(),
              gender: input.gender,
            },
          },
        });

        if (error || !data.user) {
          setStatus('signed-out');
          return {
            ok: false,
            message: signUpErrorMessage(error?.code),
          };
        }

        setProfileName(input.displayName.trim());
        setProfileGender(input.gender);

        if (!data.session) {
          setStatus('signed-out');
          return { ok: true, requiresEmailConfirmation: true };
        }

        setMe(null);
        setStatus('onboarding');
        return { ok: true };
      } catch {
        setStatus('signed-out');
        return { ok: false, message: 'The sign-up service could not be reached. Please try again.' };
      }
    },
    [config],
  );

  const signOut = useCallback(async () => {
    operationRef.current += 1;
    // THIS learner's local recovery records, cleared before the session goes (B3, 2026-10-09).
    // Read the subject first: once `setMe(null)` runs there is nothing left to scope the cleanup
    // to, and an unscoped sweep would delete a second learner's interrupted answer on a shared
    // classroom device. `clearLearnerSessionRecords` swallows its own storage failures and is a
    // no-op for a null subject, so a sign-out with no resolvable identity still completes.
    //
    // Deliberately NOT done in `clearLocalSession` (the expired-token path): an expired token is
    // not a change of learner. The record is still theirs and still replayable once they sign back
    // in, and the server's idempotency record remains the authority on whether the answer landed.
    await clearLearnerSessionRecords(me?.principal.user_id ?? null);
    // Home's in-memory progress cache, for the same reason and with the same scoping rule: it is
    // only what the panel DRAWS while revalidating, but on a shared classroom device a second
    // learner must never open Home onto the first one's session progress. Same deliberate omission
    // from `clearLocalSession` -- an expired token is not a change of learner, and the cached state
    // is still theirs.
    forgetHomeSessionState(me?.principal.user_id ?? null);
    // Component D's intro/language cache, same scoping and same omission from `clearLocalSession`:
    // the next learner on this device must reach compD through its own server answer.
    forgetCompdLearnerState(me?.principal.user_id ?? null);
    if (config) {
      try {
        await getSupabaseClient(config).auth.signOut({ scope: 'local' });
      } catch {
        // The local state below still fails closed if secure storage is unavailable.
      }
    }
    setMe(null);
    setNotice(null);
    setProfileGender(null);
    setProfileName(null);
    setStatus('signed-out');
  }, [config, me]);

  const continueToComponentBPreview = useCallback(() => {
    if (config?.appEnvironment === 'development') {
      setNotice(null);
      setStatus('preview');
    }
  }, [config]);

  const getAccessToken = useCallback(async (refresh = false) => {
    if (!config) return null;
    const supabase = getSupabaseClient(config);
    if (refresh) {
      const { data, error } = await supabase.auth.refreshSession();
      return error ? null : (data.session?.access_token ?? null);
    }
    const { data, error } = await supabase.auth.getSession();
    return error ? null : (data.session?.access_token ?? null);
  }, [config]);

  const value = useMemo<AuthContextValue>(
    () => ({
      continueToComponentBPreview,
      getAccessToken,
      me,
      notice,
      profileGender,
      profileName,
      retryAuthorization,
      signInWithEmail,
      signOut,
      signUpWithEmail,
      status,
    }),
    [
      continueToComponentBPreview,
      getAccessToken,
      me,
      notice,
      profileGender,
      profileName,
      retryAuthorization,
      signInWithEmail,
      signOut,
      signUpWithEmail,
      status,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider.');
  return value;
}
