// Thin route boundary for the Component C run-length choice, between the Play prep card and the
// game itself. Static, like `c-session.tsx` and for the same reason: there is no externally
// supplied id for a dynamic segment to carry.
//
// `grade` and `sessionMode` are read as optional query params, validated rather than trusted, and
// forwarded UNCHANGED to c-session -- this route invents neither, and must not, because the prep
// card's background prefetch already created a session against that exact grade.

import { router, useLocalSearchParams } from 'expo-router';

import type { CreateCSessionRequest } from '@/src/api/generated/openapi-types';
import { ChallengeChoiceScreen } from '@/src/features/c-session/challenge-choice-screen';
import type { ChallengeLength } from '@/src/features/c-session/challenge-length';

function parseSessionMode(raw: string | undefined): CreateCSessionRequest['session_mode'] | undefined {
  return raw === 'combined' || raw === 'c_only' ? raw : undefined;
}

export default function ComponentCPrepareRoute() {
  const params = useLocalSearchParams<{ grade?: string; sessionMode?: string }>();
  const sessionMode = parseSessionMode(params.sessionMode);

  const start = (challenge: ChallengeLength) => {
    // `replace`, not `push`: this screen is a fork in the road, not somewhere to come back to.
    // Leaving it on the stack would put the choice behind the game's own back gesture, where
    // returning to it would offer to re-choose a length for a run already under way.
    router.replace({
      params: {
        challenge,
        ...(params.grade === undefined ? {} : { grade: params.grade }),
        ...(sessionMode === undefined ? {} : { sessionMode }),
      },
      pathname: '/(learner)/c-session',
    });
  };

  // No cancel handler: the screen has no back control (owner request, 2026-10-20), so there is
  // nothing to hand one to. It was a route to home rather than a stack pop -- the prep card
  // arrives here with `replace`, so on a reload or a deep link there is no previous entry to
  // unwind to. If a way out is ever wanted again, that is the behaviour to restore.
  return <ChallengeChoiceScreen onStart={start} />;
}
