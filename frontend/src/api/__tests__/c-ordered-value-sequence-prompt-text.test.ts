// The never-composes guard (10a work order, "prompt_text -- relay verbatim"): the resolved spec's
// promptText must be character-identical to task.prompt_text, for entry and arrangement scenes
// alike, with a negative control proving a one-character difference is actually detected by the
// assertion below (not merely by construction).

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { resolveOrderedValueSequenceSpec } from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';

function makeEntryTask(promptText: string): CNextTaskResponse {
  return {
    blanks: 2,
    c_task_instance_id: 'task-1',
    difficulty_level: 3,
    game_family_id: 'C-GF-02',
    game_task_template_id: 'C-NP-03',
    interactive_assets: {},
    prompt_payload: { shown_sequence: [3, 8, 13], step: 5 },
    prompt_text: promptText,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { entered_values: 'list[int]' },
  };
}

function makeArrangeTask(promptText: string): CNextTaskResponse {
  return {
    blanks: null,
    c_task_instance_id: 'task-2',
    difficulty_level: 1,
    game_family_id: 'C-GF-02',
    game_task_template_id: 'C-NP-04',
    interactive_assets: {},
    prompt_payload: { direction: 'ascending', values: [3, 0, 2] },
    prompt_text: promptText,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-2',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { arranged_values: 'list[int]' },
  };
}

test('the entry scene spec carries prompt_text character-identical to the wire value', () => {
  const wireText = 'Keep counting the same way. Write what comes next.';
  const spec = resolveOrderedValueSequenceSpec(makeEntryTask(wireText));
  assert.notEqual(spec, null);
  assert.equal(spec!.promptText, wireText);
});

test('the arrangement scene spec carries prompt_text character-identical to the wire value', () => {
  const wireText = 'Put the numbers in order, from smallest to largest.';
  const spec = resolveOrderedValueSequenceSpec(makeArrangeTask(wireText));
  assert.notEqual(spec, null);
  assert.equal(spec!.promptText, wireText);
});

test('negative control: a one-character difference from the wire text is detected, not silently accepted', () => {
  const wireText = 'Keep counting the same way. Write what comes next.';
  const spec = resolveOrderedValueSequenceSpec(makeEntryTask(wireText));
  assert.notEqual(spec, null);

  // The mutated string differs by exactly one character (a trailing "!" instead of "."). If the
  // surface ever started composing/appending to prompt_text, spec.promptText could equal this
  // mutated string instead of the true wire value -- this assertion is what would catch that.
  const mutated = wireText.slice(0, -1) + '!';
  assert.notEqual(spec!.promptText, mutated);
  assert.equal(spec!.promptText, wireText);
});
