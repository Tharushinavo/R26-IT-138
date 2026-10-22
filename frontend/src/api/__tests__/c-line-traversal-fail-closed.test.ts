// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires. Consolidates the fail-closed enumeration for `resolveLineTraversalSpec` beyond what
// c-line-traversal-logic.test.ts already covers per-case, by proving each guard is independently
// necessary (removing it, one at a time via a passing baseline, would let a bad shape through).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveLineTraversalSpec } from '@/src/features/c-session/archetypes/line-traversal-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 5,
    game_family_id: 'C-GF-05',
    game_task_template_id: 'C-JB-02',
    interactive_assets: {},
    prompt_payload: { addend_a: 3, addend_b: 9, start: 9 },
    prompt_text: 'Start at the larger number and count on. Write where you land and each jump.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { final_position: 'int', jumps: 'list[int]' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveLineTraversalSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'prompt_payload is empty (no start key at all)', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'start is a fractional number', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, start: 9.1 }; } },
  { name: 'start is NaN', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, start: Number.NaN }; } },
  { name: 'start is a string', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, start: '9' }; } },
  { name: 'a non-origin payload value is a string', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, addend_b: 'nine' }; } },
  { name: 'a non-origin payload value is a boolean', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, addend_b: true }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { final_position: 'int', jumps: 'weird' }; } },
  { name: 'valid_action_space declares only the int key, no list[int] key', mutate: (t) => { t.valid_action_space = { final_position: 'int' }; } },
  { name: 'valid_action_space declares only the list[int] key, no int key', mutate: (t) => { t.valid_action_space = { jumps: 'list[int]' }; } },
  { name: 'valid_action_space declares two int keys and one list[int] key', mutate: (t) => { t.valid_action_space = { final_position: 'int', another: 'int', jumps: 'list[int]' }; } },
  { name: 'valid_action_space declares one int key and two list[int] keys', mutate: (t) => { t.valid_action_space = { final_position: 'int', jumps: 'list[int]', more_jumps: 'list[int]' }; } },
  { name: 'valid_action_space declares an extra bool key alongside the required two', mutate: (t) => { t.valid_action_space = { final_position: 'int', jumps: 'list[int]', extra: 'bool' }; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveLineTraversalSpec(task), null);
  });
}

test('fails closed on an entirely unknown shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveLineTraversalSpec(task), null);
});
