// Motor constancy for `option-select` (10d), mirroring `c-value-report-motor-constancy.test.ts`'s
// own method and its stated limitation: nothing in this repository can mount a React Native tree
// and measure it, so "identical at difficulty 1-5" below means the geometry CONSTANTS referenced by
// the new files are literally the same values regardless of `difficulty_level` -- not that a
// rendered screen was measured and found unchanged.
//
// This batch's own motor question is narrower than the work order originally posed: the
// `numeral_options` 3->5 growth case is deferred along with the `integer-field` path it belongs to
// (owner ruling, 2026-08-26 -- see option-select-logic.ts's header). What remains to prove for the
// two templates actually built is that a FIXED three-alternative row (`left|right|equal`,
// `<|>|=`, unchanged across all five difficulty levels for both) uses constant geometry, and that
// selecting an answer costs exactly one tap plus SUBMIT at every level -- the property
// `line-position` (10d's C-MCL-04) turned out to violate, and worth asserting here where it holds.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'option-select-logic.ts'),
  resolve(featureDir, 'archetypes', 'option-select-surface.tsx'),
  resolve(featureDir, 'primitives', 'option-choice-row.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function codeReferencesDifficultyLevel(source: string): boolean {
  return /difficulty_level|difficultyLevel/.test(stripComments(source));
}

// --- structural proof 1: none of the new files read difficulty_level at all -----------------------

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references difficulty_level`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeReferencesDifficultyLevel(source), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const size = base + task.difficulty_level;';
  assert.equal(codeReferencesDifficultyLevel(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never scale with difficulty_level\nconst size = base;';
  assert.equal(codeReferencesDifficultyLevel(commentOnly), false);
});

// --- structural proof 2: option-choice-row.tsx derives geometry from motor-constants.ts, never a bare literal ---

test('option-choice-row.tsx derives its option touch target from TOKEN_TOUCH_TARGET_SIZE / TOKEN_SPACING (the same constants value-report-surface.tsx uses for its own tokens), never a bare literal', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'option-choice-row.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /TOKEN_TOUCH_TARGET_SIZE/);
  assert.match(source, /TOKEN_SPACING/);
  // The private literal GenericExtraField's own choice row used (`minHeight: 48`) must not have been
  // reproduced in this file's actual STYLE RULES -- checked on comment-stripped source, since the
  // header comment above legitimately discusses that literal by name as the thing being avoided.
  const codeOnly = stripComments(source);
  assert.doesNotMatch(codeOnly, /minHeight:\s*48/);
  assert.doesNotMatch(codeOnly, /minWidth:\s*48/);
});

test('TOKEN_TOUCH_TARGET_SIZE, TOKEN_SPACING, HIT_SLOP are plain values, not functions', () => {
  assert.equal(typeof TOKEN_TOUCH_TARGET_SIZE, 'number');
  assert.equal(typeof TOKEN_SPACING, 'number');
  assert.equal(typeof HIT_SLOP, 'object');
});

test('option-choice-row.tsx wraps rather than compresses: its row style declares flexWrap, never a shrink-to-fit rule', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'option-choice-row.tsx'), 'utf-8');
  assert.match(source, /flexWrap:\s*'wrap'/);
});

// --- structural proof 3: both real templates declare a FIXED three-alternative set at every level ---

for (const templateId of ['C-MCL-02', 'C-MCL-03']) {
  test(`${templateId}: declares exactly three alternatives, identical at difficulty 1 and difficulty 5 (no growth for this batch's two templates)`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);
    const alternativeSets = entries.map((entry) => {
      const [declaredType] = Object.values(entry.valid_action_space);
      return declaredType!.split('|');
    });
    for (const alternatives of alternativeSets) {
      assert.equal(alternatives.length, 3, templateId);
    }
    assert.deepEqual(alternativeSets[0], alternativeSets[4], `${templateId}: level 1 vs level 5 alternative set`);
  });
}

// --- structural proof 4: interaction cost -- one tap + SUBMIT at every difficulty ------------------

test('option-select-surface.tsx gates SUBMIT on nothing but the single OptionChoiceRow selection (plus any declared extra field) -- no accumulation step exists that could make cost track difficulty', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'option-select-surface.tsx'), 'utf-8');
  // canSubmit depends only on `selected !== null` and the extraFields hasOwnProperty check -- no
  // counter, no minimum-taps requirement, no loop bound tied to any payload value.
  assert.match(source, /selected !== null/);
  assert.doesNotMatch(source, /tapCount|minTaps|requiredTaps/);
});

for (const templateId of ['C-MCL-02', 'C-MCL-03']) {
  test(`${templateId}: submitting an answer costs exactly one OptionChoiceRow selection at every difficulty level (the property C-MCL-04's line-position violates)`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    for (const entry of entries) {
      const spec = resolveOptionSelectSpec({
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
      });
      assert.notEqual(spec, null, `${templateId} level ${entry.difficulty_level}`);
      // Exactly one scene key (the selection itself) and zero extra fields in real data at every
      // level -- so the only interaction between "no selection" and "SUBMIT enabled" is one tap on
      // one option, regardless of difficulty.
      assert.equal(spec!.extraFields.length, 0, `${templateId} level ${entry.difficulty_level}`);
    }
  });
}
