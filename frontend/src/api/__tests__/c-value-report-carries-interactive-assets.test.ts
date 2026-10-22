// AC 8: interactive_assets is carried and ignored. Asserts the resolved spec carries it through
// untouched, and asserts it arrives {} for all eight approved templates' real exemplars, so a
// future population is a loud failure rather than a silent no-op -- same rationale
// c-ordered-value-sequence-carries-interactive-assets.test.ts applies for 10a.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';

const APPROVED_TEMPLATE_IDS = [
  'C-TC-01',
  'C-TC-03',
  'C-TC-04',
  'C-JB-01',
  'C-JB-03',
  'C-JB-04',
  'C-EG-03',
  'C-SF-03',
];

function makeTaskFromExemplar(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
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

for (const templateId of APPROVED_TEMPLATE_IDS) {
  test(`${templateId}: interactive_assets is {} on every real exemplar`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      assert.deepEqual(entry.interactive_assets, {});
    }
  });
}

test('the resolved spec carries interactive_assets through untouched', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-TC-01')!;
  const task = makeTaskFromExemplar(entry);
  const spec = resolveValueReportSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, task.interactive_assets);
});

test('a non-empty interactive_assets is still carried through, not stripped or defaulted', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-TC-01')!;
  const task = makeTaskFromExemplar({ ...entry, interactive_assets: { some_future_field: 'x' } });
  const spec = resolveValueReportSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, { some_future_field: 'x' });
});
