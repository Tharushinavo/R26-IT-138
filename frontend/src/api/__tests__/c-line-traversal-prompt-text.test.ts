// AC 4: the rendered question is character-identical to `task.prompt_text`, with a one-character
// negative control.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveLineTraversalSpec } from '@/src/features/c-session/archetypes/line-traversal-logic';

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-05',
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

test('C-JB-02: spec.promptText is character-identical to task.prompt_text at every difficulty level', () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-JB-02');
  assert.equal(entries.length, 5);
  for (const entry of entries) {
    const spec = resolveLineTraversalSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.equal(spec!.promptText, entry.prompt_text);
    assert.equal(spec!.promptText.length, entry.prompt_text.length);
  }
});

test('negative control: a one-character-altered prompt_text is NOT reported as identical (proves the check is not vacuous)', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-JB-02')!;
  const task = makeTask(entry);
  const spec = resolveLineTraversalSpec(task);
  assert.notEqual(spec, null);
  // Swap the final character for a DIFFERENT one. This used to append '?' unconditionally, which
  // silently stopped altering anything once prompts began ending in '?' themselves (the 2026-09-28
  // ESL rewrite) -- the "altered" string was identical to the original and the control passed
  // vacuously, which is the exact failure it exists to rule out.
  const lastCharacter = entry.prompt_text.slice(-1);
  const alteredPromptText = `${entry.prompt_text.slice(0, -1)}${lastCharacter === '?' ? '.' : '?'}`;
  assert.notEqual(spec!.promptText, alteredPromptText);
});
