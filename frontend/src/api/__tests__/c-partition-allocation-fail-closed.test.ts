// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires -- mirroring c-named-integer-fields-fail-closed.test.ts's own table-driven convention.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 2,
    game_family_id: 'C-GF-07',
    game_task_template_id: 'C-EG-01',
    interactive_assets: {},
    prompt_payload: { number_of_groups: 3, group_size: 2 },
    prompt_text: 'Make the groups. Put the same number in each.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { groups: 'list[int]' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolvePartitionAllocationSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
  { name: 'prompt_payload is an empty object', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'prompt_payload contains a non-number value', mutate: (t) => { t.prompt_payload = { number_of_groups: 3, group_size: 2, note: 'x' }; } },
  { name: 'no bin-count key present at all', mutate: (t) => { t.prompt_payload = { group_size: 2 }; } },
  { name: 'two bin-count keys present at once', mutate: (t) => { t.prompt_payload = { number_of_groups: 3, recipient_count: 3, group_size: 2 }; } },
  { name: 'bin-count value is fractional', mutate: (t) => { t.prompt_payload = { number_of_groups: 3.5, group_size: 2 }; } },
  { name: 'bin-count value is zero', mutate: (t) => { t.prompt_payload = { number_of_groups: 0, group_size: 2 }; } },
  { name: 'bin-count value is negative', mutate: (t) => { t.prompt_payload = { number_of_groups: -1, group_size: 2 }; } },
  { name: 'bin-count value exceeds MAX_BINS (12)', mutate: (t) => { t.prompt_payload = { number_of_groups: 13, group_size: 2 }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { groups: 'weird' }; } },
  { name: 'valid_action_space declares no ordered-integer-collection key at all', mutate: (t) => { t.valid_action_space = { total: 'int' }; } },
  { name: "valid_action_space declares a list[int] key outside the vocabulary ('bins')", mutate: (t) => { t.valid_action_space = { bins: 'list[int]' }; } },
  { name: 'valid_action_space declares two ordered-integer-collection keys', mutate: (t) => { t.valid_action_space = { groups: 'list[int]', allocations: 'list[int]' }; } },
  { name: 'valid_action_space declares an integer-field alongside the collection (the variable-bin-count shape, C-SF-02)', mutate: (t) => { t.valid_action_space = { groups: 'list[int]', submitted_group_count: 'int' }; } },
  { name: 'valid_action_space declares a list[str] key alongside the collection', mutate: (t) => { t.valid_action_space = { groups: 'list[int]', ids: 'list[str]' }; } },
  { name: 'valid_action_space declares a bool key alongside the collection', mutate: (t) => { t.valid_action_space = { groups: 'list[int]', extra: 'bool' }; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolvePartitionAllocationSpec(task), null);
  });
}

test('fails closed on an entirely unknown shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolvePartitionAllocationSpec(task), null);
});

test('bin count exactly MAX_BINS (12) still resolves (boundary, not "exceeds")', () => {
  const task = validTask();
  task.prompt_payload = { number_of_groups: 12, group_size: 2 };
  const spec = resolvePartitionAllocationSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.binCount, 12);
});

test('C-SF-02\'s real declared shape (groups + submitted_group_count) fails closed, matching the header\'s own stated finding', () => {
  const task = validTask();
  task.game_task_template_id = 'C-SF-02';
  task.prompt_payload = { total: 4, group_size: 2 };
  task.valid_action_space = { groups: 'list[int]', submitted_group_count: 'int' };
  assert.equal(resolvePartitionAllocationSpec(task), null);
});
