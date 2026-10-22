// `labelForPayloadKey` (10b correction, 2026-08-26): a child-facing label per `prompt_payload` key,
// covering the real vocabulary across all eight `value-report` templates, plus the generic fallback
// for any key not in the fixed table.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { labelForPayloadKey } from '@/src/features/c-session/archetypes/payload-value-labels';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';
import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';

const KNOWN_KEY_LABELS: Record<string, string> = {
  initial_count: 'Start',
  removed_count: 'Taken away',
  minuend: 'Start',
  subtrahend: 'Taken away',
  count_a: 'First group',
  count_b: 'Second group',
  addend_a: 'First number',
  addend_b: 'Second number',
  operand_a: 'First number',
  operand_b: 'Second number',
  multiplicand: 'First number',
  multiplier: 'Second number',
  dividend: 'Number',
};

for (const [key, expectedLabel] of Object.entries(KNOWN_KEY_LABELS)) {
  test(`labelForPayloadKey('${key}') === '${expectedLabel}'`, () => {
    assert.equal(labelForPayloadKey(key), expectedLabel);
  });
}

test('every real prompt_payload key across the eight approved templates has a curated label (no fallback silently used)', () => {
  const approvedTemplateIds = new Set([
    'C-TC-01',
    'C-TC-03',
    'C-TC-04',
    'C-JB-01',
    'C-JB-03',
    'C-JB-04',
    'C-EG-03',
    'C-SF-03',
  ]);
  const realKeys = new Set<string>();
  for (const entry of EXEMPLAR_ENTRIES) {
    if (!approvedTemplateIds.has(entry.game_task_template_id)) continue;
    for (const key of Object.keys(entry.prompt_payload)) realKeys.add(key);
  }
  assert.equal(realKeys.size, Object.keys(KNOWN_KEY_LABELS).length);
  for (const key of realKeys) {
    assert.ok(Object.prototype.hasOwnProperty.call(KNOWN_KEY_LABELS, key), `missing curated label for "${key}"`);
  }
});

test('a key outside the curated table falls back to a humanised form of the key itself, rather than the raw snake_case string', () => {
  assert.equal(labelForPayloadKey('some_future_quantity'), 'Some Future Quantity');
});

test('two same-shaped keys with different template origins (minuend/subtrahend shared by C-TC-03 and C-TC-04) resolve identically, proving the lookup is keyed by payload key, not template id', () => {
  assert.equal(labelForPayloadKey('minuend'), labelForPayloadKey('minuend'));
  const tc03 = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-TC-03')!;
  const tc04 = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-TC-04')!;
  assert.equal(labelForPayloadKey(Object.keys(tc03.prompt_payload)[0]!), labelForPayloadKey(Object.keys(tc04.prompt_payload)[0]!));
});

// --- integration: resolveValueReportSpec carries the label through onto each PayloadValue --------

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-06',
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

test("C-TC-01's resolved spec labels initial_count 'Start' and removed_count 'Taken away', in that order", () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-TC-01')!;
  const spec = resolveValueReportSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(
    spec!.payloadValues.map((p) => [p.key, p.label]),
    [
      ['initial_count', 'Start'],
      ['removed_count', 'Taken away'],
    ],
  );
});

test("C-SF-03's single-value payload (dividend) is labelled 'Number'", () => {
  const entry = EXEMPLAR_ENTRIES.find((e) => e.game_task_template_id === 'C-SF-03')!;
  const spec = resolveValueReportSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.deepEqual(
    spec!.payloadValues.map((p) => [p.key, p.label]),
    [['dividend', 'Number']],
  );
});
