// `resolveOptionSelectSpec`: resolution over the pipe-string path (C-MCL-02, C-MCL-03, 10d) and,
// as of 10e-0, real resolution of the `integer-field` / numeral-options path too (C-MCL-01,
// C-CC-03 -- see c-option-select-numeral-options-resolution.test.ts for that path's own dedicated
// coverage; the three tests below that used to assert its REFUSAL now assert real resolution
// instead, per the 10e-0 ruling that unblocked it). C-CC-04 (pipe-string path) is exercised here
// too, since its non-numeric `trial_type` payload value is the one thing holding it shut.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

function makeTask(entry: ExemplarEntry): CNextTaskResponse {
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

// --- C-MCL-02: left|right|equal ------------------------------------------------------------------

const MCL02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-02');

test('C-MCL-02: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture', () => {
  assert.equal(MCL02_ENTRIES.length, 5);
});

test('C-MCL-02: resolves at every difficulty level with scoreKey/alternatives and both payload tokens', () => {
  for (const entry of MCL02_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    if (spec === null || spec.kind !== 'choice') {
      assert.fail(`C-MCL-02 level ${entry.difficulty_level} failed to resolve as 'choice'`);
      continue;
    }
    assert.equal(spec.scoreKey, 'selection', `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.alternatives, ['left', 'right', 'equal'], `level ${entry.difficulty_level}`);
    assert.deepEqual(
      spec.payloadValues.map((value: { key: string }) => value.key),
      ['left_count', 'right_count'],
      `level ${entry.difficulty_level}`,
    );
    assert.equal(spec.extraFields.length, 0, `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.interactiveAssets, entry.interactive_assets, `level ${entry.difficulty_level}`);
  }
});

// --- C-MCL-03: <|>|= -------------------------------------------------------------------------------

const MCL03_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-03');

test('C-MCL-03: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture', () => {
  assert.equal(MCL03_ENTRIES.length, 5);
});

test('C-MCL-03: resolves at every difficulty level with scoreKey/alternatives and both payload tokens', () => {
  for (const entry of MCL03_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    if (spec === null || spec.kind !== 'choice') {
      assert.fail(`C-MCL-03 level ${entry.difficulty_level} failed to resolve as 'choice'`);
      continue;
    }
    assert.equal(spec.scoreKey, 'comparison_sign', `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.alternatives, ['<', '>', '='], `level ${entry.difficulty_level}`);
    assert.deepEqual(
      spec.payloadValues.map((value: { key: string }) => value.key),
      ['value_a', 'value_b'],
      `level ${entry.difficulty_level}`,
    );
  }
});

// --- the integer-field / numeral-options path (C-MCL-01, C-CC-03) ---------------------------------
// Unblocked in 10e-0. Full resolution coverage (scoreKey, quantity, numeralOptions, in-wire-order,
// the answer-leak guard) lives in c-option-select-numeral-options-resolution.test.ts; the three
// tests below are the ones this batch legitimately CHANGES from 10d, kept here so the change is
// visible in the same file and against the same fixtures the original refusal was proven against.

const MCL01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-01');
const CC03_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-03');

test('re-verification (owner ruling 2, 2026-08-26): target_representation_value is present inside numeral_options at every C-MCL-01 difficulty level', () => {
  assert.equal(MCL01_ENTRIES.length, 5);
  for (const entry of MCL01_ENTRIES) {
    const payload = entry.prompt_payload as { numeral_options: number[]; target_representation_value: number };
    assert.ok(
      payload.numeral_options.includes(payload.target_representation_value),
      `level ${entry.difficulty_level}: ${payload.target_representation_value} not in [${payload.numeral_options}]`,
    );
  }
});

test('re-verification (owner ruling 2, 2026-08-26): set_size is present inside numeral_options at every C-CC-03 difficulty level', () => {
  assert.equal(CC03_ENTRIES.length, 5);
  for (const entry of CC03_ENTRIES) {
    const payload = entry.prompt_payload as { numeral_options: number[]; set_size: number };
    assert.ok(
      payload.numeral_options.includes(payload.set_size),
      `level ${entry.difficulty_level}: ${payload.set_size} not in [${payload.numeral_options}]`,
    );
  }
});

test("C-MCL-01 resolves at every difficulty level (10e-0: was 'refuses at every difficulty level' in 10d; the integer-field path is unblocked now)", () => {
  for (const entry of MCL01_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    assert.notEqual(spec, null, `level ${entry.difficulty_level}`);
    assert.equal(spec!.kind, 'numeral-options', `level ${entry.difficulty_level}`);
  }
});

test("C-CC-03 resolves at every difficulty level (10e-0: was 'refuses at every difficulty level' in 10d; same unblock, no template-id list involved either way)", () => {
  for (const entry of CC03_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    assert.notEqual(spec, null, `level ${entry.difficulty_level}`);
    assert.equal(spec!.kind, 'numeral-options', `level ${entry.difficulty_level}`);
  }
});

test("resolution is keyed on declared type alone: a synthetic differently-named int key on an otherwise C-MCL-02-shaped task resolves too (10e-0: was 'the refusal is keyed on declared type alone... refuses too' in 10d; the underlying type-not-name discipline is unchanged, only the outcome for this binding kind is)", () => {
  const task = makeTask(MCL02_ENTRIES[0]!);
  task.valid_action_space = { chosen_value: 'int' };
  task.prompt_payload = { numeral_options: [1, 2, 3], target_representation_value: 2 };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'numeral-options');
  if (spec!.kind === 'numeral-options') {
    assert.equal(spec!.scoreKey, 'chosen_value');
    assert.equal(spec!.quantity, 2);
    assert.deepEqual(spec!.numeralOptions, [1, 2, 3]);
  }
});

test('a synthetic differently-named pipe-string key still resolves (proves classification is type-derived, not a hardcoded key name)', () => {
  const task = makeTask(MCL02_ENTRIES[0]!);
  task.valid_action_space = { verdict: 'up|down|same' };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'choice');
  assert.equal(spec!.scoreKey, 'verdict');
  if (spec!.kind === 'choice') {
    assert.deepEqual(spec!.alternatives, ['up', 'down', 'same']);
  }
});

// --- C-CC-04: pipe-string path, held shut by the non-numeric-payload guard -------------------------

const CC04_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-04');

test("C-CC-04's real payload always carries a non-numeric trial_type value, at every difficulty level", () => {
  assert.equal(CC04_ENTRIES.length, 5);
  for (const entry of CC04_ENTRIES) {
    const payload = entry.prompt_payload as { trial_type: unknown };
    assert.equal(typeof payload.trial_type, 'string');
  }
});

test('C-CC-04 fails closed at every difficulty level -- the generic non-numeric-payload guard is what holds this shut (no code branches on trial_type or on C-CC-04 by name)', () => {
  for (const entry of CC04_ENTRIES) {
    assert.equal(resolveOptionSelectSpec(makeTask(entry)), null, `level ${entry.difficulty_level}`);
  }
});

test('isolates the guard from C-CC-04\'s specific shape: an otherwise-identical task with trial_type replaced by a number would resolve (proves it is the non-numeric VALUE that refuses it, not the key name or the template id)', () => {
  const entry = CC04_ENTRIES[0]!;
  const task = makeTask(entry);
  task.prompt_payload = { ...(entry.prompt_payload as Record<string, unknown>), trial_type: 1 };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
});

// --- registry table agreement (unaffected by this batch, confirmed not drifted) --------------------

for (const templateId of ['C-MCL-02', 'C-MCL-03', 'C-MCL-01', 'C-CC-03', 'C-CC-04']) {
  test(`${templateId}: still resolves to 'option-select' in the archetype table`, () => {
    const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === templateId)!;
    assert.equal(resolveArchetype(templateId, entry.valid_action_space), 'option-select');
  });
}
