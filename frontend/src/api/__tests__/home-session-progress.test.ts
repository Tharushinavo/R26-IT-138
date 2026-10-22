import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  combineHomeSessionState,
  derivePathNodeStates,
  pathNodeLabel,
} from '@/src/features/home/session-progress';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

const ARTWORK_POSITIONS = 5; // what the illustration provides, not a session length

// --- node state derivation ------------------------------------------------------------------------

test('no active session still offers a way in: node 1 is current, the rest pending', () => {
  // This asserted all-pending until 2026-09-28, which left a child with no session -- the state
  // the panel resets to the moment they FINISH one -- looking at five inert circles with no play
  // control anywhere on the path. `current` is the only state the panel draws a play button for
  // and the only one it makes pressable, so all-pending was a dead end that forced a scroll back
  // up to the hero. Question 1 is genuinely what this learner plays next, so saying so is honest.
  const states = derivePathNodeStates({ kind: 'not-in-progress' }, ARTWORK_POSITIONS);
  assert.deepEqual(states, ['current', 'pending', 'pending', 'pending', 'pending']);
});

test('exactly one node is ever current, in every state', () => {
  // The play control is singular by construction: two current nodes would draw two play buttons
  // and leave the child choosing between them.
  const cases = [
    derivePathNodeStates({ kind: 'not-in-progress' }, ARTWORK_POSITIONS),
    derivePathNodeStates({ kind: 'in-progress', sessionId: 's', completed: 0, totalBound: 5 }, ARTWORK_POSITIONS),
    derivePathNodeStates({ kind: 'in-progress', sessionId: 's', completed: 3, totalBound: 5 }, ARTWORK_POSITIONS),
  ];
  for (const states of cases) {
    assert.equal(states.filter((node) => node === 'current').length, 1, JSON.stringify(states));
  }
});

test('a not-in-progress path with no artwork positions draws nothing rather than inventing a node', () => {
  assert.deepEqual(derivePathNodeStates({ kind: 'not-in-progress' }, 0), []);
});

test('completed N marks the first N done and the next current', () => {
  const state = { kind: 'in-progress', sessionId: 's1', completed: 2, totalBound: 5 } as const;
  assert.deepEqual(derivePathNodeStates(state, ARTWORK_POSITIONS), [
    'done',
    'done',
    'current',
    'pending',
    'pending',
  ]);
});

test('a session with nothing completed yet marks only the first node current', () => {
  const state = { kind: 'in-progress', sessionId: 's1', completed: 0, totalBound: 5 } as const;
  assert.deepEqual(derivePathNodeStates(state, ARTWORK_POSITIONS), [
    'current',
    'pending',
    'pending',
    'pending',
    'pending',
  ]);
});

test('a session with everything completed has no current node left', () => {
  const state = { kind: 'in-progress', sessionId: 's1', completed: 5, totalBound: 5 } as const;
  assert.deepEqual(derivePathNodeStates(state, ARTWORK_POSITIONS), [
    'done',
    'done',
    'done',
    'done',
    'done',
  ]);
});

// --- the node count follows the server's bound -------------------------------------------------------

test('the node count comes from opportunities_total_bound, not from a fixed five', () => {
  // The bound is an unapproved engineering placeholder; the client must follow whatever the server
  // reports. Three questions draw three nodes.
  const three = { kind: 'in-progress', sessionId: 's1', completed: 1, totalBound: 3 } as const;
  assert.deepEqual(derivePathNodeStates(three, ARTWORK_POSITIONS), ['done', 'current', 'pending']);

  const one = { kind: 'in-progress', sessionId: 's1', completed: 0, totalBound: 1 } as const;
  assert.deepEqual(derivePathNodeStates(one, ARTWORK_POSITIONS), ['current']);
});

test('a bound larger than the artwork degrades gracefully to what fits', () => {
  // The artwork has a fixed number of node positions. A bigger bound must render what fits rather
  // than overflow or break the layout — the panel's design is a hard constraint.
  const many = { kind: 'in-progress', sessionId: 's1', completed: 2, totalBound: 12 } as const;
  const states = derivePathNodeStates(many, ARTWORK_POSITIONS);
  assert.equal(states.length, ARTWORK_POSITIONS);
  assert.deepEqual(states, ['done', 'done', 'current', 'pending', 'pending']);
});

test('a completed count beyond the drawn nodes is clamped rather than producing gaps', () => {
  const overrun = { kind: 'in-progress', sessionId: 's1', completed: 99, totalBound: 5 } as const;
  assert.deepEqual(derivePathNodeStates(overrun, ARTWORK_POSITIONS), [
    'done',
    'done',
    'done',
    'done',
    'done',
  ]);
});

test('zero available positions produces no nodes rather than throwing', () => {
  assert.deepEqual(derivePathNodeStates({ kind: 'not-in-progress' }, 0), []);
});

// --- failure degrades to not-in-progress, never to an error ------------------------------------------

test('a missing active session yields not-in-progress', () => {
  assert.deepEqual(combineHomeSessionState(null, null), { kind: 'not-in-progress' });
});

test('a non-active session state yields not-in-progress', () => {
  const summary = { opportunities_completed: 2, opportunities_total_bound: 5 };
  for (const state of ['completed', 'abandoned', 'expired', 'technical_failed']) {
    assert.deepEqual(combineHomeSessionState({ session_id: 's1', state }, summary), {
      kind: 'not-in-progress',
    });
  }
});

