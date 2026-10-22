// AC 2: encoded `action_payload`'s key set exactly equals `valid_action_space`'s for both C-CC-01
// and C-CC-02, across every difficulty level. Uses the shared `encodeActionPayload`/`keySetEquals`
// -- the same function every archetype submits through -- never a per-template key table here.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const CC01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-01');
const CC02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-02');

test('C-CC-01: encoded payload key set exactly equals valid_action_space at every difficulty level', () => {
  for (const entry of CC01_ENTRIES) {
    const values = { selected_object_ids: ['obj-0', 'obj-1'], submitted_total: 2 };
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(encoded, null, `level ${entry.difficulty_level} failed to encode`);
    assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `level ${entry.difficulty_level}`);
    assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
  }
});

test('C-CC-02: encoded payload key set exactly equals valid_action_space at every difficulty level', () => {
  for (const entry of CC02_ENTRIES) {
    const values = { placed_object_ids: ['obj-0', 'obj-1', 'obj-2'] };
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(encoded, null, `level ${entry.difficulty_level} failed to encode`);
    assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `level ${entry.difficulty_level}`);
    assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
  }
});

test('C-CC-01: an empty selected_object_ids list still encodes (the client never enforces a minimum selection)', () => {
  const entry = CC01_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { selected_object_ids: [], submitted_total: 0 });
  assert.notEqual(encoded, null);
  assert.deepEqual(encoded!.selected_object_ids, []);
});

test('negative control: C-CC-01 missing submitted_total is rejected', () => {
  const entry = CC01_ENTRIES[0]!;
  const values: Record<string, unknown> = { selected_object_ids: ['obj-0'] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: C-CC-01 missing selected_object_ids is rejected', () => {
  const entry = CC01_ENTRIES[0]!;
  const values: Record<string, unknown> = { submitted_total: 1 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: list[str] rejects a number element', () => {
  const entry = CC01_ENTRIES[0]!;
  const values = { selected_object_ids: ['obj-0', 1], submitted_total: 2 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: list[str] rejects a boolean element', () => {
  const entry = CC02_ENTRIES[0]!;
  const values = { placed_object_ids: ['obj-0', true] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: submitted_total as a non-integer number is rejected (int rejects fractional)', () => {
  const entry = CC01_ENTRIES[0]!;
  const values = { selected_object_ids: ['obj-0'], submitted_total: 1.5 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: submitted_total as a boolean is rejected (int rejects bool, per the coercion trap)', () => {
  const entry = CC01_ENTRIES[0]!;
  const values = { selected_object_ids: ['obj-0'], submitted_total: true };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: C-CC-02 placed_object_ids as a non-array value is rejected', () => {
  const entry = CC02_ENTRIES[0]!;
  const values = { placed_object_ids: 'obj-0,obj-1' };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: an extra forbidden key is caught by keySetEquals', () => {
  const entry = CC02_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { placed_object_ids: ['obj-0'] });
  assert.notEqual(encoded, null);
  const withExtra = { ...encoded, extra_forbidden_key: 1 };
  assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
});
