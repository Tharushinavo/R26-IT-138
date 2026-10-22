// Motor constancy for `object-set-action` (10e), mirroring c-line-traversal-motor-constancy.test.ts's
// own method and its stated limitation: nothing in this repository can mount a React Native tree and
// measure it, so "identical at difficulty 1-5" below means the geometry CONSTANTS referenced by the
// new files are literally the same values regardless of `difficulty_level` -- not that a rendered
// screen was measured and found unchanged.
//
// This archetype's specific motor question: pool size grows across difficulty (C-CC-01: 3 -> 18
// valid ids across L1-L5, before distractors; C-CC-02: ~7 -> ~20 available ids). Sequence doc §5.1
// rules this acceptable -- selecting from a larger pool is mathematical/perceptual demand, not motor
// demand -- PROVIDED each object's own touch target never changes size or cost per tap. The
// structural proof below confirms pool size varies across the five real exemplars of each template
// while the per-object geometry constants referenced by the new files never change.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { HIT_SLOP, TOKEN_SPACING, TOKEN_TOUCH_TARGET_SIZE } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'object-set-action-logic.ts'),
  resolve(featureDir, 'archetypes', 'object-set-action-surface.tsx'),
  resolve(featureDir, 'primitives', 'object-pool.tsx'),
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

test('object-pool.tsx imports TOKEN_TOUCH_TARGET_SIZE / TOKEN_SPACING / HIT_SLOP from motor-constants.ts, not a second set', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'object-pool.tsx'), 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /TOKEN_TOUCH_TARGET_SIZE/);
  assert.match(source, /TOKEN_SPACING/);
});

test('TOKEN_TOUCH_TARGET_SIZE, TOKEN_SPACING, HIT_SLOP are plain values, not functions', () => {
  assert.equal(typeof TOKEN_TOUCH_TARGET_SIZE, 'number');
  assert.equal(typeof TOKEN_SPACING, 'number');
  assert.equal(typeof HIT_SLOP, 'object');
});

test("object-set-action-logic.ts's max-pool-objects bound is a plain literal constant, not a function of any payload value", () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'object-set-action-logic.ts'), 'utf-8');
  assert.match(source, /MAX_POOL_OBJECTS\s*=\s*\d+/);
});

test("C-CC-01's pool size grows across difficulty 1-5, yet the surface's ObjectPool import is a single fixed component regardless (pool size is perceptual/mathematical demand, not motor demand, per §5.1)", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-01');
  assert.equal(entries.length, 5);
  const poolSizes = entries.map((entry) => {
    const payload = entry.prompt_payload as { valid_object_ids: string[]; distractor_object_ids: string[] };
    return payload.valid_object_ids.length + payload.distractor_object_ids.length;
  });
  assert.notEqual(Math.min(...poolSizes), Math.max(...poolSizes), 'pool size should vary across levels in the real data');

  const source = readFileSync(resolve(featureDir, 'archetypes', 'object-set-action-surface.tsx'), 'utf-8');
  const poolImportCount = (source.match(/import\s*\{\s*ObjectPool\s*\}/g) ?? []).length;
  assert.equal(poolImportCount, 1);
});

test("C-CC-02's pool size grows across difficulty 1-5 the same way", () => {
  const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-02');
  assert.equal(entries.length, 5);
  const poolSizes = entries.map((entry) => {
    const payload = entry.prompt_payload as { available_object_ids: string[] };
    return payload.available_object_ids.length;
  });
  assert.notEqual(Math.min(...poolSizes), Math.max(...poolSizes), 'pool size should vary across levels in the real data');
});

test('object-set-action-logic.ts MAX_POOL_OBJECTS comfortably exceeds the real maximum pool size observed in either template', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'object-set-action-logic.ts'), 'utf-8');
  const match = source.match(/MAX_POOL_OBJECTS\s*=\s*(\d+)/);
  assert.notEqual(match, null);
  const bound = Number.parseInt(match![1]!, 10);

  const cc01Entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-01');
  const cc02Entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-CC-02');
  const maxCc01 = Math.max(
    ...cc01Entries.map((entry) => {
      const payload = entry.prompt_payload as { valid_object_ids: string[]; distractor_object_ids: string[] };
      return payload.valid_object_ids.length + payload.distractor_object_ids.length;
    }),
  );
  const maxCc02 = Math.max(
    ...cc02Entries.map((entry) => (entry.prompt_payload as { available_object_ids: string[] }).available_object_ids.length),
  );
  assert.ok(bound > Math.max(maxCc01, maxCc02), `expected MAX_POOL_OBJECTS > ${Math.max(maxCc01, maxCc02)}, got ${bound}`);
});
