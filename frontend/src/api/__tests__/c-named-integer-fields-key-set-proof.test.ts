// AC 2: encoded `action_payload`'s key set exactly equals `valid_action_space`'s for all four
// C-BT-* templates, across every difficulty level. Uses the shared `encodeActionPayload`/
// `keySetEquals` -- the same function every archetype submits through -- never a per-template key
// table here.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const BT_TEMPLATE_IDS = ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04'];

for (const id of BT_TEMPLATE_IDS) {
  test(`${id}: encoded payload key set exactly equals valid_action_space at every difficulty level`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === id);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      const values: Record<string, number> = {};
      for (const key of Object.keys(entry.valid_action_space)) values[key] = 1;
      const encoded = encodeActionPayload(entry.valid_action_space, values);
      assert.notEqual(encoded, null, `${id} level ${entry.difficulty_level} failed to encode`);
      assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `${id} level ${entry.difficulty_level}`);
      assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
    }
  });
}

test('a value of 0 for every field still encodes (the client never enforces a minimum)', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-01')!;
  const encoded = encodeActionPayload(entry.valid_action_space, { tens: 0, ones: 0 });
  assert.notEqual(encoded, null);
  assert.equal(encoded!.tens, 0);
  assert.equal(encoded!.ones, 0);
});

test('negative control: a missing field is rejected', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-02')!;
  const values: Record<string, unknown> = { hundreds: 1, tens: 2 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: int rejects a fractional value', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-01')!;
  const values = { tens: 1.5, ones: 2 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: int rejects a boolean (the coercion trap)', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-01')!;
  const values = { tens: true, ones: 2 };
  assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
});

test('negative control: an extra forbidden key is caught by keySetEquals', () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-BT-03')!;
  const encoded = encodeActionPayload(entry.valid_action_space, { post_tens: 1, post_ones: 2 });
  assert.notEqual(encoded, null);
  const withExtra = { ...encoded, extra_forbidden_key: 1 };
  assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
});
