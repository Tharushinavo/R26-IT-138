// Pre-advance coverage for BOTH verdicts, without taking TRY AGAIN away (owner instruction,
// 2026-10-10).
//
// THE CONSTRAINT THIS IS SHAPED BY. A wrong answer keeps TRY AGAIN, and TRY AGAIN needs the
// current opportunity to stay OPEN. The next question therefore cannot be fetched in advance --
// not as an API preference but as a database rule:
//
//   CREATE UNIQUE INDEX uq_b_item_opportunities_one_open_per_session
//     ON b_item_opportunities (session_id) WHERE state = 'OPEN'
//
// One open opportunity per session, so the next cannot exist while this one does. "Cache both" is
// impossible while the retry affordance stays.
//
// What IS available is the gap between finger-down and lift-off on "Next question". These pin
// that, and pin that TRY AGAIN is untouched.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const SCREEN = 'src/features/session/live-session-screen.tsx';
const source = readFileSync(SCREEN, 'utf8');

test('a terminal verdict still pre-advances as soon as it lands', () => {
  // Correct / timed out: no TRY AGAIN, nothing to protect, so the fetch starts immediately -- the
  // earliest the server permits, since `complete` 409s until an attempt is recorded.
  assert.match(
    source,
    /if \(outcome === null \|\| outcomeView\(outcome\)\.canTryAgain\) return;\s*\n\s*primeAdvance\(\);/,
    'the effect must still fire for non-retryable outcomes only',
  );
});

test('a wrong answer starts the fetch on finger-down instead', () => {
  assert.match(source, /onPressIn=\{primeAdvanceOnIntent\}/, 'Next question must prime on press-in');
  assert.match(source, /const primeAdvanceOnIntent = useCallback\(/);
});

test('both paths share one request, so a press cannot duplicate the pre-advance', () => {
  // Both call `primeAdvance`, which is keyed by opportunity id -- a second call for the same
  // question is a no-op rather than a second `complete`.
  const fn = source.slice(source.indexOf('const primeAdvance = useCallback'), source.indexOf('const primeAdvanceOnIntent'));
  assert.match(
    fn,
    /if \(advancePrefetchRef\.current\?\.itemOpportunityId === itemOpportunityId\) return;/,
    'priming must be idempotent per opportunity',
  );
});

test('TRY AGAIN is still offered on a wrong answer, and sends nothing', () => {
  // The whole point of the compromise: the retry affordance survives. `tryAgain` is local-only --
  // if the child takes it, `complete` was never sent and the opportunity is still open.
  assert.match(source, /view\?\.canTryAgain \? <PrimaryButton label="TRY AGAIN" onPress=\{tryAgain\} \/> : null/);
  const fn = source.slice(source.indexOf('const tryAgain = useCallback'), source.indexOf('const tryAgain = useCallback') + 400);
  assert.doesNotMatch(fn, /api\.|sendAdvance|withToken/, 'TRY AGAIN must make no network call');
});
