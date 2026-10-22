// c-session-screen.tsx must key its <Surface> on the task instance, so React remounts the surface
// for every new task instead of reconciling a new task into the old component instance.
//
// WHY THIS IS A CORRECTNESS GUARD AND NOT A STYLE ONE. Every archetype surface keeps the child's
// in-progress answer in its own local state (10a's ordered-value-sequence holds `entryValues` and
// `order`), and none of it is derived from the task prop. Same element type in the same position
// with no key means React keeps the instance and swaps the prop, so the previous question's
// already-entered answer is still sitting in the input when the next question appears -- and can be
// submitted against it without ever being re-entered. Keying on the instance id makes the discard a
// consequence of mounting rather than a second mechanism that could itself be forgotten.
//
// WHAT THIS FILE CANNOT DO, STATED PLAINLY. It does not observe the remount. This project has no
// rendering library in devDependencies, so no test here can mount a component tree, drive a submit,
// and assert the input cleared. What is proven below is strictly that the source binds a key to a
// task-identifying wire field. That React remounts on a changed key is React's documented
// behaviour, relied on here and NOT verified by this project. The behavioural half remains
// unverified, and is a supervisor observation to make in a browser, not a claim this file supports.
//
// EXTENDED for the retry loop: the key is now `` `${task.c_task_instance_id}:${attempt}` ``, not
// `task.c_task_instance_id` alone. Combining with `attempt` closes the identical gap one level
// down -- a WRONG answer may be resubmitted on the same instance id without limit (the backend
// writes no terminal event on that path), so a key bound to the instance id alone would not change
// between attempts on one task, and the answer_feedback_panel's "Try again" would remount nothing:
// the previous, wrong entry would still be sitting in the surface. The predicate below now extracts
// the key as a full expression (handling the template-literal shape, not just a bare member
// expression) and a second predicate confirms `attempt` is actually part of it -- both are required
// for the guard to mean what this file claims.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const screenPath = resolve(here, '..', '..', 'features', 'c-session', 'c-session-screen.tsx');
const generatedTypesPath = resolve(here, '..', 'generated', 'openapi-types.ts');

/**
 * Comments stripped before any scan. The fix's own JSX comment explains the key at length and names
 * both `key` and `c_task_instance_id`, so a guard reading raw bytes would pass on a file whose
 * comment merely discusses the key while the element carries none -- the comment-stripping trap the
 * build-steps doc records this project hitting at least four times.
 */
