// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires. Consolidates the fail-closed enumeration for `resolveOptionSelectSpec`'s pipe-string path
// beyond what c-option-select-logic.test.ts already covers per real template, by proving each guard
// is independently necessary (removing it, one at a time via a passing baseline, would let a bad
// shape through). The numeral-options path's OWN fail-closed enumeration (10e-0) lives in its own
// dedicated file, c-option-select-numeral-options-fail-closed.test.ts -- this file keeps only the
// pipe-string guards plus the handful of tests below whose behaviour the 10e-0 unblock changed.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 3,
    game_family_id: 'C-GF-03',
    game_task_template_id: 'C-MCL-02',
    interactive_assets: {},
    prompt_payload: { left_count: 10, right_count: 27 },
    prompt_text: 'Choose which side has more, or say if they are equal.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { selection: 'left|right|equal' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveOptionSelectSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
  { name: 'prompt_payload is an empty object', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'prompt_payload contains a string value', mutate: (t) => { t.prompt_payload = { left_count: 10, right_count: 'many' }; } },
  { name: 'prompt_payload contains a boolean value', mutate: (t) => { t.prompt_payload = { left_count: 10, right_count: true }; } },
  { name: 'prompt_payload contains a non-finite number (NaN)', mutate: (t) => { t.prompt_payload = { left_count: Number.NaN, right_count: 27 }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { selection: 'weird_type' }; } },
  { name: 'valid_action_space declares a pipe-string with fewer than two alternatives (single value, no "|")', mutate: (t) => { t.valid_action_space = { selection: 'left' }; } },
  { name: 'valid_action_space declares two exact-choice-control keys', mutate: (t) => { t.valid_action_space = { selection: 'left|right|equal', verdict: 'up|down' }; } },
  { name: 'valid_action_space declares only a bool key, no choice key', mutate: (t) => { t.valid_action_space = { exchange_performed: 'bool' }; } },
  { name: 'valid_action_space declares an extra key bound to a kind other than boolean-control', mutate: (t) => { t.valid_action_space = { selection: 'left|right|equal', groups: 'list[int]' }; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveOptionSelectSpec(task), null);
  });
}

test('fails closed on an entirely unknown template shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveOptionSelectSpec(task), null);
});

// --- the integer-field / numeral-options path -- unblocked in 10e-0 --------------------------------
// 10d proved a structural REFUSAL here with the four tests this section used to hold. 10e-0 unblocks
// the path (see option-select-logic.ts's own header); its own dedicated fail-closed coverage lives
// in c-option-select-numeral-options-fail-closed.test.ts. The two tests below are the ones whose
// ASSERTION genuinely flips (null -> resolves) and are kept here, explicitly, so the change from
// 10d is visible against the exact fixtures the original refusal was proven against -- not silently
// dropped. The other two of the original four are also updated below: one's assertion was already
// "resolves normally" and needed no change beyond its own comment; one still asserts null, but now
// for the real reason (wrong payload key count), not the old refusal.

test("a real C-MCL-01-shaped task resolves now (10e-0: was 'the integer-field path refuses even with an otherwise fully valid...' in 10d)", () => {
  const task = validTask();
  task.game_task_template_id = 'C-MCL-01';
  task.prompt_text = 'Choose the number that matches the amount shown.';
  task.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: 9 };
  task.valid_action_space = { selected_value: 'int' };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'numeral-options');
  if (spec!.kind === 'numeral-options') {
    assert.equal(spec!.quantity, 9);
    assert.deepEqual(spec!.numeralOptions, [3, 5, 9]);
  }
});

test('a task with a pipe-string action space (not integer-field) resolves normally, as it always did (proves classification is keyed on the declared TYPE, not accidentally on something else about this shape) -- unchanged from 10d, comment updated only', () => {
  const task = validTask();
  task.prompt_payload = { numeral_options_count: 3 };
  task.valid_action_space = { verdict: 'yes|no' };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'choice');
});

test("fails closed: a lone payload key with an int-typed action-space key (no numeral_options present, and only one payload key where the numeral-options path requires exactly two) -- was 'the integer-field refusal fires with no numeral_options key present at all' in 10d; still null, now for the real, positive reason instead of the old refusal", () => {
  const task = validTask();
  task.prompt_payload = { some_unrelated_value: 5 };
  task.valid_action_space = { selected_value: 'int' };
  assert.equal(resolveOptionSelectSpec(task), null);
});

test("a synthetic differently-named int key resolves identically to a real one (10e-0: was 'the integer-field refusal fires regardless of key name...' in 10d; the type-not-name discipline survives, only the outcome for this binding kind changed) -- proves classification is type-derived, not a hardcoded key-name pair", () => {
  const task = validTask();
  task.prompt_payload = { numeral_options: [1, 2], other: 1 };
  task.valid_action_space = { chosen_answer: 'int' };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'numeral-options');
  if (spec!.kind === 'numeral-options') {
    assert.equal(spec!.scoreKey, 'chosen_answer');
    assert.equal(spec!.quantity, 1);
  }
});
