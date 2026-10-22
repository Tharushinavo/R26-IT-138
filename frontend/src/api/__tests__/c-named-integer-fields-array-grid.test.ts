// Structural proof for the C-EG-02 grid extension (10g): `MAX_GRID_DIMENSION` is a plain literal
// constant, comfortably exceeds the real observed maximum (5x5), and `array-grid.tsx` is imported
// exactly once, from `named-integer-fields-surface.tsx`, mirroring
// c-partition-allocation-motor-constancy.test.ts's own MAX_BINS proof.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

test("named-integer-fields-logic.ts's max-grid-dimension bound is a plain literal constant, not a function of any payload value", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'), 'utf-8');
  assert.match(source, /MAX_GRID_DIMENSION\s*=\s*\d+/);
});

test('MAX_GRID_DIMENSION comfortably exceeds the real maximum rows/cols observed in C-EG-02', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'), 'utf-8');
  const match = source.match(/MAX_GRID_DIMENSION\s*=\s*(\d+)/);
  assert.notEqual(match, null);
  const bound = Number.parseInt(match![1]!, 10);

  const eg02Entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-02');
  const maxDimension = Math.max(
    ...eg02Entries.map((entry) => {
      const payload = entry.prompt_payload as { rows: number; cols: number };
      return Math.max(payload.rows, payload.cols);
    }),
  );
  assert.ok(bound > maxDimension, `expected MAX_GRID_DIMENSION > ${maxDimension}, got ${bound}`);
});

test('named-integer-fields-surface.tsx imports ArrayGrid exactly once', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/primitives\/array-grid'/);
  const gridJsxCount = (source.match(/<ArrayGrid\b/g) ?? []).length;
  assert.equal(gridJsxCount, 1);
});

test('array-grid.tsx does not import TOKEN_TOUCH_TARGET_SIZE or OBJECT_TOKEN_SIZE (its own passive-cell constants govern it, not another primitive\'s)', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'array-grid.tsx'), 'utf-8');
  assert.equal(/TOKEN_TOUCH_TARGET_SIZE/.test(source), false);
  assert.equal(/OBJECT_TOKEN_SIZE/.test(source), false);
  assert.match(source, /GRID_CELL_SIZE/);
});

test('array-grid.tsx renders exactly rows * cols cells, one row per rendered View, never a hardcoded count', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'array-grid.tsx'), 'utf-8');
  assert.match(source, /Array\.from\(\{\s*length:\s*rows\s*\}/);
  assert.match(source, /Array\.from\(\{\s*length:\s*cols\s*\}/);
});

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

test('array-grid.tsx source, with comments stripped, never references difficulty_level', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'array-grid.tsx'), 'utf-8');
  assert.equal(/difficulty_level|difficultyLevel/.test(stripComments(source)), false);
});
