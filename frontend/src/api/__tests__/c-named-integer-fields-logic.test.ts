// `resolveNamedIntegerFieldsSpec` (10f): resolution over all four C-BT-* templates, proving one
// resolver covers both the 2-field (BT-01/03/04) and 3-field (BT-02) shapes with no per-template
// branch, plus the field-count discriminator against `value-report`.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolveNamedIntegerFieldsSpec } from '@/src/features/c-session/archetypes/named-integer-fields-logic';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

function makeTask(entry: ExemplarEntry): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-04',
    game_task_template_id: entry.game_task_template_id,
    interactive_assets: entry.interactive_assets,
    prompt_payload: entry.prompt_payload,
    prompt_text: entry.prompt_text,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: entry.valid_action_space,
  };
}

const BT_TEMPLATE_IDS = ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04'];
const BT_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => BT_TEMPLATE_IDS.includes(entry.game_task_template_id));

test('C-BT-01..04: exactly 5 exemplar rows each (difficulty 1-5), all present in the frozen fixture', () => {
  for (const id of BT_TEMPLATE_IDS) {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === id);
    assert.equal(entries.length, 5, id);
  }
});

test('every C-BT-* exemplar resolves at every difficulty level', () => {
  for (const entry of BT_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    if (spec === null) {
      assert.fail(`${entry.game_task_template_id} level ${entry.difficulty_level} failed to resolve`);
      continue;
    }
    assert.equal(spec.promptText, entry.prompt_text);
    assert.deepEqual(spec.interactiveAssets, entry.interactive_assets);
  }
});

test('C-BT-01/03/04 resolve exactly 2 fields; C-BT-02 resolves exactly 3 -- no per-template branch, purely the declared key count', () => {
  for (const entry of BT_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    const expected = entry.game_task_template_id === 'C-BT-02' ? 3 : 2;
    assert.equal(spec!.fields.length, expected, `${entry.game_task_template_id} level ${entry.difficulty_level}`);
  }
});

test('field keys are exactly Object.keys(valid_action_space), in wire key order', () => {
  for (const entry of BT_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.deepEqual(
      spec!.fields.map((field) => field.key),
      Object.keys(entry.valid_action_space),
    );
  }
});

test('field labels are mechanically humanised from the key, never from a fixed table (post_tens -> "Post Tens"), in the wire\'s own key order', () => {
  const entry = BT_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-03')!;
  const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(
    spec!.fields.map((field) => field.label),
    Object.keys(entry.valid_action_space).map((key) =>
      key
        .split('_')
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' '),
    ),
  );
  assert.deepEqual(spec!.fields.map((field) => field.label).sort(), ['Post Ones', 'Post Tens']);
});

test('C-BT-01: field labels are "Tens" and "Ones", in the wire\'s own key order', () => {
  const entry = BT_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-01')!;
  const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.fields.map((field) => field.label).sort(), ['Ones', 'Tens']);
  assert.deepEqual(
    spec!.fields.map((field) => field.label),
    Object.keys(entry.valid_action_space).map((key) => key.charAt(0).toUpperCase() + key.slice(1)),
  );
});

test('C-BT-02: field labels are "Hundreds", "Tens", "Ones", matching the wire\'s own key order exactly', () => {
  const entry = BT_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-02')!;
  const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.fields.map((field) => field.label).sort(), ['Hundreds', 'Ones', 'Tens']);
  assert.deepEqual(
    spec!.fields.map((field) => field.label),
    Object.keys(entry.valid_action_space).map((key) => key.charAt(0).toUpperCase() + key.slice(1)),
  );
});

test('payloadValues carry every prompt_payload key, in wire order, each a finite number', () => {
  for (const entry of BT_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.deepEqual(
      spec!.payloadValues.map((value) => value.key),
      Object.keys(entry.prompt_payload),
    );
    for (const value of spec!.payloadValues) {
      assert.equal(typeof value.value, 'number');
    }
  }
});

test('resolves: a synthetic 4-field valid_action_space also resolves (proves classification is a count of integer-field keys, not a fixed 2-or-3 enum)', () => {
  const task = makeTask(BT_ENTRIES[0]!);
  task.prompt_payload = { target_number: 42 };
  task.valid_action_space = { a: 'int', b: 'int', c: 'int', d: 'int' };
  const spec = resolveNamedIntegerFieldsSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.fields.length, 4);
});

test('C-BT-01..04 resolve to named-integer-fields, not any other archetype', () => {
  for (const id of BT_TEMPLATE_IDS) {
    const entry = BT_ENTRIES.find((e) => e.game_task_template_id === id)!;
    assert.equal(resolveArchetype(id, entry.valid_action_space), 'named-integer-fields', id);
  }
});
