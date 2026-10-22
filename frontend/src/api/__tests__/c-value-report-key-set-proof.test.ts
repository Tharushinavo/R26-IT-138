// AC 2: `action_payload`'s key set exactly equals `valid_action_space`'s, per template, across all
// six distinct int key names (`submitted_remainder`, `submitted_difference`, `submitted_total`,
// `submitted_sum`, `submitted_product`, `submitted_quotient`) and both boolean-bearing templates
// (C-TC-04, C-JB-04). Uses the shared `encodeActionPayload`/`keySetEquals` -- the same function
// every archetype submits through -- never a per-template key table in this test.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const APPROVED_TEMPLATE_IDS = [
  'C-TC-01',
  'C-TC-03',
  'C-TC-04',
  'C-JB-01',
  'C-JB-03',
  'C-JB-04',
  'C-EG-03',
  'C-SF-03',
] as const;

function valuesFor(entry: ExemplarEntry): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const [key, declaredType] of Object.entries(entry.valid_action_space)) {
    values[key] = declaredType === 'bool' ? true : 7;
  }
  return values;
}

for (const templateId of APPROVED_TEMPLATE_IDS) {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);

  test(`${templateId}: encoded payload key set exactly equals valid_action_space at every difficulty level`, () => {
    for (const entry of entries) {
      const values = valuesFor(entry);
      const encoded = encodeActionPayload(entry.valid_action_space, values);
      assert.notEqual(encoded, null, `${templateId} level ${entry.difficulty_level} failed to encode`);
      assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `${templateId} level ${entry.difficulty_level}`);
      assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
    }
  });

  test(`${templateId}: negative control -- missing a required key is rejected`, () => {
    const entry = entries[0]!;
    const values = valuesFor(entry);
    const [firstKey] = Object.keys(entry.valid_action_space);
    delete values[firstKey!];
    assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
  });

  test(`${templateId}: negative control -- an extra forbidden key is not carried into the encoded payload's key-set check`, () => {
    const entry = entries[0]!;
    const values = valuesFor(entry);
    values.telemetry_should_never_ride_along = 'x';
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    // encodeActionPayload only ever emits keys valid_action_space declares -- an extra input key is
    // silently not copied, not rejected. keySetEquals is what a caller uses to independently prove
    // extra_forbidden would be caught server-side too, by mutating the (correctly encoded) result.
    assert.notEqual(encoded, null);
    const withExtra = { ...encoded, extra_forbidden_key: 1 };
    assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
  });
}

test('C-TC-04 and C-JB-04 are the only two of the eight whose declared key set has size 2', () => {
  for (const templateId of APPROVED_TEMPLATE_IDS) {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    const keyCount = Object.keys(entry.valid_action_space).length;
    if (templateId === 'C-TC-04' || templateId === 'C-JB-04') {
      assert.equal(keyCount, 2, templateId);
    } else {
      assert.equal(keyCount, 1, templateId);
    }
  }
});

test('the six int key names across the eight templates are all distinct (proves one surface renders six different scene keys)', () => {
  const intKeyNames = new Set<string>();
  for (const templateId of APPROVED_TEMPLATE_IDS) {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    for (const [key, declaredType] of Object.entries(entry.valid_action_space)) {
      if (declaredType === 'int') intKeyNames.add(key);
    }
  }
  assert.equal(intKeyNames.size, 6);
});
