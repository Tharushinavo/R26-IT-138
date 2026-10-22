// Thin route boundary for the Component C session shell. Static, not a dynamic segment like B's
// `session/[sessionId].tsx` -- Component C's `createSession` takes only a request body and
// `getActiveSession` takes only a token (component-c-api.ts), so there is no externally supplied
// session id for a route param to carry. A [cSessionId] segment here would be a parameter nothing
// ever fills, the same shape as the idempotency-key header 10.0a's builder found and did not add.
//
// `grade` and `sessionMode` are read as optional query params, validated rather than trusted, and
// passed straight through -- this route invents neither. No entry point from home.tsx is wired
// here; that is a B screen and out of this batch's scope.

import { useLocalSearchParams } from 'expo-router';

import type { CreateCSessionRequest } from '@/src/api/generated/openapi-types';
import { CSessionScreen } from '@/src/features/c-session/c-session-screen';
import { parseChallengeLength } from '@/src/features/c-session/challenge-length';

function parseGrade(raw: string | undefined): number | undefined {
  if (raw === undefined) return undefined;
  const parsed = Number(raw);
  return Number.isInteger(parsed) ? parsed : undefined;
}

function parseSessionMode(raw: string | undefined): CreateCSessionRequest['session_mode'] | undefined {
  return raw === 'combined' || raw === 'c_only' ? raw : undefined;
}

export default function ComponentCSessionRoute() {
  // `challenge` arrives from c-prepare.tsx and is validated there and again here -- an
  // unrecognised value becomes the default rather than an error, so a hand-typed or stale URL
  // still plays.
  const params = useLocalSearchParams<{ challenge?: string; grade?: string; sessionMode?: string }>();
  return (
    <CSessionScreen
      challenge={parseChallengeLength(params.challenge)}
      grade={parseGrade(params.grade)}
      sessionMode={parseSessionMode(params.sessionMode)}
    />
  );
}
