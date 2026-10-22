// AC 5/6 (10e-0): every malformed path on the numeral-options scene renders fail-closed, each with
// a negative control proving the guard fires. Mirrors c-option-select-fail-closed.test.ts's own
// method for the pipe-string path. Every guard listed in this file's NEGATIVE_CONTROLS array is also
// independently proven by breaking it in option-select-logic.ts, confirming the targeted control
// goes red, then restoring -- see the verification report for that run (not encoded here, since it
// requires editing the source file itself, which this test does not do).

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
    game_task_template_id: 'C-MCL-01',
    interactive_assets: {},
    prompt_payload: { numeral_options: [3, 5, 9], target_representation_value: 9 },
    prompt_text: 'Choose the number that matches the amount shown.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { selected_value: 'int' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  const spec = resolveOptionSelectSpec(validTask());
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'numeral-options');
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  {
    name: 'the quantity value is a string',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: 'nine' }; },
  },
  {
    name: 'the quantity value is a boolean',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: true }; },
  },
  {
    name: 'the quantity value is a non-finite number (NaN)',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: Number.NaN }; },
  },
  {
    name: 'the quantity value is fractional (not an integer)',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: 5.5 }; },
  },
  {
    name: 'the quantity value is negative',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: -1 }; },
  },
  {
    name: 'the quantity value is above the layout bound (101)',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 101], target_representation_value: 101 }; },
  },
  {
    name: 'numeral_options is not an array (a plain number)',
    mutate: (t) => { t.prompt_payload = { numeral_options: 9, target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options is not an array (a string)',
    mutate: (t) => { t.prompt_payload = { numeral_options: '3,5,9', target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options contains a non-numeric element',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 'five', 9], target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options contains a boolean element',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, true, 9], target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options has fewer than 2 entries',
    mutate: (t) => { t.prompt_payload = { numeral_options: [9], target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options has more than the layout bound (11) entries',
    mutate: (t) => { t.prompt_payload = { numeral_options: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], target_representation_value: 9 }; },
  },
  {
    name: 'numeral_options key is absent entirely (a differently-named array instead)',
    mutate: (t) => { t.prompt_payload = { options: [3, 5, 9], target_representation_value: 9 }; },
  },
  {
    name: 'the quantity key is missing (only numeral_options present, one payload key total)',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9] }; },
  },
  {
    name: 'more than two payload keys (numeral_options, the quantity, and a third)',
    mutate: (t) => { t.prompt_payload = { numeral_options: [3, 5, 9], target_representation_value: 9, extra_key: 1 }; },
  },
  {
    name: 'blanks is a positive integer instead of null',
    mutate: (t) => { t.blanks = 1; },
  },
  {
    name: 'prompt_text is an empty string',
    mutate: (t) => { t.prompt_text = ''; },
  },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveOptionSelectSpec(task), null);
  });
}

test('the layout bound for numeral_options length is exactly 10 (2x the observed real maximum of 5): 10 entries resolves, 11 does not', () => {
  const at10 = validTask();
  at10.prompt_payload = { numeral_options: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], target_representation_value: 10 };
  assert.notEqual(resolveOptionSelectSpec(at10), null);

  const at11 = validTask();
  at11.prompt_payload = { numeral_options: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], target_representation_value: 11 };
  assert.equal(resolveOptionSelectSpec(at11), null);
});

test('the quantity bound is exactly 100 (a corruption-safety ceiling, deliberately above the real maximum of 66): 100 resolves, 101 does not', () => {
  const at100 = validTask();
  at100.prompt_payload = { numeral_options: [3, 5, 100], target_representation_value: 100 };
  assert.notEqual(resolveOptionSelectSpec(at100), null);

  const at101 = validTask();
  at101.prompt_payload = { numeral_options: [3, 5, 101], target_representation_value: 101 };
  assert.equal(resolveOptionSelectSpec(at101), null);
});
