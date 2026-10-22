// The re-entry guard around `submit_action`, proven at the level the guard actually lives:
// `createSubmitGate` is the synchronous cell `c-session-screen.tsx` holds in a `useRef` and takes
// before its first `await` in `submitFromSurface`.
//
// WHAT THIS PROTECTS, and what it deliberately does NOT replace. The backend refuses a second
// submission on a terminated instance with `task_already_terminal` (`task_service.py:573-576`),
// a 409 that `classifySessionFailure` routes to the technical-block screen. That refusal is the
// authority and is untouched by this batch -- these tests assert the CLIENT stops asking twice,
// never that the server stopped caring. If every assertion here were deleted, the backend would
// still refuse the duplicate; the child would simply see "Something changed on our end" for it.
//
// Why a same-frame race is the case under test rather than a slow double-tap: React `setState` is
// asynchronous and batched, so two taps dispatched in one frame both observe the pre-update flag.
// A `useState`-based guard passes a naive sequential test and fails exactly this one, which is why
// the gate is a plain closure over a mutable cell and why `tryEnter` is tested re-entrantly rather
// than only in sequence.

import assert from 'node:assert/strict';
import test from 'node:test';

import { createSubmitGate } from '@/src/features/c-session/c-session-logic';

test('the first caller enters and the second is refused while it is still in flight', () => {
  const gate = createSubmitGate();

  assert.equal(gate.tryEnter(), true, 'the first submission must be allowed through');
  assert.equal(gate.tryEnter(), false, 'a second submission must be refused while one is open');
  assert.equal(gate.tryEnter(), false, 'and every further attempt, not just the second');
});

test('releasing reopens the gate for the next task', () => {
  const gate = createSubmitGate();

  assert.equal(gate.tryEnter(), true);
  gate.release();
  assert.equal(gate.tryEnter(), true, 'a released gate must admit the next genuine submission');
});

test('isBusy reports the gate state without consuming it', () => {
  const gate = createSubmitGate();

  assert.equal(gate.isBusy(), false);
  gate.tryEnter();
  assert.equal(gate.isBusy(), true, 'the overlay reads this to render');
  // The render mirror must not itself claim the gate -- if `isBusy` consumed it, reading it to
  // draw the indicator would lock out the real submission.
  gate.release();
  assert.equal(gate.isBusy(), false);
  assert.equal(gate.tryEnter(), true);
});

test('gates are independent per instance, so one screen cannot block another', () => {
  const a = createSubmitGate();
  const b = createSubmitGate();

  assert.equal(a.tryEnter(), true);
  assert.equal(b.tryEnter(), true, 'a second screen must not inherit the first screen\'s gate');
});

// The behavioural test: a submit function shaped exactly like `submitFromSurface` -- gate taken
// before the first await, released in `finally` -- driven by two concurrent callers, asserting the
// network call happened once. This is the property the screen actually needs; the unit tests above
// only establish the mechanism it rests on.
test('two concurrent submissions produce exactly one network call', async () => {
  const gate = createSubmitGate();
  const submitted: string[] = [];
  let releaseInFlight: (() => void) | null = null;

  const submitFromSurface = async (value: string) => {
    if (!gate.tryEnter()) return;
    try {
      // Stands in for `await getAccessToken()` -- the suspension point a guard taken any later
      // than this would fail to cover.
      await new Promise<void>((resolve) => {
        releaseInFlight = resolve;
      });
      submitted.push(value);
    } finally {
      gate.release();
    }
  };

  const first = submitFromSurface('first-tap');
  const second = submitFromSurface('second-tap');

  assert.equal(submitted.length, 0, 'neither call has resolved yet');
  releaseInFlight!();
  await Promise.all([first, second]);

  assert.deepEqual(submitted, ['first-tap'], 'only the first tap may reach submitAction');
});

test('a submission that throws still releases the gate', async () => {
  const gate = createSubmitGate();

  const failing = async () => {
    if (!gate.tryEnter()) return;
    try {
      await Promise.reject(new Error('network died'));
    } catch {
      // `handleSubmit` routes its own failures rather than rethrowing; the shape that matters here
      // is that the `finally` runs either way.
    } finally {
      gate.release();
    }
  };

  await failing();

  assert.equal(gate.isBusy(), false, 'a failed submission must not leave SUBMIT permanently dead');
  assert.equal(gate.tryEnter(), true, 'the child must be able to try again after a failure');
});
