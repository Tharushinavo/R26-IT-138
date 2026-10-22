// AC 5: every malformed path renders fail-closed, each with a negative control proving the guard
// fires -- mirroring c-object-set-action-fail-closed.test.ts's own table-driven convention.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveNamedIntegerFieldsSpec } from '@/src/features/c-session/archetypes/named-integer-fields-logic';

function validTask(): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-1',
    difficulty_level: 3,
    game_family_id: 'C-GF-04',
    game_task_template_id: 'C-BT-01',
    interactive_assets: {},
    prompt_payload: { target_number: 29 },
    prompt_text: 'Show this number using tens and ones.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { tens: 'int', ones: 'int' },
  };
}

test('the valid baseline resolves (sanity check for every negative control below)', () => {
  assert.notEqual(resolveNamedIntegerFieldsSpec(validTask()), null);
});

const NEGATIVE_CONTROLS: Array<{ name: string; mutate: (task: CNextTaskResponse) => void }> = [
  { name: 'prompt_text is an empty string', mutate: (t) => { t.prompt_text = ''; } },
  { name: 'blanks is a positive integer instead of null', mutate: (t) => { t.blanks = 1; } },
  { name: 'prompt_payload is null', mutate: (t) => { (t as { prompt_payload: unknown }).prompt_payload = null; } },
  { name: 'prompt_payload is an empty object', mutate: (t) => { t.prompt_payload = {}; } },
  { name: 'prompt_payload contains a non-number value outside the single named `direction` exception', mutate: (t) => { t.prompt_payload = { target_number: 29, note: 'read' }; } },
  { name: 'direction is present but an empty string', mutate: (t) => { t.prompt_payload = { target_number: 29, direction: '' }; } },
  { name: 'rows is present without cols (a malformed, asymmetric grid)', mutate: (t) => { t.prompt_payload = { target_number: 29, rows: 5 }; } },
  { name: 'cols is present without rows', mutate: (t) => { t.prompt_payload = { target_number: 29, cols: 5 }; } },
  { name: 'rows exceeds MAX_GRID_DIMENSION (10)', mutate: (t) => { t.prompt_payload = { rows: 11, cols: 5, direction: 'read' }; t.valid_action_space = { rows: 'int', cols: 'int', submitted_product: 'int' }; } },
  { name: 'rows is zero', mutate: (t) => { t.prompt_payload = { rows: 0, cols: 5, direction: 'read' }; t.valid_action_space = { rows: 'int', cols: 'int', submitted_product: 'int' }; } },
  { name: 'rows is fractional', mutate: (t) => { t.prompt_payload = { rows: 2.5, cols: 5, direction: 'read' }; t.valid_action_space = { rows: 'int', cols: 'int', submitted_product: 'int' }; } },
  { name: 'prompt_payload value is a string that looks numeric', mutate: (t) => { t.prompt_payload = { target_number: '29' }; } },
  { name: 'prompt_payload value is NaN', mutate: (t) => { t.prompt_payload = { target_number: Number.NaN }; } },
  { name: 'valid_action_space is empty', mutate: (t) => { t.valid_action_space = {}; } },
  { name: 'valid_action_space declares an unrecognised type', mutate: (t) => { t.valid_action_space = { tens: 'int', ones: 'weird' }; } },
  { name: 'valid_action_space declares only one integer-field key (fewer than MIN_FIELDS)', mutate: (t) => { t.valid_action_space = { tens: 'int' }; } },
  { name: 'valid_action_space declares more than MAX_FIELDS (6) integer-field keys', mutate: (t) => { t.valid_action_space = { a: 'int', b: 'int', c: 'int', d: 'int', e: 'int', f: 'int', g: 'int' }; } },
  { name: 'valid_action_space declares a non-integer-field key alongside integer-field keys', mutate: (t) => { t.valid_action_space = { tens: 'int', ones: 'int', extra: 'bool' }; } },
  { name: 'valid_action_space declares a list[str] key alongside integer-field keys', mutate: (t) => { t.valid_action_space = { tens: 'int', ones: 'int', ids: 'list[str]' }; } },
];

for (const { name, mutate } of NEGATIVE_CONTROLS) {
  test(`fails closed: ${name}`, () => {
    const task = validTask();
    mutate(task);
    assert.equal(resolveNamedIntegerFieldsSpec(task), null);
  });
}

test('fails closed on an entirely unknown shape too (no template-id special-casing rescues it)', () => {
  const task = validTask();
  task.game_task_template_id = 'C-DOES-NOT-EXIST';
  task.valid_action_space = { some_key: 'unbound' };
  assert.equal(resolveNamedIntegerFieldsSpec(task), null);
});

test('exactly one integer-field key resolves to value-report\'s own shape, not this one (MIN_FIELDS boundary)', () => {
  const task = validTask();
  task.valid_action_space = { tens: 'int' };
  assert.equal(resolveNamedIntegerFieldsSpec(task), null);
});

test('exactly MAX_FIELDS (6) integer-field keys still resolves (boundary, not "exceeds")', () => {
  const task = validTask();
  task.prompt_payload = { target_number: 29 };
  task.valid_action_space = { a: 'int', b: 'int', c: 'int', d: 'int', e: 'int', f: 'int' };
  const spec = resolveNamedIntegerFieldsSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.fields.length, 6);
});
