// The Component C run-length choice (owner request): "10 Game Challenge" or "Keep Playing".
//
// These tests pin the two things that make the choice HONEST rather than decorative — that an
// endless run is uncapped, and that a fixed run ends at exactly the number the child was promised
// — plus the fail-safe behaviour on a value that never came from the choice screen.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  CHALLENGE_TASK_COUNT,
  DEFAULT_CHALLENGE_LENGTH,
  formatDuration,
  isRunComplete,
  parseChallengeLength,
  taskCapFor,
  totalDurationMs,
} from '@/src/features/c-session/challenge-length';

test('an endless run has no cap, and never completes on its own', () => {
  assert.equal(taskCapFor('endless'), null);
  assert.equal(isRunComplete('endless', 0), false);
  assert.equal(isRunComplete('endless', CHALLENGE_TASK_COUNT), false);
  assert.equal(isRunComplete('endless', 10_000), false);
});

test('a challenge run ends at exactly the number the child was promised', () => {
  assert.equal(taskCapFor('challenge'), CHALLENGE_TASK_COUNT);
  assert.equal(isRunComplete('challenge', CHALLENGE_TASK_COUNT - 1), false, 'not one task early');
  assert.equal(isRunComplete('challenge', CHALLENGE_TASK_COUNT), true);
});

test('a count already past the cap still ends the run', () => {
  // `>=`, not `===`. A resumed session can rejoin with a count beyond the cap, and such a run has
  // to end rather than play on forever because it stepped over the exact value.
  assert.equal(isRunComplete('challenge', CHALLENGE_TASK_COUNT + 3), true);
});

test('an unrecognised route param falls back to the default, never an error', () => {
  // A hand-typed URL, a stale link, or a reload with no param at all. None of these may crash or
  // show a child an error; they play.
  for (const raw of [undefined, '', 'infinite', '10', 'CHALLENGE', 'null']) {
    assert.equal(parseChallengeLength(raw), DEFAULT_CHALLENGE_LENGTH);
  }
  assert.equal(parseChallengeLength('challenge'), 'challenge');
  assert.equal(parseChallengeLength('endless'), 'endless');
});

test('the default is endless -- the behaviour that existed before the choice did', () => {
  // Defaulting to the fixed run would cut a session short on a child who never chose anything.
  assert.equal(DEFAULT_CHALLENGE_LENGTH, 'endless');
});


/** Strips whole-line `//` comments, so a guard matches CODE rather than prose about the code --
 * the same trap three of this codebase's other source-scanning guards have been caught by. */
function withoutComments(source: string): string {
  const newline = String.fromCharCode(10);
  return source
    .split(newline)
    .filter((line) => !line.trim().startsWith('//'))
    .join(newline);
}

// --- structural guards --------------------------------------------------------------------------

test('the promised number has ONE source', () => {
  // The choice screen tells the child a number and the run must honour that same number. A second
  // literal anywhere in the pair is how those two drift apart.
  const screen = readFileSync('src/features/c-session/challenge-choice-screen.tsx', 'utf8');
  assert.match(screen, /CHALLENGE_TASK_COUNT/, 'the screen must render the shared constant');
  assert.doesNotMatch(
    screen.replace(/\/\/[^\n]*/g, ''),
    /\b10\b/,
    'the screen must not hardcode the count',
  );
});

test('the run is capped by the shared rule, not by a comparison written at the call site', () => {
  const screen = readFileSync('src/features/c-session/c-session-screen.tsx', 'utf8');
  assert.match(screen, /isRunComplete\(challenge, completed\)/);
});

test('ending a run completes the session rather than abandoning it', () => {
  // `abandonSession` exists and is the wrong call: a run the child played to the end is attended,
  // and recording it as abandoned would misreport it in every downstream count.
  const screen = readFileSync('src/features/c-session/c-session-screen.tsx', 'utf8');
  assert.match(screen, /completeSession\(cSessionId, \{ attendance_status: 'attended' \}/);
});

test('the clock starts when the question is SHOWN, not when it was fetched', () => {
  // The first task is pre-fetched while the prep card is still up. Timing from the request would
  // bill the child for a wait they never saw.
  const screen = readFileSync('src/features/c-session/c-session-screen.tsx', 'utf8');
  assert.match(screen, /currentTaskStartedAtRef\.current = Date\.now\(\);/);
  assert.match(
    screen,
    /recordTaskStarted\(\);[\s\S]{0,600}?currentTaskStartedAtRef\.current = Date\.now\(\);/,
    'the clock must start where the task is presented',
  );
});

test('a WRONG answer does not stop the clock', () => {
  // The whole point of timing rather than marking: the child stays on the same task and tries
  // again, so the question is not over. Only an accepted answer ends it, and the time then covers
  // every attempt it took. A clock stopped on any submission would report the first guess.
  const screen = readFileSync('src/features/c-session/c-session-screen.tsx', 'utf8');
  assert.match(
    screen,
    /if \(outcome\.kind === 'advance'\) \{\s*acceptedElapsedMsRef\.current = Date\.now\(\) - currentTaskStartedAtRef\.current;/,
    'only an accepted answer may stop the clock',
  );
  assert.doesNotMatch(
    withoutComments(screen),
    /outcome\.kind !== 'advance'/,
    'nothing may key off a wrong answer to end the question',
  );
});

test('the completion list is built in play order, one row per finished game', () => {
  const screen = readFileSync('src/features/c-session/c-session-screen.tsx', 'utf8');
  // Appended, never keyed by skill or sorted: the child played them in an order and the card
  // retells that order.
  assert.match(screen, /runResultsRef\.current = \[\s*\.\.\.runResultsRef\.current,/);
});

test('a duration renders as m:ss, with seconds always two digits', () => {
  assert.equal(formatDuration(0), '0:00');
  assert.equal(formatDuration(1_000), '0:01');
  assert.equal(formatDuration(9_500), '0:09', 'part-seconds floor, never round up');
  assert.equal(formatDuration(65_000), '1:05');
  assert.equal(formatDuration(600_000), '10:00');
});

test('a broken clock renders as zero rather than a negative time', () => {
  // A device clock change mid-question can produce a negative elapsed value. "-1:-3" in front of
  // a child is worse than an understated zero.
  assert.equal(formatDuration(-5_000), '0:00');
  assert.equal(formatDuration(Number.NaN), '0:00');
  assert.equal(formatDuration(Number.POSITIVE_INFINITY), '0:00');
});

test('the total is the sum of the rows, so the two can never disagree', () => {
  const rows = [
    { ms: 4_000, name: 'A' },
    { ms: 6_500, name: 'B' },
  ];
  assert.equal(totalDurationMs(rows), 10_500);
  assert.equal(totalDurationMs([]), 0);
  // One bad row must not poison the whole total.
  assert.equal(totalDurationMs([{ ms: Number.NaN, name: 'A' }, { ms: 3_000, name: 'B' }]), 3_000);
});
