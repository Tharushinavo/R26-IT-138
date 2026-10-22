import { useAuth as useHostAuth } from '@/src/auth/auth-context';

/**
 * The slice of compD's old AuthContext its screens still read, answered from MathMingo's auth.
 *
 * compD had its own login, JWT and roles; inside MathMingo none of that exists -- the learner signed
 * in through the host, and the (learner) group only admits learners. So `role` is always
 * 'student' (the teacher branches in compD's screens never render), and the name is the one the
 * host shows in its own header.
 */
export function useAuth() {
  const { me, profileName } = useHostAuth();
  return {
    role: 'student' as const,
    user: { full_name: profileName ?? '', id: me?.principal.user_id ?? '' },
  };
}