test('a failed summary call yields not-in-progress rather than an error state', () => {
  // The screen passes null when the call throws. Showing "Start" to a learner who has a session open
  // is safe: POST /b/sessions returns the existing session, so the start path self-corrects.
  assert.deepEqual(combineHomeSessionState({ session_id: 's1', state: 'active' }, null), {
    kind: 'not-in-progress',
  });
});

test('malformed summary counts yield not-in-progress rather than a broken panel', () => {
  const session = { session_id: 's1', state: 'active' };
  for (const summary of [
    { opportunities_completed: 1.5, opportunities_total_bound: 5 },
    { opportunities_completed: -1, opportunities_total_bound: 5 },
    { opportunities_completed: 2, opportunities_total_bound: 0 },
    { opportunities_completed: Number.NaN, opportunities_total_bound: 5 },
  ]) {
    assert.deepEqual(combineHomeSessionState(session, summary), { kind: 'not-in-progress' });
  }
});

test('a valid active session and summary yield in-progress with the session id', () => {
  assert.deepEqual(
    combineHomeSessionState(
      { session_id: 'session-abc', state: 'active' },
      { opportunities_completed: 3, opportunities_total_bound: 5 },
    ),
    { kind: 'in-progress', sessionId: 'session-abc', completed: 3, totalBound: 5 },
  );
});

// --- labels are positional, never per-skill ------------------------------------------------------------

test('node labels are positional and name no skill', () => {
  assert.equal(pathNodeLabel(0, 'done'), 'Question 1, answered');
  assert.equal(pathNodeLabel(1, 'current'), 'Question 2, up next');
  assert.equal(pathNodeLabel(4, 'pending'), 'Question 5, not started');
});

// --- grep guards --------------------------------------------------------------------------------------

// Grep-as-a-test, same pattern as no-auth-bypass.test.ts. These are ugly on purpose and must not be
// deleted for being inelegant: each stands in for a claim the backend cannot support, and the only
// structural thing stopping it coming back is this file.
const HOME_SCREEN = 'src/features/home/learner-home-screen.tsx';
const PREP_SCREEN = 'src/features/session/session-preparation-screen.tsx';
const PROGRESS_LOGIC = 'src/features/home/session-progress.ts';

function source(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf-8');
}

test('neither screen presents hardcoded skill names as a lesson path', () => {
  // The server exposes no path, no ordering and no per-skill progress. Naming five skills as a
  // sequence of lessons asserted a structure that does not exist, and node 1 was labelled "Current
  // Lesson" regardless of what the learner was actually doing. The skill of a question IS shown —
  // per question, on the session screen, from the presentation's own skill_id.
  for (const path of [HOME_SCREEN, PREP_SCREEN]) {
    const text = source(path);
    for (const forbidden of [
      'componentBSkills',
      'Current Lesson',
      'On your path',
      'Number Sense',
      'Place Value',
    ]) {
      assert.equal(text.includes(forbidden), false, `${path} must not contain "${forbidden}"`);
    }
  }
});

test("neither screen greets a child by the placeholder name 'Yass'", () => {
  // It is a real person's name. Shipped as a fallback it means a child can be greeted as someone
  // else whenever their profile has not loaded.
  for (const path of [HOME_SCREEN, PREP_SCREEN]) {
    assert.equal(source(path).includes('Yass'), false, `${path} must not contain 'Yass'`);
  }
});

test('the prep screen makes no try-again promise', () => {
  // Attempt limits are Gate-B unresolved, so "You can try again / Learn at your own pace" was a
  // guarantee the app cannot make. (FE-3b does currently offer a retry, but the *policy* is not
  // settled, and a preparation screen promising it up front is a different claim from a retry
  // affordance appearing after an attempt.)
  const text = source(PREP_SCREEN);
  for (const forbidden of ['You can try again', 'Learn at your own pace']) {
    assert.equal(text.includes(forbidden), false, `prep screen must not contain "${forbidden}"`);
  }
});

test('the progress logic hardcodes no session length', () => {
  // The node count must follow opportunities_total_bound. This module holds all the derivation and
  // carries no styles, so a bare numeric-literal scan is meaningful here (unlike the screen, which
  // is full of legitimate layout numbers).
  const text = source(PROGRESS_LOGIC);
  assert.equal(/\b5\b/.test(text), false, 'session-progress.ts must not hardcode a session length');
  assert.equal(text.includes('MAX_OPPORTUNITIES'), false);
});

test('the home screen derives its node count rather than assuming the artwork is full', () => {
  // The artwork's node positions are a design fact; how many are DRAWN comes from the server. If the
  // screen ever maps over the positions array directly again, it would silently reintroduce
  // "always five questions".
  const text = source(HOME_SCREEN);
  assert.ok(text.includes('derivePathNodeStates'), 'home screen must derive node states');
  assert.equal(
    /PATH_NODE_POSITIONS\.map\(/.test(text),
    false,
    'home screen must not map the artwork positions directly — the count comes from the server',
  );
});

test('the home screen does not invent a first-time state', () => {
  // The server cannot distinguish a new learner from a returning one, and a device-local flag would
  // be wrong after a reinstall and wrong on a second device. One neutral not-in-progress state
  // covers both honestly; a cold-start distinction needs a backend endpoint.
  const text = source(HOME_SCREEN);
  for (const forbidden of ['hasPlayedBefore', 'firstTime', 'isFirstTime', 'firstVisit']) {
    assert.equal(text.includes(forbidden), false, `home screen must not contain "${forbidden}"`);
  }
});
