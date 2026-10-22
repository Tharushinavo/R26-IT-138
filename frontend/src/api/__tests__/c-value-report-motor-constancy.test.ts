// Motor constancy for `value-report` (10b), mirroring `c-ordered-value-sequence-motor-constancy
// .test.ts`'s own method and its stated limitation: nothing in this repository can mount a React
// Native tree and measure it, so "identical at difficulty 1-5" below means the geometry CONSTANTS
// referenced by the new files are literally the same values regardless of `difficulty_level` --
// not that a rendered screen was measured and found unchanged.
//
// This archetype's specific motor question (10b work order): none of the eight templates' answer
// magnitudes were checked against keypad tap-count the way 10a's stepper-vs-keypad question was.
// The structural proof below confirms growing digit count (e.g. C-EG-03's product) never changes
// which keypad geometry constants the surface imports -- digit count tracking magnitude is expected
// mathematical demand, not a motor-constancy violation, per digit-keypad.tsx's own reasoning.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { KEYPAD_KEY_SIZE, KEYPAD_KEY_SPACING, HIT_SLOP } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'value-report-logic.ts'),
  resolve(featureDir, 'archetypes', 'value-report-surface.tsx'),
  resolve(featureDir, 'archetypes', 'payload-value-labels.ts'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function codeReferencesDifficultyLevel(source: string): boolean {
  return /difficulty_level|difficultyLevel/.test(stripComments(source));
}

// --- structural proof 1: neither new file reads difficulty_level at all -------------------------

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

// --- structural proof 2: the surface imports the SAME keypad geometry ordered-value-sequence uses ---

test('value-report-surface.tsx imports KEYPAD_KEY_SIZE / HIT_SLOP from motor-constants.ts (the same module ordered-value-sequence uses), not a second set', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /HIT_SLOP/);
});

test('KEYPAD_KEY_SIZE, KEYPAD_KEY_SPACING, HIT_SLOP are plain values, not functions', () => {
  assert.equal(typeof KEYPAD_KEY_SIZE, 'number');
  assert.equal(typeof KEYPAD_KEY_SPACING, 'number');
  assert.equal(typeof HIT_SLOP, 'object');
});

test('value-report-surface.tsx derives its payload token size and spacing from TOKEN_TOUCH_TARGET_SIZE / TOKEN_SPACING (the same constants value-token-row.tsx uses for its own tokens), never a bare literal', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /TOKEN_TOUCH_TARGET_SIZE/);
  assert.match(source, /TOKEN_SPACING/);
});

test("value-report-surface.tsx's payload token is 60% larger and its label 50% larger than the shared constants, per the user's own sizing request (2026-08-26) -- still a fixed multiplier of the shared constant, not an independently invented size", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /TOKEN_TOUCH_TARGET_SIZE\s*\*\s*1\.6/);
  assert.match(source, /fontSize\.sm\s*\*\s*1\.5/);
});

test('value-report-surface.tsx colours the payload label with the task\'s own game-family accent (accentForGameFamily), never a fixed or per-template colour', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /accentForGameFamily\(task\.game_family_id\)/);
});

test('value-report-surface.tsx spaces the payload tokens at double TOKEN_SPACING, per the user\'s own gap request (2026-08-26) -- still derived from the shared constant, not a bare literal', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /gap:\s*TOKEN_SPACING\s*\*\s*2/);
});

test("value-report-surface.tsx renders the answer as its own labelled column in the SAME row as the given payload values, sharing payloadColumn's flex:1 (per the user's own request that the answer sit at the same row level, divided evenly)", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /ANSWER_LABEL/);
  // exactly one payloadRow View, containing both the payloadValues.map(...) and the answer column --
  // proven structurally by there being only one `styles.payloadRow` reference in the whole file.
  const payloadRowUsages = (source.match(/styles\.payloadRow/g) ?? []).length;
  assert.equal(payloadRowUsages, 1);
});

test("value-report-surface.tsx shows a '?' placeholder in the answer token before the child types a digit", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /ANSWER_PLACEHOLDER\s*=\s*'\?'/);
  assert.match(source, /buffer\.length === 0 \? ANSWER_PLACEHOLDER : buffer/);
});

test("value-report-surface.tsx reserves a fixed two-line height for every label (payloadLabelBlock), so a label that wraps to two lines (e.g. \"Taken away\") does not push its token lower than a one-line label's token (2026-08-26 finding: boxes were not level)", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  assert.match(source, /payloadLabelBlock/);
  assert.match(source, /height:\s*PAYLOAD_LABEL_BLOCK_HEIGHT/);
  assert.match(source, /justifyContent:\s*'flex-end'/);
  // every payloadLabel (given values AND the answer) is wrapped in the same fixed-height block --
  // three usages: two-value templates' two payload labels + the answer, or one-value templates'
  // one payload label + the answer -- checked structurally as "at least the answer's own usage
  // exists alongside the mapped one", not by an exact count that would vary by template.
  const wrapperUsages = (source.match(/styles\.payloadLabelBlock/g) ?? []).length;
  assert.equal(wrapperUsages, 2);
});

// --- structural proof 3: growing answer-digit count across difficulty never changes which keypad --

test("C-EG-03's product grows from a 1-2 digit answer at low difficulty to a larger one at high difficulty, yet the surface's keypad import is a single fixed component regardless (digit count is mathematical demand, not motor demand)", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-03');
  assert.equal(entries.length, 5);
  const products = entries.map((entry) => {
    const payload = entry.prompt_payload as { multiplicand: number; multiplier: number };
    return payload.multiplicand * payload.multiplier;
  });
  // Sanity: digit-count does vary across the real data (proves this isn't a vacuous check of a flat
  // sequence) -- at least one product is single-digit and at least one is double-digit.
  assert.ok(products.some((value) => value < 10));
  assert.ok(products.some((value) => value >= 10));

  const source = readFileSync(resolve(featureDir, 'archetypes', 'value-report-surface.tsx'), 'utf-8');
  const digitKeypadImportCount = (source.match(/import\s*\{\s*DigitKeypad\s*\}/g) ?? []).length;
  assert.equal(digitKeypadImportCount, 1);
});
