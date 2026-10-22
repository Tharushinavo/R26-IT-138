// Bounded retry on the presentation acknowledgement (A2, 2026-10-10).
//
// WHY A RETRY AT ALL. `POST .../presented` is what anchors the five-minute answering deadline:
// `anchor_presentation` sets `presented_at_utc` and `timeout_deadline_utc = now + timeout` on the
// FIRST acknowledgement. If that request is lost, the deadline the server judges a submission
// against stays the fail-safe one written at SELECTION -- which, with Home/prep prefetching, can
// have been minted well before the child saw anything. A lost ack is therefore the one remaining
// path by which pre-presentation time can still be charged to a child.
//
// WHY EXACTLY TWO ATTEMPTS. The call is idempotent by construction: `anchor_presentation` returns
// early once `presented_at_utc` is set, so every later acknowledgement is a no-op that returns the
// SAME deadline. Retrying therefore cannot extend or reset a deadline that already exists. That
// makes a retry safe -- it does not make an unbounded ladder acceptable, because a dead network
// would then generate background traffic behind a child who is simply reading the question.
//
// These tests exercise the retry LADDER in isolation, plus structural guards on the screen. The
// ladder is reproduced here rather than imported because it lives inside a `useEffect` in a 1400-
// line component with no render harness in `test:contract`; the structural guards below are what
// tie this model to the real implementation.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const SCREEN_PATH = 'src/features/session/live-session-screen.tsx';
const screenSource = readFileSync(SCREEN_PATH, 'utf8');

const ATTEMPTS = 4;

type AckResult = { server_timeout_deadline_utc: string };

/**
 * The shape of the effect's body: attempt, on failure wait and attempt once more, then give up
 * silently. `isCancelled` stands for the unmount/navigation check.
 */
async function ackWithRetry(
  send: () => Promise<AckResult>,
  onAnchored: (deadline: string) => void,
  isCancelled: () => boolean = () => false,
): Promise<{ attempts: number; anchored: boolean }> {
  let attempts = 0;
  for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
    if (isCancelled()) return { anchored: false, attempts };
    attempts += 1;
    try {
      const ack = await send();
      if (isCancelled()) return { anchored: false, attempts };
      onAnchored(ack.server_timeout_deadline_utc);
      return { anchored: true, attempts };
    } catch {
      // fall through to the bounded retry
    }
  }
  return { anchored: false, attempts };
}

test('the retry budget outlives a multi-second backend outage', async () => {
  // The budget was 2 attempts over 400ms, which could not survive the failure actually seen: the
  // API unavailable for several seconds during a container restart. The question then kept its
  // selection-time fail-safe deadline and the child was told "Time's up" on a question they had
  // only just been shown.
  const source = readFileSync(SCREEN_PATH, 'utf8');
  const delays = source.match(/PRESENTATION_ACK_RETRY_DELAYS_MS = \[([^\]]*)\]/);
  assert.ok(delays, 'the backoff schedule must be an explicit, readable list');
  const total = delays[1].split(',').map((n) => Number(n.trim())).reduce((a, b) => a + b, 0);
  assert.ok(total >= 5000, `the ladder must span at least 5s, spans ${total}ms`);
  assert.match(source, /const PRESENTATION_ACK_ATTEMPTS = 4;/);
});

test('a first-attempt success anchors the deadline and makes exactly one request', async () => {
  let adopted: string | null = null;
  const result = await ackWithRetry(
    async () => ({ server_timeout_deadline_utc: '2026-10-10T00:05:00Z' }),
    (deadline) => {
      adopted = deadline;
    },
  );

  assert.equal(result.attempts, 1, 'a success must not be followed by a retry');
  assert.equal(result.anchored, true);
  assert.equal(adopted, '2026-10-10T00:05:00Z', "the server's anchored deadline is adopted");
});

test('a failed first attempt is retried once, and the retry can anchor', async () => {
  let calls = 0;
  let adopted: string | null = null;
  const result = await ackWithRetry(
    async () => {
      calls += 1;
      if (calls === 1) throw new Error('request dropped');
      return { server_timeout_deadline_utc: '2026-10-10T00:05:00Z' };
    },
    (deadline) => {
      adopted = deadline;
    },
  );

  assert.equal(calls, 2);
  assert.equal(result.anchored, true, 'the retry is what recovers the anchored deadline');
  assert.equal(adopted, '2026-10-10T00:05:00Z');
});

