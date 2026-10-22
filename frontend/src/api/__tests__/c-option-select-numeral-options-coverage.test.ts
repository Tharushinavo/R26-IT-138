// Remaining acceptance criteria for the numeral-options scene (10e-0), bundled: prompt_text
// character-identity, interactive_assets carry-through, no representation_mode reference, motor
// constancy for the new scene (geometry from motor-constants.ts, no difficulty_level reference,
// the one-tap-plus-SUBMIT cost assertion), and C-MCL-04/line-position's own regression proof
// (untouched by this batch). Nothing here can mount a component tree -- these are resolver-level
// and source-scan proofs, matching every other archetype's own test method in this codebase.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
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

const NEW_OR_CHANGED_FILES = [
  resolve(featureDir, 'archetypes', 'option-select-logic.ts'),
  resolve(featureDir, 'archetypes', 'option-select-surface.tsx'),
  resolve(featureDir, 'primitives', 'object-quantity-display.tsx'),
];

// --- prompt_text character identity ------------------------------------------------------------------

for (const templateId of ['C-MCL-01', 'C-CC-03']) {
  test(`${templateId}: spec.promptText is character-identical to task.prompt_text at every difficulty level`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      const spec = resolveOptionSelectSpec(makeTask(entry));
      assert.notEqual(spec, null);
      assert.equal(spec!.promptText, entry.prompt_text);
      assert.equal(spec!.promptText.length, entry.prompt_text.length);
    }
  });
}

test('negative control: a one-character-altered prompt_text is NOT reported as identical (proves the check is not vacuous)', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-01')!;
  const spec = resolveOptionSelectSpec(makeTask(entry));
  assert.notEqual(spec, null);
  // Swap the final character for a DIFFERENT one. Appending '?' unconditionally stopped
  // altering anything once prompts began ending in '?' themselves (the 2026-09-28 ESL
  // rewrite), so the control passed vacuously -- the exact failure it exists to rule out.
  const lastCharacter = entry.prompt_text.slice(-1);
  const alteredPromptText = `${entry.prompt_text.slice(0, -1)}${lastCharacter === '?' ? '.' : '?'}`;
  assert.notEqual(spec!.promptText, alteredPromptText);
});

// --- interactive_assets carried, ignored --------------------------------------------------------------

for (const templateId of ['C-MCL-01', 'C-CC-03']) {
  test(`${templateId}: interactive_assets is {} on every real exemplar`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    for (const entry of entries) {
      assert.deepEqual(entry.interactive_assets, {});
    }
  });
}

test('the resolved spec carries interactive_assets through untouched, even when non-empty', () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-01')!;
  const task = makeTask({ ...entry, interactive_assets: { some_future_field: 'x' } });
  const spec = resolveOptionSelectSpec(task);
  assert.notEqual(spec, null);
  assert.deepEqual(spec!.interactiveAssets, { some_future_field: 'x' });
});

// --- no representation_mode reference ------------------------------------------------------------------

for (const filePath of NEW_OR_CHANGED_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references representation_mode`, () => {
    const source = stripComments(readFileSync(filePath, 'utf-8'));
    assert.doesNotMatch(source, /representation_mode/);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'if (task.representation_mode === "x") { /* ... */ }';
  assert.match(stripComments(fabricated), /representation_mode/);
});

// --- motor constancy: geometry from motor-constants.ts, no difficulty_level reference ------------------

for (const filePath of NEW_OR_CHANGED_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references difficulty_level`, () => {
    const source = stripComments(readFileSync(filePath, 'utf-8'));
    assert.doesNotMatch(source, /difficulty_level|difficultyLevel/);
  });
}

test('option-select-surface.tsx renders ObjectQuantityDisplay for the numeral-options scene, deriving no geometry of its own for it', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'option-select-surface.tsx'), 'utf-8');
  assert.match(source, /import \{ ObjectQuantityDisplay \}/);
  assert.match(source, /<ObjectQuantityDisplay count=\{spec\.quantity\}/);
});

// --- interaction cost: one tap (an OptionChoiceRow selection) + SUBMIT, at every difficulty -----------

for (const templateId of ['C-MCL-01', 'C-CC-03']) {
  test(`${templateId}: submitting an answer costs exactly one OptionChoiceRow selection at every difficulty level (no extra fields in real data, no accumulation step)`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    for (const entry of entries) {
      const spec = resolveOptionSelectSpec(makeTask(entry));
      assert.notEqual(spec, null, `${templateId} level ${entry.difficulty_level}`);
      assert.equal(spec!.extraFields.length, 0, `${templateId} level ${entry.difficulty_level}`);
    }
  });
}

test('option-select-surface.tsx gates SUBMIT on nothing but the single selection (plus any declared extra field) for the numeral-options scene too -- no counter, no minimum-taps requirement tied to quantity', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'option-select-surface.tsx'), 'utf-8');
  assert.match(source, /selected !== null/);
  assert.doesNotMatch(source, /tapCount|minTaps|requiredTaps/);
});

// --- C-MCL-04 / line-position: untouched, still fails closed the same way -----------------------------

test("C-MCL-04: resolveArchetype still yields 'line-position' -- untouched by this batch, unregistered in SURFACE_TABLE (see c-mcl-family-surface-registration.test.ts for the full plan-level proof)", () => {
  const entry = EXEMPLAR_ENTRIES.find((candidate) => candidate.game_task_template_id === 'C-MCL-04')!;
  assert.equal(resolveArchetype('C-MCL-04', entry.valid_action_space), 'line-position');
});
