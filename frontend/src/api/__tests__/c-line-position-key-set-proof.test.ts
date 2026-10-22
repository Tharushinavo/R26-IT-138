// AC 2: `action_payload`'s key set exactly equals `valid_action_space`'s for C-MCL-04, across every
// difficulty level. Uses the shared `encodeActionPayload`/`keySetEquals` -- the same function every
// archetype submits through -- never a per-template key table in this test.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const MCL04_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-04');

test('C-MCL-04: encoded payload key set exactly equals valid_action_space at every difficulty level', () => {
  for (const entry of MCL04_ENTRIES) {
    const values = { marker_position: 7 };
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(encoded, null, `level ${entry.difficulty_level} failed to encode`);
    assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `level ${entry.difficulty_level}`);
    assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
  }
});

test('C-MCL-04: marker_position of 0 still encodes (the boundary value, not just positive ones)', () => {
  const entry = MCL04_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { marker_position: 0 });
  assert.notEqual(encoded, null);
  assert.equal(encoded!.marker_position, 0);
});

test('C-MCL-04: marker_position accepts a fractional value (the wire declares "number", not "int")', () => {
  const entry = MCL04_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { marker_position: 3.5 });
  assert.notEqual(encoded, null);
  assert.equal(encoded!.marker_position, 3.5);
});

test('negative control: missing marker_position is rejected', () => {
  const entry = MCL04_ENTRIES[0]!;
  const values: Record<string, unknown> = {};
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: marker_position as a boolean is rejected (numeric-field rejects bool, per the coercion trap)', () => {
  const entry = MCL04_ENTRIES[0]!;
  const values = { marker_position: true };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: marker_position as a string is rejected', () => {
  const entry = MCL04_ENTRIES[0]!;
  const values = { marker_position: '7' };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: marker_position as NaN is rejected', () => {
  const entry = MCL04_ENTRIES[0]!;
  const values = { marker_position: Number.NaN };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: an extra forbidden key is caught by keySetEquals', () => {
  const entry = MCL04_ENTRIES[0]!;
  const encoded = encodeActionPayload(entry.valid_action_space, { marker_position: 7 });
  assert.notEqual(encoded, null);
  const withExtra = { ...encoded, extra_forbidden_key: 1 };
  assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
});
