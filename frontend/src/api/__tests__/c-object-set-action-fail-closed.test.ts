// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires. Consolidates the fail-closed enumeration for `resolveObjectSetActionSpec` beyond what
// c-object-set-action-logic.test.ts already covers per-case, by proving each guard is independently
// necessary (removing it, one at a time via a passing baseline, would let a bad shape through).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveObjectSetActionSpec } from '@/src/features/c-session/archetypes/object-set-action-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 3,
    game_family_id: 'C-GF-01',
    game_task_template_id: 'C-CC-01',
    interactive_assets: {},
    prompt_payload: {
      valid_object_ids: ['obj-0', 'obj-1', 'obj-2'],
      distractor_object_ids: ['dist-0'],
    },
    prompt_text: 'Select every object one time. Then write how many you selected.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { selected_object_ids: 'list[str]', submitted_total: 'int' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveObjectSetActionSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
  { name: 'prompt_payload has no string[] key at all (no id source)', mutate: (t) => { t.prompt_payload = { submitted_total: 5 }; } },
  { name: 'an id-array element is a number', mutate: (t) => { t.prompt_payload = { valid_object_ids: ['obj-0', 1], distractor_object_ids: [] }; } },
  { name: 'an id-array element is an empty string', mutate: (t) => { t.prompt_payload = { valid_object_ids: ['obj-0', ''], distractor_object_ids: [] }; } },
  { name: 'a duplicate id appears across the two id-array keys', mutate: (t) => { t.prompt_payload = { valid_object_ids: ['obj-0'], distractor_object_ids: ['obj-0'] }; } },
  { name: 'the concatenated pool exceeds MAX_POOL_OBJECTS (60)', mutate: (t) => { t.prompt_payload = { valid_object_ids: Array.from({ length: 61 }, (_, i) => `obj-${i}`), distractor_object_ids: [] }; } },
  { name: 'more than one non-array payload key is present', mutate: (t) => { t.prompt_payload = { valid_object_ids: ['obj-0'], distractor_object_ids: [], submitted_total: 5, another_scalar: 1 }; } },
  { name: 'the one non-array key is a fractional number', mutate: (t) => { t.prompt_payload = { available_object_ids: ['obj-0'], target_n: 3.5 }; } },
  { name: 'the one non-array key is negative', mutate: (t) => { t.prompt_payload = { available_object_ids: ['obj-0'], target_n: -1 }; } },
  { name: 'the one non-array key is NaN', mutate: (t) => { t.prompt_payload = { available_object_ids: ['obj-0'], target_n: Number.NaN }; } },
  { name: 'the one non-array key exceeds MAX_TARGET_VALUE (100)', mutate: (t) => { t.prompt_payload = { available_object_ids: ['obj-0'], target_n: 101 }; } },
  { name: 'the one non-array key is a boolean', mutate: (t) => { t.prompt_payload = { available_object_ids: ['obj-0'], target_n: true }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { selected_object_ids: 'list[str]', submitted_total: 'weird' }; } },
  { name: 'valid_action_space declares no id-set-collection key at all', mutate: (t) => { t.valid_action_space = { submitted_total: 'int' }; } },
  { name: 'valid_action_space declares two id-set-collection keys', mutate: (t) => { t.valid_action_space = { selected_object_ids: 'list[str]', another_ids: 'list[str]' }; } },
  { name: 'valid_action_space declares two integer-field keys', mutate: (t) => { t.valid_action_space = { selected_object_ids: 'list[str]', submitted_total: 'int', another_total: 'int' }; } },
  { name: 'valid_action_space declares an extra bool key alongside the required shape', mutate: (t) => { t.valid_action_space = { selected_object_ids: 'list[str]', submitted_total: 'int', extra: 'bool' }; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveObjectSetActionSpec(task), null);
  });
}

test('fails closed on an entirely unknown shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveObjectSetActionSpec(task), null);
});