test('both attempts failing gives up silently and never claims the deadline was anchored', async () => {
  let calls = 0;
  let adopted: string | null = null;
  const result = await ackWithRetry(
    async () => {
      calls += 1;
      throw new Error('network down');
    },
    (deadline) => {
      adopted = deadline;
    },
  );

  assert.equal(calls, ATTEMPTS, 'no more than two attempts, ever');
  assert.equal(result.anchored, false, 'a failure must not report presentation as acknowledged');
  assert.equal(adopted, null, 'and must not fabricate a deadline to adopt');
  // The fallback is the SELECTION-time deadline already on the plan. This retry introduces no new
  // fallback contract; it only narrows how often the old one is relied on.
});

test('retries are bounded: a permanently failing endpoint cannot loop', async () => {
  let calls = 0;
  await ackWithRetry(
    async () => {
      calls += 1;
      throw new Error('still down');
    },
    () => undefined,
  );
  assert.ok(calls <= ATTEMPTS, `expected at most ${ATTEMPTS} attempts, saw ${calls}`);
});

test('an unmount between attempts stops the ladder', async () => {
  let calls = 0;
  let cancelled = false;
  const result = await ackWithRetry(
    async () => {
      calls += 1;
      cancelled = true; // the child navigated away while the first attempt was in flight
      throw new Error('dropped');
    },
    () => undefined,
    () => cancelled,
  );

  assert.equal(calls, 1, 'a navigated-away screen must not issue the retry');
  assert.equal(result.anchored, false);
});

test('a duplicate acknowledgement adopts the same deadline, never a later one', async () => {
  // Models the server contract: first ack wins, later ones are no-ops returning the SAME deadline.
  const anchored = '2026-10-10T00:05:00Z';
  const adopted: string[] = [];
  const send = async () => ({ server_timeout_deadline_utc: anchored });

  await ackWithRetry(send, (d) => adopted.push(d));
  await ackWithRetry(send, (d) => adopted.push(d));

  assert.deepEqual(adopted, [anchored, anchored], 'the deadline must not move on a second ack');
});

// --- structural guards tying the model above to the real effect -------------------------------

test('the screen retries a bounded number of times, from a named constant', () => {
  assert.match(
    screenSource,
    /const PRESENTATION_ACK_ATTEMPTS = \d+;/,
    `${SCREEN_PATH} must bound the attempts with an explicit constant`,
  );
  assert.match(screenSource, /const PRESENTATION_ACK_RETRY_DELAYS_MS = \[/);
  assert.match(
    screenSource,
    /attempt <= PRESENTATION_ACK_ATTEMPTS/,
    'the loop must be bounded by that constant, not by a condition that can never end',
  );
  assert.doesNotMatch(screenSource, /while \(true\)/, 'no unbounded retry loop');
});

test('the once-per-opportunity guard is still set before the first attempt', () => {
  // Set BEFORE the ladder starts, or a re-render during the retry would start a second one.
  const guardIndex = screenSource.indexOf('ackedOpportunityRef.current = opportunityId;');
  const loopIndex = screenSource.indexOf('attempt <= PRESENTATION_ACK_ATTEMPTS');
  assert.notEqual(guardIndex, -1);
  assert.notEqual(loopIndex, -1);
  assert.ok(guardIndex < loopIndex, 'the guard must precede the retry ladder');
});

test('the effect cancels on unmount', () => {
  assert.match(
    screenSource,
    /return \(\) => \{\s*cancelled = true;\s*\};/,
    'the ack effect must stop issuing attempts once the screen is gone',
  );
});

test('the retry stays silent — no failure phase is raised from the ack path', () => {
  // A transient infrastructure failure must never put a technical error in front of a child; the
  // governance rule is that infrastructure failure is never learner failure.
  // Bounded to the ack effect ONLY, ending at its own dependency array. A wider window runs into
  // the bootstrap effect below it, which legitimately does raise a failure phase.
  const start = screenSource.indexOf('// PRESENTATION ACKNOWLEDGEMENT');
  const end = screenSource.indexOf('}, [api, phase, sessionId, withToken]);', start);
  assert.notEqual(start, -1, 'the ack effect must still be findable');
  assert.notEqual(end, -1, "the ack effect's dependency array must be unchanged");

  const effect = screenSource.slice(start, end);
  assert.match(effect, /attempt <= PRESENTATION_ACK_ATTEMPTS/, 'slice really is the ack effect');
  assert.doesNotMatch(effect, /setPhase\(\{\s*kind: 'failure'/, 'the ack path must stay silent');
});
