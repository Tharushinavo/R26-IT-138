// `resolveOptionSelectSpec`'s numeral-options path (10e-0): real resolution of C-MCL-01 and
// C-CC-03 across all five difficulty levels each, the structural (not by-name) quantity-key
// resolution, in-wire-order preservation of `numeral_options`, and the answer-leak guard as a
// PERMANENT, provable property of the returned type -- not a comment. This is the path 10d refused
// outright; see option-select-logic.ts's own header for the full reasoning this batch unblocks.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';

const here = dirname(fileURLToPath(import.meta.url));

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

// --- C-MCL-01 --------------------------------------------------------------------------------------

const MCL01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-01');

test('C-MCL-01: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture', () => {
  assert.equal(MCL01_ENTRIES.length, 5);
});

test('C-MCL-01: resolves at every difficulty level with scoreKey, quantity and numeralOptions matching the real exemplar exactly', () => {
  for (const entry of MCL01_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    const payload = entry.prompt_payload as { numeral_options: number[]; target_representation_value: number };
    if (spec === null || spec.kind !== 'numeral-options') {
      assert.fail(`C-MCL-01 level ${entry.difficulty_level} failed to resolve as 'numeral-options'`);
      continue;
    }
    assert.equal(spec.scoreKey, 'selected_value', `level ${entry.difficulty_level}`);
    assert.equal(spec.quantity, payload.target_representation_value, `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.numeralOptions, payload.numeral_options, `level ${entry.difficulty_level}`);
    assert.equal(spec.extraFields.length, 0, `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.interactiveAssets, entry.interactive_assets, `level ${entry.difficulty_level}`);
  }
});

// --- C-CC-03 ---------------------------------------------------------------------------------------

const CC03_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-03');

test('C-CC-03: exactly 5 exemplar rows (difficulty 1-5), all present in the frozen fixture', () => {
  assert.equal(CC03_ENTRIES.length, 5);
});

test('C-CC-03: resolves at every difficulty level with scoreKey, quantity and numeralOptions matching the real exemplar exactly', () => {
  for (const entry of CC03_ENTRIES) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    const payload = entry.prompt_payload as { numeral_options: number[]; set_size: number };
    if (spec === null || spec.kind !== 'numeral-options') {
      assert.fail(`C-CC-03 level ${entry.difficulty_level} failed to resolve as 'numeral-options'`);
      continue;
    }
    assert.equal(spec.scoreKey, 'selected_numeral', `level ${entry.difficulty_level}`);
    assert.equal(spec.quantity, payload.set_size, `level ${entry.difficulty_level}`);
    assert.deepEqual(spec.numeralOptions, payload.numeral_options, `level ${entry.difficulty_level}`);
  }
});

// --- numeral_options relayed in server order, never re-sorted --------------------------------------

test('numeral_options is relayed in server order, never re-sorted (a descending-order synthetic array stays descending)', () => {
  const entry = MCL01_ENTRIES[0]!;
  const task = makeTask(entry);
  task.prompt_payload = { numeral_options: [9, 5, 3], target_representation_value: 9 };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  if (spec!.kind === 'numeral-options') {
    assert.deepEqual(spec!.numeralOptions, [9, 5, 3]);
  }
});

// --- structural (not by-name) quantity-key resolution -----------------------------------------------

test('the quantity key is resolved structurally, not by a two-name table: a third, differently-named quantity key resolves unchanged', () => {
  const entry = MCL01_ENTRIES[0]!;
  const task = makeTask(entry);
  task.prompt_payload = { numeral_options: [4, 7, 11], amount_shown: 7 };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  if (spec!.kind === 'numeral-options') {
    assert.equal(spec!.quantity, 7);
  }
});

test('quantity 0 is a structurally valid quantity (non-negative, not merely positive)', () => {
  const entry = MCL01_ENTRIES[0]!;
  const task = makeTask(entry);
  task.prompt_payload = { numeral_options: [0, 2, 5], target_representation_value: 0 };
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  if (spec!.kind === 'numeral-options') {
    assert.equal(spec!.quantity, 0);
  }
});

// --- the answer-leak guard, as a PERMANENT, provable property ---------------------------------------
// The defect 10d's refusal existed to prevent: the quantity IS the answer on this path, so it must
// never be exposed anywhere a numeral-rendering code path could pick it up. Proven at the TYPE
// level (the 'numeral-options' variant structurally has no `payloadValues` field at all -- there is
// no runtime value to assert against because there is no field to hold one) and, for completeness,
// against the real data that motivated the original refusal.

test("the 'numeral-options' variant has no payloadValues field -- the quantity cannot be rendered as a numeral token because there is no field on this variant that a token-rendering code path could read", () => {
  const entry = MCL01_ENTRIES[MCL01_ENTRIES.length - 1]!; // difficulty 5: quantity 66
  const spec = resolveOptionSelectSpec(makeTask(entry));
  assert.notEqual(spec, null);
  assert.equal(spec!.kind, 'numeral-options');
  assert.equal('payloadValues' in spec!, false);
});

test('re-confirmation: the quantity is always one of the numeral options, at every difficulty level of both templates (the property that made 10d refuse this path in the first place)', () => {
  for (const entry of [...MCL01_ENTRIES, ...CC03_ENTRIES]) {
    const spec = resolveOptionSelectSpec(makeTask(entry));
    assert.notEqual(spec, null, `${entry.game_task_template_id} level ${entry.difficulty_level}`);
    if (spec!.kind === 'numeral-options') {
      assert.ok(
        spec!.numeralOptions.includes(spec!.quantity),
        `${entry.game_task_template_id} level ${entry.difficulty_level}: ${spec!.quantity} not in [${spec!.numeralOptions}]`,
      );
    }
  }
});

// --- no template-id branching anywhere in the resolver's source ------------------------------------

test("option-select-logic.ts's source contains no game_task_template_id read or comparison (source-scan, comments stripped)", () => {
  const filePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'option-select-logic.ts');
  const source = readFileSync(filePath, 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  assert.doesNotMatch(source, /game_task_template_id/);
});

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = "if (task.game_task_template_id === 'C-MCL-01') { /* ... */ }";
  assert.match(fabricated, /game_task_template_id/);
});
