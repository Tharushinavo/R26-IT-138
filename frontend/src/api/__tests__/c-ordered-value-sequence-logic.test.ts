// resolveOrderedValueSequenceSpec's own tests (10a): correctness against the real exemplars for
// all four NP templates at every difficulty level, and every fail-closed path with a negative
// control proving it fires. Flat in src/api/__tests__/ -- the glob is non-recursive.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveOrderedValueSequenceSpec } from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';

function makeTask(overrides: Partial<CNextTaskResponse> = {}): CNextTaskResponse {
  return {
    blanks: 1,
    c_task_instance_id: 'task-1',
    difficulty_level: 1,
    game_family_id: 'C-GF-02',
    game_task_template_id: 'C-NP-01',
    interactive_assets: {},
    prompt_payload: { shown_sequence: [6, 7, 8] },
    prompt_text: 'Write what comes next in the pattern.',
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: { entered_values: 'list[int]' },
    ...overrides,
  };
}

function exemplarTasks(templateId: string): CNextTaskResponse[] {
  return EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId).map((entry) =>
    makeTask({
      blanks: entry.blanks,
      difficulty_level: entry.difficulty_level,
      game_task_template_id: entry.game_task_template_id,
      interactive_assets: entry.interactive_assets,
      prompt_payload: entry.prompt_payload,
      prompt_text: entry.prompt_text,
      valid_action_space: entry.valid_action_space,
    }),
  );
}

// --- real exemplars: all four templates, every difficulty level --------------------------------

for (const templateId of ['C-NP-01', 'C-NP-02', 'C-NP-03']) {
  test(`${templateId}: resolves to the entry scene at all five difficulty levels`, () => {
    const tasks = exemplarTasks(templateId);
    assert.equal(tasks.length, 5, `expected 5 exemplar levels for ${templateId}`);
    for (const task of tasks) {
      const spec = resolveOrderedValueSequenceSpec(task);
      if (spec === null) {
        assert.fail(`${templateId} level ${task.difficulty_level} failed to resolve`);
        return;
      }
      assert.equal(spec.scene, 'entry');
      if (spec.scene === 'entry') {
        assert.deepEqual(spec.shownSequence, task.prompt_payload.shown_sequence);
        assert.equal(spec.blanks, task.blanks);
        assert.equal(spec.entryKey, 'entered_values');
        assert.equal(spec.promptText, task.prompt_text);
        assert.deepEqual(spec.extraFields, []);
      }
    }
  });
}

test('C-NP-03: step is carried from prompt_payload at every difficulty level', () => {
  for (const task of exemplarTasks('C-NP-03')) {
    const spec = resolveOrderedValueSequenceSpec(task);
    if (spec === null) {
      assert.fail('expected a resolved spec');
      return;
    }
    if (spec.scene === 'entry') {
      assert.equal(spec.step, task.prompt_payload.step);
      assert.notEqual(spec.step, null);
    }
  }
});

test('C-NP-01/02: step is null when prompt_payload carries no step key', () => {
  for (const templateId of ['C-NP-01', 'C-NP-02']) {
    for (const task of exemplarTasks(templateId)) {
      const spec = resolveOrderedValueSequenceSpec(task);
      if (spec === null) {
        assert.fail('expected a resolved spec');
        return;
      }
      if (spec.scene === 'entry') {
        assert.equal(spec.step, null);
      }
    }
  }
});

test('the wire blanks value is 1 at difficulty 1-2 and 2 at difficulty 3-5 for NP-01/02/03', () => {
  for (const templateId of ['C-NP-01', 'C-NP-02', 'C-NP-03']) {
    for (const task of exemplarTasks(templateId)) {
      const spec = resolveOrderedValueSequenceSpec(task);
      if (spec === null) {
        assert.fail('expected a resolved spec');
        return;
      }
      if (spec.scene === 'entry') {
        const expected = task.difficulty_level <= 2 ? 1 : 2;
        assert.equal(spec.blanks, expected, `${templateId} level ${task.difficulty_level}`);
        assert.equal(spec.blanks, task.blanks);
      }
    }
  }
});

test('C-NP-04: resolves to the arrangement scene at all five difficulty levels', () => {
  const tasks = exemplarTasks('C-NP-04');
  assert.equal(tasks.length, 5);
  for (const task of tasks) {
    const spec = resolveOrderedValueSequenceSpec(task);
    if (spec === null) {
      assert.fail(`C-NP-04 level ${task.difficulty_level} failed to resolve`);
      return;
    }
    assert.equal(spec.scene, 'arrange');
    if (spec.scene === 'arrange') {
      assert.deepEqual(spec.values, task.prompt_payload.values);
      assert.equal(spec.direction, task.prompt_payload.direction);
      assert.equal(spec.arrangeKey, 'arranged_values');
      assert.equal(spec.promptText, task.prompt_text);
      assert.deepEqual(spec.extraFields, []);
    }
  }
});

test('C-NP-04 exemplars all carry blanks: null on the wire', () => {
  for (const task of exemplarTasks('C-NP-04')) {
    assert.equal(task.blanks, null);
  }
});

