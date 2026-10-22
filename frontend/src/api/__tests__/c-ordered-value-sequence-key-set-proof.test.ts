// The end-to-end key-set proof (10a acceptance criteria 2-3): for all four NP templates, a payload
// built from the resolved spec's own scene key and run through encodeActionPayload (10.0's shared
// encoder, unmodified) produces a key set exactly equal to valid_action_space, with list[int]
// rejecting a non-integer element and rejecting a boolean.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import {
  encodeActionPayload,
  keySetEquals,
} from '@/src/features/c-session/archetypes/encode-action-payload';
import { resolveOrderedValueSequenceSpec } from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';

function makeTaskFromExemplar(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-02',
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

for (const templateId of ['C-NP-01', 'C-NP-02', 'C-NP-03', 'C-NP-04']) {
  test(`${templateId}: encodeActionPayload's key set equals valid_action_space at every difficulty level`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);

    for (const entry of entries) {
      const task = makeTaskFromExemplar(entry);
      const spec = resolveOrderedValueSequenceSpec(task);
      assert.notEqual(spec, null, `${templateId} level ${entry.difficulty_level} failed to resolve`);

      const values =
        spec!.scene === 'entry'
          ? { [spec!.entryKey]: [7, 8].slice(0, spec!.blanks) }
          : { [spec!.arrangeKey]: [...spec!.values] };

      const payload = encodeActionPayload(task.valid_action_space, values);
      assert.notEqual(payload, null, `${templateId} level ${entry.difficulty_level} failed to encode`);
      assert.equal(
        keySetEquals(payload as Record<string, unknown>, task.valid_action_space),
        true,
        `${templateId} level ${entry.difficulty_level}: key set disagrees with valid_action_space`,
      );
    }
  });
}

test('entered_values rejects a non-integer element via encodeActionPayload', () => {
  const validActionSpace = { entered_values: 'list[int]' };
  assert.equal(encodeActionPayload(validActionSpace, { entered_values: [1, 2.5] }), null);
});

test('entered_values rejects a boolean element via encodeActionPayload', () => {
  const validActionSpace = { entered_values: 'list[int]' };
  assert.equal(encodeActionPayload(validActionSpace, { entered_values: [1, true] }), null);
});

test('arranged_values rejects a non-integer element via encodeActionPayload', () => {
  const validActionSpace = { arranged_values: 'list[int]' };
  assert.equal(encodeActionPayload(validActionSpace, { arranged_values: [1, 2.5] }), null);
});

test('arranged_values rejects a boolean element via encodeActionPayload', () => {
  const validActionSpace = { arranged_values: 'list[int]' };
  assert.equal(encodeActionPayload(validActionSpace, { arranged_values: [1, false] }), null);
});

test('negative control: a payload missing entered_values fails keySetEquals', () => {
  const validActionSpace = { entered_values: 'list[int]' };
  assert.equal(keySetEquals({}, validActionSpace), false);
});

test('negative control: a payload carrying an extra key beyond arranged_values fails keySetEquals', () => {
  const validActionSpace = { arranged_values: 'list[int]' };
  const tampered = { arranged_values: [1, 2, 3], extra: true };
  assert.equal(keySetEquals(tampered, validActionSpace), false);
});
