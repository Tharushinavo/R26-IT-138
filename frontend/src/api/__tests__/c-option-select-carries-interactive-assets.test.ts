// AC 8: interactive_assets is carried and ignored. Asserts the resolved spec carries it through
// untouched, and asserts it arrives {} for C-MCL-02/C-MCL-03's real exemplars, so a future
// population is a loud failure rather than a silent no-op -- same rationale
// c-line-traversal-carries-interactive-assets.test.ts applies for 10c.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';

function makeTaskFromExemplar(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-03',
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

for (const templateId of ['C-MCL-02', 'C-MCL-03']) {
  test(`${templateId}: interactive_assets is {} on every real exemplar`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      assert.deepEqual(entry.interactive_assets, {});
    }
  });
}

test('the resolved spec carries interactive_assets through untouched', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-02')!;
  const task = makeTaskFromExemplar(entry);
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, task.interactive_assets);
});

test('a non-empty interactive_assets is still carried through, not stripped or defaulted', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-02')!;
  const task = makeTaskFromExemplar({ ...entry, interactive_assets: { some_future_field: 'x' } });
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, { some_future_field: 'x' });
});
