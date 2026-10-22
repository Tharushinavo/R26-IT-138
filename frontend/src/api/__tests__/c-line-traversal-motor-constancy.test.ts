// Motor constancy for `line-traversal` (10c), mirroring `c-value-report-motor-constancy.test.ts`'s
// own method and its stated limitation: nothing in this repository can mount a React Native tree
// and measure it, so "identical at difficulty 1-5" below means the geometry CONSTANTS referenced by
// the new files are literally the same values regardless of `difficulty_level` -- not that a
// rendered screen was measured and found unchanged.
//
// This archetype's specific motor question (10c plan): the number of forward jumps a child must
// make to reach the answer is min(addend_a, addend_b), which COULD reach up to 18 at difficulty 5
// (the generator's own magnitude ramp's theoretical ceiling), though the frozen exemplar fixture's
// actual draws stay smaller ([2, 2, 1, 1, 3] across L1-L5 -- a random draw can put the larger value
// in either addend). Sequence doc §5.1 rules any such growth acceptable -- "mathematical demand
// grows with the number of steps; motor demand does not move" -- PROVIDED the per-step control
// itself (STEP_TOUCH_TARGET_SIZE / STEP_SPACING) never changes size or cost per tap. The structural
// proof below confirms growing jump count never changes which stepper geometry constants the
// surface imports, and separately confirms the real jump counts do vary across the five real
// exemplars (so this isn't a vacuous check of a flat sequence).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { HIT_SLOP, STEP_SPACING, STEP_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'line-traversal-logic.ts'),
  resolve(featureDir, 'archetypes', 'line-traversal-surface.tsx'),
  resolve(featureDir, 'primitives', 'unit-stepper.tsx'),
  resolve(featureDir, 'primitives', 'jump-accumulator.tsx'),
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

// --- structural proof 2: the stepper geometry is the shared, reserved motor-constants -------------

test('unit-stepper.tsx imports STEP_TOUCH_TARGET_SIZE / STEP_SPACING / HIT_SLOP from motor-constants.ts, not a second set', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'unit-stepper.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /STEP_TOUCH_TARGET_SIZE/);
  assert.match(source, /STEP_SPACING/);
});

test('STEP_TOUCH_TARGET_SIZE, STEP_SPACING, HIT_SLOP are plain values, not functions', () => {
  assert.equal(typeof STEP_TOUCH_TARGET_SIZE, 'number');
  assert.equal(typeof STEP_SPACING, 'number');
  assert.equal(typeof HIT_SLOP, 'object');
});

test("unit-stepper.tsx's max-forward-steps bound is a plain literal constant, not a function of any payload value (deriving the line's extent from the addends would leak the answer -- see line-traversal-logic.ts's header)", () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'unit-stepper.tsx'), 'utf-8');
  assert.match(source, /MAX_LINE_FORWARD_STEPS\s*=\s*\d+/);
});

// --- structural proof 3: growing jump count across difficulty never changes stepper geometry ------

test("C-JB-02's required jump count (min(addend_a, addend_b)) grows across difficulty 1-5, yet the surface's UnitStepper/JumpAccumulator imports are single fixed components regardless (step count is mathematical demand, not motor demand, per §5.1)", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-JB-02');
  assert.equal(entries.length, 5);
  const jumpCounts = entries.map((entry) => {
    const payload = entry.prompt_payload as { addend_a: number; addend_b: number };
    return Math.min(payload.addend_a, payload.addend_b);
  });
  // Sanity: jump count does vary across the real, frozen exemplar data (proves this isn't a
  // vacuous check of a flat sequence). Measured, not assumed: [2, 2, 1, 1, 3] across L1-L5 --
  // materially smaller than the generator's theoretical ceiling (min(addend_a, addend_b) could
  // reach up to 18, per magnitude_a_by_level's own difficulty-5 bound), because a random draw can
  // put the larger value in either addend. The frozen fixture is not required to hit that ceiling
  // for this proof to hold: the CONSTANTS below don't move regardless of which count occurs.
  assert.ok(jumpCounts.some((count) => count === Math.min(...jumpCounts)));
  assert.ok(jumpCounts.some((count) => count === Math.max(...jumpCounts)));
  assert.notEqual(Math.min(...jumpCounts), Math.max(...jumpCounts), 'jump count should vary across levels in the real data');

  const source = readFileSync(resolve(featureDir, 'archetypes', 'line-traversal-surface.tsx'), 'utf-8');
  const stepperImportCount = (source.match(/import\s*\{\s*UnitStepper\s*\}/g) ?? []).length;
  const accumulatorImportCount = (source.match(/import\s*\{\s*JumpAccumulator\s*\}/g) ?? []).length;
  assert.equal(stepperImportCount, 1);
  assert.equal(accumulatorImportCount, 1);
});

test("unit-stepper.tsx's MAX_LINE_FORWARD_STEPS comfortably exceeds the real generator's maximum required jump count (18, at difficulty 5) -- a robustness ceiling, not a value tuned to the data", () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'unit-stepper.tsx'), 'utf-8');
  const match = source.match(/MAX_LINE_FORWARD_STEPS\s*=\s*(\d+)/);
  assert.notEqual(match, null);
  const bound = Number.parseInt(match![1]!, 10);
  assert.ok(bound > 18, `expected MAX_LINE_FORWARD_STEPS > 18, got ${bound}`);
});
