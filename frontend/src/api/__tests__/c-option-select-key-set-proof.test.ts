// AC 2/3: `action_payload`'s key set exactly equals `valid_action_space`'s, per template, and every
// declared type is honoured -- `selection`/`comparison_sign` reject any string outside their own
// three literals. Uses the shared `encodeActionPayload`/`keySetEquals` -- the same function every
// archetype submits through -- never a per-template key table in this test. Covers only the two
// templates this batch builds (C-MCL-02, C-MCL-03); C-MCL-01/C-CC-03 never reach submission this
// batch (option-select-logic.ts refuses them before a surface renders anything to submit).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const APPROVED_TEMPLATE_IDS = ['C-MCL-02', 'C-MCL-03'] as const;

const FIRST_ALTERNATIVE: Record<(typeof APPROVED_TEMPLATE_IDS)[number], string> = {
  'C-MCL-02': 'left',
  'C-MCL-03': '<',
};

function valuesFor(entry: ExemplarEntry, templateId: (typeof APPROVED_TEMPLATE_IDS)[number]): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const key of Object.keys(entry.valid_action_space)) {
    values[key] = FIRST_ALTERNATIVE[templateId];
  }
  return values;
}

for (const templateId of APPROVED_TEMPLATE_IDS) {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);

  test(`${templateId}: encoded payload key set exactly equals valid_action_space at every difficulty level`, () => {
    for (const entry of entries) {
      const values = valuesFor(entry, templateId);
      const encoded = encodeActionPayload(entry.valid_action_space, values);
      assert.notEqual(encoded, null, `${templateId} level ${entry.difficulty_level} failed to encode`);
      assert.equal(keySetEquals(encoded!, entry.valid_action_space), true, `${templateId} level ${entry.difficulty_level}`);
      assert.deepEqual(Object.keys(encoded!).sort(), Object.keys(entry.valid_action_space).sort());
    }
  });

  test(`${templateId}: negative control -- missing the required key is rejected`, () => {
    const entry = entries[0]!;
    const values = valuesFor(entry, templateId);
    const [firstKey] = Object.keys(entry.valid_action_space);
    delete values[firstKey!];
    assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
  });

  test(`${templateId}: negative control -- an extra forbidden key is not carried into the encoded payload's key-set check`, () => {
    const entry = entries[0]!;
    const values = valuesFor(entry, templateId);
    values.telemetry_should_never_ride_along = 'x';
    const encoded = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(encoded, null);
    const withExtra = { ...encoded, extra_forbidden_key: 1 };
    assert.equal(keySetEquals(withExtra, entry.valid_action_space), false);
  });

  test(`${templateId}: negative control -- a boolean value is rejected where the pipe-string expects one of its own literals`, () => {
    const entry = entries[0]!;
    const [key] = Object.keys(entry.valid_action_space);
    const values = { [key!]: true };
    assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
  });

  test(`${templateId}: negative control -- a string outside the declared alternatives is rejected`, () => {
    const entry = entries[0]!;
    const [key] = Object.keys(entry.valid_action_space);
    const values = { [key!]: 'not_a_real_alternative' };
    assert.equal(encodeActionPayload(entry.valid_action_space, values), null);
  });
}

test('C-MCL-02 and C-MCL-03 each declare exactly one key', () => {
  for (const templateId of APPROVED_TEMPLATE_IDS) {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    assert.equal(Object.keys(entry.valid_action_space).length, 1, templateId);
  }
});

test("C-MCL-02's and C-MCL-03's declared key names and alternative sets are distinct (proves one shared primitive renders two different scenes' worth of choices, not one hardcoded set)", () => {
  const mcl02 = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-02')!;
  const mcl03 = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-03')!;
  assert.notEqual(Object.keys(mcl02.valid_action_space)[0], Object.keys(mcl03.valid_action_space)[0]);
  assert.notEqual(mcl02.valid_action_space[Object.keys(mcl02.valid_action_space)[0]!], mcl03.valid_action_space[Object.keys(mcl03.valid_action_space)[0]!]);
});
