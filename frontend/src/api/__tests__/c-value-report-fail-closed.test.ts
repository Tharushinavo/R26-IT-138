// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires. Consolidates the fail-closed enumeration for `resolveValueReportSpec` beyond what
// c-value-report-logic.test.ts already covers per-case, by proving each guard is independently
// necessary (removing it, one at a time via a passing baseline, would let a bad shape through).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 3,
    game_family_id: 'C-GF-06',
    game_task_template_id: 'C-TC-01',
    interactive_assets: {},
    prompt_payload: { initial_count: 6, removed_count: 5 },
    prompt_text: 'Take away the amount shown. Write how many are left.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { submitted_remainder: 'int' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveValueReportSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { submitted_remainder: 'weird_type' }; } },
  { name: 'valid_action_space declares two int keys', mutate: (t) => { t.valid_action_space = { submitted_remainder: 'int', extra_total: 'int' }; } },
  { name: 'valid_action_space declares only a bool key, no int', mutate: (t) => { t.valid_action_space = { exchange_performed: 'bool' }; } },
  { name: 'valid_action_space declares an extra list[int] key alongside the int scene key', mutate: (t) => { t.valid_action_space = { submitted_remainder: 'int', groups: 'list[int]' }; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 2; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
  { name: 'prompt_payload is an empty object', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'prompt_payload contains a non-numeric value (e.g. a boolean discriminator)', mutate: (t) => { t.prompt_payload = { ...t.prompt_payload, directed: true }; } },
  { name: 'prompt_payload contains a string value', mutate: (t) => { t.prompt_payload = { initial_count: '6', removed_count: 5 }; } },
  { name: 'prompt_payload contains a non-finite number (NaN)', mutate: (t) => { t.prompt_payload = { initial_count: Number.NaN, removed_count: 5 }; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveValueReportSpec(task), null);
  });
}

test('fails closed on an entirely unknown template shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveValueReportSpec(task), null);
});

// C-TC-02 exclusion (2026-08-26 fix): registry.ts's ARCHETYPE_TABLE already routes
// 'C-TC-02' -> 'value-report', and this resolver is otherwise purely type-based, so without an
// explicit refusal C-TC-02 would silently resolve to a live, mounted surface -- see
// value-report-logic.ts's own comment at the check for the full reason (its `directed` payload
// flag may need a signed answer DigitKeypad cannot produce).
//
// A real C-TC-02 exemplar's payload happens to contain a boolean `directed` key at every
// difficulty level (measured: false at L1-4, true at L5), which the pre-existing "prompt_payload
// contains a non-numeric value" guard above would ALSO reject -- coincidentally, not by design.
// That coincidence is fragile: if a future payload revision ever dropped `directed`, C-TC-02 would
// silently start resolving with no review. The two tests below isolate the new, explicit,
// id-based refusal from that coincidence, so this guard's own correctness does not depend on
// C-TC-02's payload shape staying accidentally hostile forever.

test('C-TC-02 fails closed even with an otherwise fully valid, all-numeric payload and action space (isolates the id-check from the coincidental boolean-payload guard above)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-TC-02';
  // Deliberately NOT using C-TC-02's real payload shape here -- it stays C-TC-01's numeric-only
  // { initial_count, removed_count } on purpose, so nothing about this task's payload could
  // independently trigger the non-numeric-value guard. Only the template id changed.
  assert.equal(resolveValueReportSpec(task), null);
});

test('a task otherwise identical to C-TC-02 but with a covered template id resolves normally (proves the refusal is keyed on the id, not accidentally on something else about this shape)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-TC-01';
  assert.notEqual(resolveValueReportSpec(task), null);
});

test('the real C-TC-02 exemplar shape fails closed at difficulty 1 (directed: false) and difficulty 5 (directed: true) alike', () => {
  const base = validTask();
  base.game_task_template_id = 'C-TC-02';
  base.valid_action_space = { submitted_difference: 'int' };
  base.prompt_text = 'Compare the two numbers. Write how many more or how many fewer.';

  const atL1: CNextTaskResponse = {
    ...base,
    difficulty_level: 1,
    prompt_payload: { directed: false, value_a: 1, value_b: 2 },
  };
  const atL5: CNextTaskResponse = {
    ...base,
    difficulty_level: 5,
    prompt_payload: { directed: true, value_a: 5, value_b: 9 },
  };
  assert.equal(resolveValueReportSpec(atL1), null);
  assert.equal(resolveValueReportSpec(atL5), null);
});
