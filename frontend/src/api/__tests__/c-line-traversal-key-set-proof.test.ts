// AC 2: `action_payload`'s key set exactly equals `valid_action_space`'s for C-JB-02, across every
// difficulty level. Uses the shared `encodeActionPayload`/`keySetEquals` -- the same function every
// archetype submits through -- never a per-template key table in this test.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const JB02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-JB-02');

test('C-JB-02: encoded payload key set exactly equals valid_action_space at every difficulty level', () => {
  for (const entry of JB02_ENTRIES) {
    const values = { final_position: 7, jumps: [1, 1, 1] };
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(encoded, null, `level ${entry.difficulty_level} failed to encode`);
    assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `level ${entry.difficulty_level}`);
    assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
  }
});

test('C-JB-02: an empty jumps list still encodes (the client never enforces a minimum jump count)', () => {
  const entry = JB02_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { final_position: 3, jumps: [] });
  assert.notEqual(encoded, null);
  assert.deepEqual(encoded!.jumps, []);
});

test('negative control: missing final_position is rejected', () => {
  const entry = JB02_ENTRIES[0]!;
  const values: Record<string, unknown> = { jumps: [1] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: missing jumps is rejected', () => {
  const entry = JB02_ENTRIES[0]!;
  const values: Record<string, unknown> = { final_position: 3 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: final_position as a non-integer number is rejected (int rejects fractional)', () => {
  const entry = JB02_ENTRIES[0]!;
  const values = { final_position: 3.5, jumps: [1] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: final_position as a boolean is rejected (int rejects bool, per the coercion trap)', () => {
  const entry = JB02_ENTRIES[0]!;
  const values = { final_position: true, jumps: [1] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: jumps containing a non-integer element is rejected', () => {
  const entry = JB02_ENTRIES[0]!;
  const values = { final_position: 3, jumps: [1, 1.5] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: jumps containing a boolean element is rejected', () => {
  const entry = JB02_ENTRIES[0]!;
  const values = { final_position: 3, jumps: [1, true] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: jumps as a non-array value is rejected', () => {
  const entry = JB02_ENTRIES[0]!;
  const values = { final_position: 3, jumps: '1,1,1' };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: an extra forbidden key is caught by keySetEquals', () => {
  const entry = JB02_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { final_position: 3, jumps: [1] });
  assert.notEqual(encoded, null);
  const withExtra = { ...encoded, extra_forbidden_key: 1 };
  assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
});
