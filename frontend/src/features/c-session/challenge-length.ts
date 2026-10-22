// How long a Component C game run lasts, as chosen by the child before it starts.
//
// WHY THIS IS A CLIENT CHOICE AT ALL, and why it is honest to make one. Component C's contract
// carries NO session-length field: `CreateCSessionRequest` takes `grade` and `session_mode` and
// nothing else, and `POST /c/sessions/{id}/complete` is the client's own call to make. So a C
// session has never had an end -- it serves tasks for as long as it is asked, and today's app
// simply never asks it to stop (`completeSession` exists in component-c-api.ts and no screen has
// ever called it). That is what makes both options below real rather than decorative:
//
//   * ENDLESS is exactly today's behaviour, named. Nothing is faked and nothing is capped.
//   * CHALLENGE is the client deciding to stop asking after a fixed number of tasks and then
//     completing the session through the endpoint that already exists for it.
//
// Neither option is a request to the engine to behave differently, and neither claims the engine
// supports a length it does not. If a governed session length is ever added to the C contract,
// this module is what it replaces.
//
// CONTRAST WITH COMPONENT B, where the same feature would NOT be honest. `POST /b/sessions` takes
// no request body at all, and the session ends when the server's own
// `opportunities_total_bound` is reached -- a bound live-session-logic.ts describes as "an
// unapproved engineering placeholder, not a governed session length". A client cannot extend past
// it, so "endless" is unimplementable there, and a client-side stop short of it would be inventing
// a length the server did not sanction. This choice is offered on the C path only.

/** The two run lengths a child can pick. */
export const CHALLENGE_LENGTHS = ['challenge', 'endless'] as const;

export type ChallengeLength = (typeof CHALLENGE_LENGTHS)[number];

/**
 * How many tasks a `challenge` run lasts.
 *
 * TEN, because the child was told ten. This number appears on the choice screen as a promise and
 * is the only thing that may fulfil it -- nothing else in the app may count to a different number
 * and call it the same run.
 */
export const CHALLENGE_TASK_COUNT = 10;

/** The default when no choice reached the screen (a deep link, a reload). Endless is the safer
 * fallback of the two: it is the behaviour that existed before this choice did, so defaulting to
 * it cannot cut a run short on a child who never chose anything. */
export const DEFAULT_CHALLENGE_LENGTH: ChallengeLength = 'endless';

/** Validates a route param rather than trusting it. Anything unrecognised becomes the default,
 * never an error surfaced to a child and never a crash. */
export function parseChallengeLength(raw: string | undefined): ChallengeLength {
  return CHALLENGE_LENGTHS.includes(raw as ChallengeLength)
    ? (raw as ChallengeLength)
    : DEFAULT_CHALLENGE_LENGTH;
}

/** The task cap for a run, or `null` for endless. `null` rather than `Infinity` so a caller that
 * forgets to handle it fails loudly at the type level instead of silently comparing against a
 * number no count can ever reach. */
export function taskCapFor(length: ChallengeLength): number | null {
  return length === 'challenge' ? CHALLENGE_TASK_COUNT : null;
}

/**
 * Whether a run that has completed `completedTasks` tasks is over.
 *
 * `>=` rather than `===` deliberately: a resumed session can rejoin with a count already past the
 * cap, and such a run must end rather than play on forever because it missed the exact value.
 */
export function isRunComplete(length: ChallengeLength, completedTasks: number): boolean {
  const cap = taskCapFor(length);
  return cap !== null && completedTasks >= cap;
}

/**
 * One finished game in a run, as the completion card lists it.
 *
 * TIME, NOT A MARK -- and the reason is structural, not a preference. Component C lets a child
 * RETRY a wrong answer on the same task until they get it, and the session only advances once the
 * answer matches. So every finished task was eventually answered correctly: a correct/incorrect
 * column would be a tick on all ten, every run, for every child, and would say nothing at all.
 *
 * What does vary is how long each one took. `ms` runs from the moment the question is on screen to
 * the moment the answer is accepted, so wrong attempts are INCLUDED -- a question that took three
 * goes shows as the time all three goes took, which is the honest reading of "how did that one
 * go" once correctness cannot distinguish anything.
 */
export type ChallengeRunResult = {
  /** The game's display name, from `nameForGameFamily`. Never invented here. */
  name: string;
  /** Milliseconds from the question appearing to the answer being accepted. */
  ms: number;
};

/**
 * `m:ss`, the only format this app shows a duration in.
 *
 * Minutes are NOT capped at 59 and there is no hour field: a single question is not going to run
 * past an hour, and a bogus clock reading is better shown as an absurd number of minutes than
 * silently folded into a wrong-looking small one. Negative and non-finite inputs floor to zero --
 * a clock that went backwards (a device time change mid-question) must not render "-1:-3".
 */
export function formatDuration(ms: number): string {
  const safe = Number.isFinite(ms) && ms > 0 ? ms : 0;
  const totalSeconds = Math.floor(safe / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

/** The run's total, summed from the rows rather than timed separately -- so the total can never
 * disagree with the list above it. */
export function totalDurationMs(results: readonly ChallengeRunResult[]): number {
  return results.reduce((sum, result) => sum + (Number.isFinite(result.ms) ? result.ms : 0), 0);
}
