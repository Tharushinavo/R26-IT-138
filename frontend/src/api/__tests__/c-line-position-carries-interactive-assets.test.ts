// AC 8: interactive_assets is carried and ignored. Asserts the resolved spec carries it through
// untouched, and asserts it arrives {} for C-MCL-04's real exemplars, so a future population is a
// loud failure rather than a silent no-op.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveLinePositionSpec } from '@/src/features/c-session/archetypes/line-position-logic';

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

test('C-MCL-04: interactive_assets is {} on every real exemplar', () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-04');
  assert.equal(entries.length, 5);
  for (const entry of entries) {
    assert.deepEqual(entry.interactive_assets, {});
  }
});

test('the resolved spec carries interactive_assets through untouched', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-04')!;
  const task = makeTaskFromExemplar(entry);
  const spec = resolveLinePositionSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, task.interactive_assets);
});

test('a non-empty interactive_assets is still carried through, not stripped or defaulted', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-04')!;
  const task = makeTaskFromExemplar({ ...entry, interactive_assets: { some_future_field: 'x' } });
  const spec = resolveLinePositionSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, { some_future_field: 'x' });
});
