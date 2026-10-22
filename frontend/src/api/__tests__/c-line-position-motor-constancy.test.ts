// Motor constancy for `line-position` (10d), mirroring c-line-traversal-motor-constancy.test.ts's
// own method and its stated limitation: nothing in this repository can mount a React Native tree and
// measure it, so "identical at difficulty 1-5" below means the geometry CONSTANTS referenced by the
// new files are literally the same values regardless of `difficulty_level` -- not that a rendered
// screen was measured and found unchanged.
//
// This archetype's specific motor question, and the reason it stayed unbuilt through 10d proper: the
// number of unit taps needed to reach `target_position` from 0 ranges from 2 (L1) to 34 (L5) --
// unlike `line-traversal` (where each unit jump IS the counting-on act scored), every one of those
// taps here is pure transit cost after the first, which SPEC section 10 forbids scaling with
// difficulty. `LINE_POSITION_COARSE_STEP` (a fixed 10, unit-stepper.tsx's own `coarseStep` prop) is
// the fix: it collapses that spread by adding a second, constant-size jump control, never derived
// from `interval_max` or `difficulty_level`. The structural proof below confirms both that the raw
// tap-count spread really is that large across the five real exemplars (so this isn't solving a
// vacuous problem) and that the coarse-step constant itself never varies.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { LINE_POSITION_COARSE_STEP } from '@/src/features/c-session/archetypes/line-position-logic';
import { HIT_SLOP, STEP_SPACING, STEP_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'line-position-logic.ts'),
  resolve(featureDir, 'archetypes', 'line-position-surface.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function codeReferencesDifficultyLevel(source: string): boolean {
  return /difficulty_level|difficultyLevel/.test(stripComments(source));
}

// --- structural proof 1: neither new file reads difficulty_level at all ---------------------------

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references difficulty_level`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeReferencesDifficultyLevel(source), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const step = base + task.difficulty_level;';
  assert.equal(codeReferencesDifficultyLevel(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never scale with difficulty_level\nconst step = base;';
  assert.equal(codeReferencesDifficultyLevel(commentOnly), false);
});

// --- structural proof 2: the coarse-step constant is a literal, never derived ----------------------

test('LINE_POSITION_COARSE_STEP is a plain number, not a function', () => {
  assert.equal(typeof LINE_POSITION_COARSE_STEP, 'number');
});

test('line-position-logic.ts declares LINE_POSITION_COARSE_STEP as a literal constant expression, not computed from interval_max or difficulty_level', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'line-position-logic.ts'), 'utf-8');
  assert.match(source, /export const LINE_POSITION_COARSE_STEP\s*=\s*\d+;/);
});

test('line-position-surface.tsx imports STEP_TOUCH_TARGET_SIZE-governed geometry from unit-stepper.tsx, not a second set of constants (no direct STEP_* import of its own)', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'line-position-surface.tsx'), 'utf-8');
  assert.equal(/STEP_TOUCH_TARGET_SIZE|STEP_SPACING/.test(source), false);
  assert.match(source, /from '@\/src\/features\/c-session\/primitives\/unit-stepper'/);
});

test('STEP_TOUCH_TARGET_SIZE, STEP_SPACING, HIT_SLOP (the constants both of unit-stepper.tsx\'s coarse and fine buttons share) are plain values, not functions', () => {
  assert.equal(typeof STEP_TOUCH_TARGET_SIZE, 'number');
  assert.equal(typeof STEP_SPACING, 'number');
  assert.equal(typeof HIT_SLOP, 'object');
});

// --- structural proof 3: the raw tap-count spread this fix addresses is real, measured data --------

test("C-MCL-04's required unit-only tap count (target_position - 0) grows 17x from L1 to L5 in the real, frozen exemplar data -- the confound this batch's coarse-step fix exists to close", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-MCL-04');
  assert.equal(entries.length, 5);
  const tapCounts = entries.map((entry) => (entry.prompt_payload as { target_position: number }).target_position);
  assert.deepEqual(tapCounts, [2, 7, 26, 36, 34]);
  const spread = Math.max(...tapCounts) / Math.min(...tapCounts);
  assert.ok(spread >= 17, `expected a spread of at least 17x, measured ${spread}x`);
});

test('with the coarse+fine fix, the same L5 target (34) reaches in 7 taps (3 coarse-of-10 + 4 fine-of-1), not 34', () => {
  const target = 34;
  const coarseTaps = Math.floor(target / LINE_POSITION_COARSE_STEP);
  const fineTaps = target % LINE_POSITION_COARSE_STEP;
  assert.equal(coarseTaps, 3);
  assert.equal(fineTaps, 4);
  assert.equal(coarseTaps + fineTaps, 7);
});