function strippedSource(text: string): string {
  return text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

/**
 * The raw text of a `<Surface ... />` element's `key={...}` expression (everything between the
 * outer braces, brace-balanced so a nested `${...}` template expression does not truncate the
 * match early), or `null` if there is no Surface element or no `key` attribute on it at all.
 */
function keyExpressionOfSurfaceElement(elementSource: string): string | null {
  const marker = elementSource.match(/\bkey=\{/);
  if (!marker || marker.index === undefined) return null;
  let index = marker.index + marker[0].length;
  let depth = 1;
  const start = index;
  while (index < elementSource.length && depth > 0) {
    if (elementSource[index] === '{') depth += 1;
    else if (elementSource[index] === '}') depth -= 1;
    index += 1;
  }
  if (depth !== 0) return null; // unbalanced -- malformed source, not a key this guard can trust
  return elementSource.slice(start, index - 1);
}

/**
 * The task-field name a `<Surface ... />` element's `key` expression references (via a bare
 * `task.<field>` member expression appearing ANYWHERE inside the key, so both
 * `key={task.c_task_instance_id}` and `` key={`${task.c_task_instance_id}:${attempt}`} `` are
 * recognised), or `null` when there is no Surface element, no key on it, or the key references no
 * `task.<field>` at all -- a string literal, a number, a loop index, or a bare call yield `null`.
 *
 * This is the primary predicate under test. The real file and every negative control below run
 * through it, so the controls exercise the guard itself rather than a lookalike of it.
 */
export function keyFieldOfSurfaceElement(source: string): string | null {
  const element = strippedSource(source).match(/<Surface\b[^>]*\/>/);
  if (!element) return null;

  const keyExpr = keyExpressionOfSurfaceElement(element[0]);
  if (keyExpr === null) return null;

  const key = keyExpr.match(/\btask\.([A-Za-z_][A-Za-z0-9_]*)\b/);
  return key ? key[1] : null;
}

/**
 * Whether a `<Surface ... />` element's `key` expression ALSO references the retry attempt count
 * (a bare `attempt` identifier), independent of which task field it uses. `false` for every shape
 * `keyFieldOfSurfaceElement` itself would call `null` on, and for a key bound to the task field
 * alone with no attempt component -- the exact pre-retry shape this guard exists to catch.
 */
export function keyIncludesAttempt(source: string): boolean {
  const element = strippedSource(source).match(/<Surface\b[^>]*\/>/);
  if (!element) return false;

  const keyExpr = keyExpressionOfSurfaceElement(element[0]);
  if (keyExpr === null) return false;

  return /\battempt\b/.test(keyExpr);
}

// Fields that are present on a task but provably REPEAT across consecutive tasks, so a key bound to
// one of them would not change between questions and would therefore not remount -- the exact bug
// this batch fixes, reintroduced under the appearance of a key. A template id in particular repeats
// for every task drawn from the same template.
const NON_IDENTIFYING_FIELDS = [
  'game_task_template_id',
  'game_family_id',
  'skill_id',
  'representation_mode',
  'scaffold_state',
  'prompt_text',
];

test('the Surface element carries a key bound to a task field', () => {
  const field = keyFieldOfSurfaceElement(readFileSync(screenPath, 'utf8'));
  assert.notEqual(field, null, 'c-session-screen.tsx renders <Surface> with no task-bound key');
});

test('the key is bound to a field that actually exists on the wire response', () => {
  const field = keyFieldOfSurfaceElement(readFileSync(screenPath, 'utf8'));
  const generated = readFileSync(generatedTypesPath, 'utf8');
  // Declared as a required string in the generated contract types -- so the key is bound to a real
  // registry field, not to a name invented in the screen.
  assert.match(
    generated,
    new RegExp(`"${field}":\\s*string;`),
    `${field} is not a required string on the generated contract types`,
  );
});

test('the key is not bound to a field that repeats across tasks', () => {
  const field = keyFieldOfSurfaceElement(readFileSync(screenPath, 'utf8'));
  assert.ok(
    field !== null && !NON_IDENTIFYING_FIELDS.includes(field),
    `${field} repeats across consecutive tasks, so keying on it would not remount the surface`,
  );
});

// ---------------------------------------------------------------------------
// Negative controls. The guard must go RED on each of these, or it proves nothing about the real
// file. A guard exercised in only the passing direction is not a guard.
// ---------------------------------------------------------------------------

test('the guard fires on a Surface element with no key at all -- the pre-fix shape', () => {
  assert.equal(
    keyFieldOfSurfaceElement('<Surface onSubmit={submitFromSurface} task={task} />'),
    null,
  );
});

test('the guard fires on a key bound to a constant, an index, or a call', () => {
  assert.equal(keyFieldOfSurfaceElement('<Surface key="surface" task={task} />'), null);
  assert.equal(keyFieldOfSurfaceElement('<Surface key={0} task={task} />'), null);
  assert.equal(keyFieldOfSurfaceElement('<Surface key={index} task={task} />'), null);
  assert.equal(keyFieldOfSurfaceElement('<Surface key={"literal"} task={task} />'), null);
  assert.equal(keyFieldOfSurfaceElement('<Surface key={makeKey(task)} task={task} />'), null);
});

test('the guard fires when a comment merely discusses the key but the element carries none', () => {
  const commentOnly = [
    '/* keyed on key={task.c_task_instance_id} so the surface remounts */',
    '// key={task.c_task_instance_id}',
    '<Surface onSubmit={submitFromSurface} task={task} />',
  ].join('\n');
  assert.equal(keyFieldOfSurfaceElement(commentOnly), null);
});

test('the guard fires when there is no Surface element at all', () => {
  assert.equal(keyFieldOfSurfaceElement('const a = 1;'), null);
});

// The positive control: the same predicate must RECOGNISE a correctly keyed element. Without this,
// a predicate that returned null unconditionally would satisfy every control above.
test('the guard recognises a correctly keyed element, so it is not vacuously null', () => {
  assert.equal(
    keyFieldOfSurfaceElement('<Surface key={task.c_task_instance_id} onSubmit={s} task={task} />'),
    'c_task_instance_id',
  );
});

test('the guard rejects a key bound to a repeating field, through the real predicate', () => {
  const field = keyFieldOfSurfaceElement('<Surface key={task.game_task_template_id} task={task} />');
  assert.equal(field, 'game_task_template_id');
  assert.ok(NON_IDENTIFYING_FIELDS.includes(field), 'the repeating-field list would not catch it');
});

// ---------------------------------------------------------------------------
// The attempt component of the key -- added for the retry loop. `keyFieldOfSurfaceElement` alone
// cannot see this: a key bound to `task.c_task_instance_id` with no attempt component passes every
// test above unchanged, yet would not remount between a wrong answer and a "try again" on the same
// task. `keyIncludesAttempt` is the second, independent check that closes that gap.
// ---------------------------------------------------------------------------

test('the real Surface element\'s key includes the task field AND the attempt count', () => {
  const source = readFileSync(screenPath, 'utf8');
  assert.notEqual(keyFieldOfSurfaceElement(source), null, 'no task field in the key');
  assert.ok(keyIncludesAttempt(source), 'c-session-screen.tsx\'s Surface key does not include `attempt`');
});

test('the attempt guard fires on the pre-retry shape -- task field alone, no attempt', () => {
  assert.equal(
    keyIncludesAttempt('<Surface key={task.c_task_instance_id} onSubmit={s} task={task} />'),
    false,
  );
});

test('the attempt guard fires when there is no Surface element, or no key, at all', () => {
  assert.equal(keyIncludesAttempt('const a = 1;'), false);
  assert.equal(keyIncludesAttempt('<Surface onSubmit={s} task={task} />'), false);
});

test('the attempt guard fires on a lookalike identifier -- `attemptCount` is not `attempt`', () => {
  assert.equal(
    keyIncludesAttempt('<Surface key={`${task.c_task_instance_id}:${attemptCount}`} task={task} />'),
    false,
  );
});

test('the attempt guard recognises the real, correctly-shaped key -- not vacuously false', () => {
  assert.ok(
    keyIncludesAttempt('<Surface key={`${task.c_task_instance_id}:${attempt}`} task={task} />'),
  );
});

test('keyFieldOfSurfaceElement still extracts the task field from the template-literal shape', () => {
  assert.equal(
    keyFieldOfSurfaceElement('<Surface key={`${task.c_task_instance_id}:${attempt}`} task={task} />'),
    'c_task_instance_id',
  );
});
