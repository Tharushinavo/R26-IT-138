// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires. Consolidates the fail-closed enumeration for `resolveLinePositionSpec` beyond what
// c-line-position-logic.test.ts already covers per-case, by proving each guard is independently
// necessary (removing it, one at a time via a passing baseline, would let a bad shape through).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveLinePositionSpec } from '@/src/features/c-session/archetypes/line-position-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 5,
    game_family_id: 'C-GF-03',
    game_task_template_id: 'C-MCL-04',
    interactive_assets: {},
    prompt_payload: { interval_max: 200, target_position: 34 },
    prompt_text: 'Move the marker to the target spot on the line.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { marker_position: 'number' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveLinePositionSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'prompt_payload is empty (no interval_max/target_position at all)', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'interval_max is a fractional number', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, interval_max: 200.5 }; } },
  { name: 'interval_max is NaN', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, interval_max: Number.NaN }; } },
  { name: 'interval_max is a string', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, interval_max: '200' }; } },
  { name: 'interval_max is zero', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, interval_max: 0, target_position: 0 }; } },
  { name: 'interval_max exceeds MAX_INTERVAL_MAX (1000)', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, interval_max: 1001, target_position: 5 }; } },
  { name: 'target_position is negative', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, target_position: -1 }; } },
  { name: 'target_position exceeds interval_max', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, target_position: 201 }; } },
  { name: 'target_position is a boolean', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, target_position: true }; } },
  { name: 'an extra payload value is a boolean', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, extra: true }; } },
  { name: 'an extra payload value is a string', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, extra: 'seven' }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { marker_position: 'weird' }; } },
  { name: 'valid_action_space declares int instead of number', mutate: (t) => { t.valid_action_space = { marker_position: 'int' }; } },
  { name: 'valid_action_space declares two numeric-field keys', mutate: (t) => { t.valid_action_space = { marker_position: 'number', another: 'number' }; } },
  { name: 'valid_action_space declares an extra bool key alongside the required one', mutate: (t) => { t.valid_action_space = { marker_position: 'number', extra: 'bool' }; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveLinePositionSpec(task), null);
  });
}

test('fails closed on an entirely unknown shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveLinePositionSpec(task), null);
});
