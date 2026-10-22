// Motor constancy for `named-integer-fields` (10f), mirroring
// c-object-set-action-motor-constancy.test.ts's own method and its stated limitation: nothing in
// this repository can mount a React Native tree and measure it, so "identical at difficulty 1-5"
// below means the geometry CONSTANTS referenced by the new files are literally the same values
// regardless of `difficulty_level` -- not that a rendered screen was measured and found unchanged.
//
// This archetype's specific motor question: field COUNT varies by template (2 for BT-01/03/04, 3
// for BT-02) and the VALUES entered grow with difficulty (target_number reaches 586 at C-BT-02 L5),
// but a field's own touch-target size and the keypad's own key size must never change regardless.
// Digit count entered tracks mathematical demand (how many digits the number has), never motor
// demand (the size of any one tap) -- the same doctrine `digit-keypad.tsx`'s own header states.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { KEYPAD_KEY_SIZE, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'),
  resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'),
  resolve(featureDir, 'primitives', 'named-field-row.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function codeReferencesDifficultyLevel(source: string): boolean {
  return /difficulty_level|difficultyLevel/.test(stripComments(source));
}

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

test('named-field-row.tsx imports TOKEN_TOUCH_TARGET_SIZE / HIT_SLOP from motor-constants.ts, not a second set', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'named-field-row.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /TOKEN_TOUCH_TARGET_SIZE/);
  assert.match(source, /HIT_SLOP/);
});

test('named-integer-fields-surface.tsx reuses the shared DigitKeypad rather than a second keypad implementation (one shared instance retargeted per focused field, per the header)', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/primitives\/digit-keypad'/);
  const keypadJsxCount = (source.match(/<DigitKeypad\b/g) ?? []).length;
  assert.equal(keypadJsxCount, 1);
});

test('TOKEN_TOUCH_TARGET_SIZE, TOKEN_SPACING, KEYPAD_KEY_SIZE are plain values, not functions', () => {
  assert.equal(typeof TOKEN_TOUCH_TARGET_SIZE, 'number');
  assert.equal(typeof TOKEN_SPACING, 'number');
  assert.equal(typeof KEYPAD_KEY_SIZE, 'number');
});

test("named-integer-fields-logic.ts's max-fields bound is a plain literal constant, not a function of any payload value", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'), 'utf-8');
  assert.match(source, /MAX_FIELDS\s*=\s*\d+/);
});

test("C-BT-02's target_number grows across difficulty 1-5, yet the field COUNT stays fixed at 3 and no field's own geometry is touched by this variation", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-BT-02');
  assert.equal(entries.length, 5);
  const values = entries.map((entry) => (entry.prompt_payload as { target_number: number }).target_number);
  assert.notEqual(Math.min(...values), Math.max(...values), 'target_number should vary across levels in the real data');
  for (const entry of entries) {
    assert.deepEqual(Object.keys(entry.valid_action_space).sort(), ['hundreds', 'ones', 'tens']);
  }

  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/primitives\/named-field-row'/);
  // Two legitimate call sites (10g): the generic wrapped row (mapped over orderedFields, used by
  // C-BT-01..04) and C-EG-02's own equation row (`EquationFieldsRow`'s `renderBox` helper, called
  // three times at runtime for cols/rows/submitted_product but written once in source) -- neither is
  // one-per-field hardcoded.
  const boxJsxCount = (source.match(/<NamedFieldBox\b/g) ?? []).length;
  assert.equal(boxJsxCount, 2, 'exactly two NamedFieldBox JSX call sites: the generic row and the equation row\'s shared renderBox helper');
});

test('named-integer-fields-logic.ts MAX_FIELDS comfortably exceeds the real maximum field count observed across all four C-BT-* templates', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'), 'utf-8');
  const match = source.match(/MAX_FIELDS\s*=\s*(\d+)/);
  assert.notEqual(match, null);
  const bound = Number.parseInt(match![1]!, 10);

  const btEntries = EXEMPLAR_ENTRIES.filter((entry) => ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04'].includes(entry.game_task_template_id));
  const maxFields = Math.max(...btEntries.map((entry) => Object.keys(entry.valid_action_space).length));
  assert.ok(bound > maxFields, `expected MAX_FIELDS > ${maxFields}, got ${bound}`);
});