// --- fail-closed: prompt_text --------------------------------------------------------------------

test('resolveOrderedValueSequenceSpec returns null when prompt_text is empty', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ prompt_text: '' })), null);
});

test('resolveOrderedValueSequenceSpec returns null when prompt_text is not a string', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(makeTask({ prompt_text: 5 as unknown as string })),
    null,
  );
});

// --- fail-closed: valid_action_space ---------------------------------------------------------

test('returns null when valid_action_space declares no key', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ valid_action_space: {} })), null);
});

test('returns null when valid_action_space carries an unrecognised declared type', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(makeTask({ valid_action_space: { entered_values: 'float' } })),
    null,
  );
});

test('returns null when the list[int] key is under a name this archetype does not recognise', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(
      makeTask({
        prompt_payload: { shown_sequence: [1, 2, 3] },
        valid_action_space: { jumps: 'list[int]' },
      }),
    ),
    null,
  );
});

test('returns null when two list[int] keys are both present', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(
      makeTask({
        valid_action_space: { arranged_values: 'list[int]', entered_values: 'list[int]' },
      }),
    ),
    null,
  );
});

test('returns null when a list[str] key accompanies the scene key', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(
      makeTask({
        valid_action_space: { entered_values: 'list[int]', selected_ids: 'list[str]' },
      }),
    ),
    null,
  );
});

// --- fail-closed: entry scene prompt_payload / blanks -----------------------------------------

test('returns null when shown_sequence is absent', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ prompt_payload: {} })), null);
});

test('returns null when shown_sequence contains a non-integer element', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(makeTask({ prompt_payload: { shown_sequence: [1, 2.5, 3] } })),
    null,
  );
});

test('returns null when shown_sequence is empty', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ prompt_payload: { shown_sequence: [] } })), null);
});

test('returns null when shown_sequence exceeds the layout bound of 20', () => {
  const overLong = Array.from({ length: 21 }, (_, index) => index);
  assert.equal(
    resolveOrderedValueSequenceSpec(makeTask({ prompt_payload: { shown_sequence: overLong } })),
    null,
  );
});

test('a shown_sequence of exactly 20 elements still resolves (the bound is inclusive)', () => {
  const atBound = Array.from({ length: 20 }, (_, index) => index);
  assert.notEqual(
    resolveOrderedValueSequenceSpec(makeTask({ prompt_payload: { shown_sequence: atBound } })),
    null,
  );
});

test('returns null when step is present but not an integer', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(
      makeTask({ prompt_payload: { shown_sequence: [1, 2, 3], step: 2.5 } }),
    ),
    null,
  );
});

test('returns null when blanks is null for the entry scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ blanks: null })), null);
});

test('returns null when blanks is 0 or negative for the entry scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ blanks: 0 })), null);
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ blanks: -1 })), null);
});

test('returns null when blanks is a non-integer for the entry scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ blanks: 1.5 })), null);
});

test('returns null when blanks exceeds the robustness bound of 10 for the entry scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeTask({ blanks: 11 })), null);
});

test('blanks of exactly 10 still resolves (the bound is inclusive)', () => {
  assert.notEqual(resolveOrderedValueSequenceSpec(makeTask({ blanks: 10 })), null);
});

// --- fail-closed: arrangement scene prompt_payload / blanks -------------------------------------

function makeArrangeTask(overrides: Partial<CNextTaskResponse> = {}): CNextTaskResponse {
  return makeTask({
    blanks: null,
    game_task_template_id: 'C-NP-04',
    prompt_payload: { direction: 'ascending', values: [3, 0, 2] },
    prompt_text: 'Put the numbers in order, from smallest to largest.',
    valid_action_space: { arranged_values: 'list[int]' },
    ...overrides,
  });
}

test('returns null when values is absent for the arrangement scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeArrangeTask({ prompt_payload: { direction: 'ascending' } })), null);
});

test('returns null when direction is absent for the arrangement scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeArrangeTask({ prompt_payload: { values: [1, 2, 3] } })), null);
});

test('returns null when direction is an empty string', () => {
  assert.equal(
    resolveOrderedValueSequenceSpec(
      makeArrangeTask({ prompt_payload: { direction: '', values: [1, 2, 3] } }),
    ),
    null,
  );
});

test('returns null when blanks is non-null for the arrangement scene', () => {
  assert.equal(resolveOrderedValueSequenceSpec(makeArrangeTask({ blanks: 1 })), null);
});

test('the arrangement scene resolves when blanks is exactly null', () => {
  assert.notEqual(resolveOrderedValueSequenceSpec(makeArrangeTask()), null);
});

// --- own-property discipline: a hostile prompt_payload key ---------------------------------------

test('a prompt_payload key named "constructor" is not mistaken for a real field', () => {
  const task = makeTask({ prompt_payload: { constructor: [1, 2, 3] } });
  assert.equal(resolveOrderedValueSequenceSpec(task), null);
});
