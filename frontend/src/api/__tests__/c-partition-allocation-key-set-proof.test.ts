// AC 2: encoded `action_payload`'s key set exactly equals `valid_action_space`'s for C-EG-01 and
// C-SF-01, across every difficulty level. Uses the shared `encodeActionPayload`/`keySetEquals` --
// the same function every archetype submits through -- never a per-template key table here.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const TEMPLATE_IDS = ['C-EG-01', 'C-SF-01'];

for (const id of TEMPLATE_IDS) {
  test(`${id}: encoded payload key set exactly equals valid_action_space at every difficulty level`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === id);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      const collectionKey = Object.keys(entry.valid_action_space)[0]!;
      const values = { [collectionKey]: [1, 2, 3] };
      const encoded = encodeActionPayload(entry.valid_action_space, values);
      assert.notEqual(encoded, null, `${id} level ${entry.difficulty_level} failed to encode`);
      assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `${id} level ${entry.difficulty_level}`);
      assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
    }
  });
}

test('an empty list still encodes at the encoder layer (the surface, not the encoder, gates on completeness -- see partition-allocation-surface.tsx)', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  const encoded = encodeActionPayload(entry.valid_action_space, { groups: [] });
  assert.notEqual(encoded, null);
  assert.deepEqual(encoded!.groups, []);
});

test('negative control: a missing collection key is rejected', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-SF-01')!;
  assert.equal(encodeActionPayload(entry.valid_action_space, {}), null);
});

test('negative control: list[int] rejects a string element', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  const values = { groups: [1, 'two'] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: list[int] rejects a fractional element', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  const values = { groups: [1, 2.5] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: list[int] rejects a boolean element (the coercion trap)', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  const values = { groups: [1, true] };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: a non-array value is rejected', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-SF-01')!;
  const values = { allocations: '1,2,3' };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: an extra forbidden key is caught by keySetEquals', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-EG-01')!;
  const encoded = encodeActionPayload(entry.valid_action_space, { groups: [1, 2] });
  assert.notEqual(encoded, null);
  const withExtra = { ...encoded, extra_forbidden_key: 1 };
  assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
});
