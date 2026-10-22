// Motor constancy for `partition-allocation` (10g), mirroring
// c-object-set-action-motor-constancy.test.ts's own method and its stated limitation: nothing in
// this repository can mount a React Native tree and measure it, so "identical at difficulty 1-5"
// below means the geometry CONSTANTS referenced by the new files are literally the same values
// regardless of `difficulty_level` -- not that a rendered screen was measured and found unchanged.
//
// This archetype's specific motor question: bin COUNT grows across difficulty (C-EG-01: 2 -> 5
// across L1-L5), but `ValueTokenRow`'s own per-slot touch target must never change size or cost per
// tap. §5.1 rules this acceptable -- filling a longer row is mathematical/perceptual demand, not
// motor demand -- provided the slot geometry stays constant, which is `value-token-row.tsx`'s own
// pre-existing guarantee (unmodified here, per the header).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'partition-allocation-logic.ts'),
  resolve(featureDir, 'archetypes', 'partition-allocation-surface.tsx'),
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

test('partition-allocation-surface.tsx imports ValueTokenRow rather than a new row primitive', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'partition-allocation-surface.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/primitives\/value-token-row'/);
  const rowJsxCount = (source.match(/<ValueTokenRow\b/g) ?? []).length;
  assert.equal(rowJsxCount, 1);
});

test("partition-allocation-logic.ts's max-bins bound is a plain literal constant, not a function of any payload value", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'partition-allocation-logic.ts'), 'utf-8');
  assert.match(source, /MAX_BINS\s*=\s*\d+/);
});

test("C-EG-01's bin count grows across difficulty 1-5, yet the surface's ValueTokenRow import is a single fixed component regardless (bin count is perceptual/mathematical demand, not motor demand, per §5.1)", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-01');
  assert.equal(entries.length, 5);
  const counts = entries.map((entry) => (entry.prompt_payload as { number_of_groups: number }).number_of_groups);
  assert.notEqual(Math.min(...counts), Math.max(...counts), 'bin count should vary across levels in the real data');
});

test('partition-allocation-logic.ts MAX_BINS comfortably exceeds the real maximum bin count observed across both fixed-count templates', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'partition-allocation-logic.ts'), 'utf-8');
  const match = source.match(/MAX_BINS\s*=\s*(\d+)/);
  assert.notEqual(match, null);
  const bound = Number.parseInt(match![1]!, 10);

  const eg01Entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-01');
  const sf01Entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-SF-01');
  const maxEg01 = Math.max(...eg01Entries.map((entry) => (entry.prompt_payload as { number_of_groups: number }).number_of_groups));
  const maxSf01 = Math.max(...sf01Entries.map((entry) => (entry.prompt_payload as { recipient_count: number }).recipient_count));
  assert.ok(bound > Math.max(maxEg01, maxSf01), `expected MAX_BINS > ${Math.max(maxEg01, maxSf01)}, got ${bound}`);
});
