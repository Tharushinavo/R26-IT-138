// Behavioural resolution proof for `object-set-action` (10e), driven off the real, frozen exemplar
// fixtures for both real templates -- C-CC-01 (composite id-set + integer field) and C-CC-02
// (id-set only).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveObjectSetActionSpec } from '@/src/features/c-session/archetypes/object-set-action-logic';

function makeTaskFromExemplar(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-01',
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

const CC01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-01');
const CC02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-02');

test('C-CC-01: has 5 real exemplars', () => {
  assert.equal(CC01_ENTRIES.length, 5);
});

test('C-CC-02: has 5 real exemplars', () => {
  assert.equal(CC02_ENTRIES.length, 5);
});

test('C-CC-01 resolves at every difficulty level, with a non-null totalKey (the composite id-set + integer-field shape)', () => {
  for (const entry of CC01_ENTRIES) {
    const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
    assert.notEqual(spec, null, `level ${entry.difficulty_level} failed to resolve`);
    assert.notEqual(spec!.totalKey, null, `level ${entry.difficulty_level} should have a totalKey`);
    assert.equal(spec!.totalKey, 'submitted_total');
    assert.equal(spec!.idSetKey, 'selected_object_ids');
  }
});

test('C-CC-02 resolves at every difficulty level, with totalKey null (the id-set-only shape)', () => {
  for (const entry of CC02_ENTRIES) {
    const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
    assert.notEqual(spec, null, `level ${entry.difficulty_level} failed to resolve`);
    assert.equal(spec!.totalKey, null, `level ${entry.difficulty_level} should have no totalKey`);
    assert.equal(spec!.idSetKey, 'placed_object_ids');
  }
});

test('C-CC-01: objectIds concatenates the two id-array payload keys in wire key order, with no distinction preserved', () => {
  const entry = CC01_ENTRIES[2]!; // difficulty 3, has both valid and distractor ids
  const payload = entry.prompt_payload as { valid_object_ids: string[]; distractor_object_ids: string[] };
  assert.ok(payload.distractor_object_ids.length > 0, 'sanity: this exemplar should have distractors');

  const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
  assert.notEqual(spec, null);
  // Wire key order, not an assumed name order -- Object.keys(entry.prompt_payload) is the actual
  // JSON key order, which the resolver iterates and concatenates.
  const expected: string[] = [];
  for (const key of Object.keys(entry.prompt_payload)) {
    const value = (entry.prompt_payload as Record<string, unknown>)[key];
    if (Array.isArray(value)) expected.push(...(value as string[]));
  }
  assert.deepEqual(spec!.objectIds, expected);
  // Sanity: this exemplar really does exercise concatenation of two arrays, not a vacuous
  // single-key case.
  assert.equal(expected.length, payload.valid_object_ids.length + payload.distractor_object_ids.length);
});

test('C-CC-02: objectIds equals available_object_ids in wire order', () => {
  const entry = CC02_ENTRIES[0]!;
  const payload = entry.prompt_payload as { available_object_ids: string[] };
  const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.objectIds, payload.available_object_ids);
});

test('C-CC-02: targetValue resolves target_n with the "How many" label, value matching the wire', () => {
  const entry = CC02_ENTRIES[0]!;
  const payload = entry.prompt_payload as { target_n: number };
  const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
  assert.notEqual(spec, null);
  assert.notEqual(spec!.targetValue, null);
  assert.equal(spec!.targetValue!.key, 'target_n');
  assert.equal(spec!.targetValue!.value, payload.target_n);
  assert.equal(spec!.targetValue!.label, 'How many');
});

test('C-CC-01: targetValue is null (no non-array payload key besides the id lists)', () => {
  const entry = CC01_ENTRIES[0]!;
  const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
  assert.notEqual(spec, null);
  assert.equal(spec!.targetValue, null);
});

test('prompt_text is preserved verbatim', () => {
  const entry = CC01_ENTRIES[0]!;
  const spec = resolveObjectSetActionSpec(makeTaskFromExemplar(entry));
  assert.notEqual(spec, null);
  assert.equal(spec!.promptText, entry.prompt_text);
});
