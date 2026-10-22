// "Does NOT deliver" proof (master work order §3/§10e sequence doc): no client-side distinction
// between valid and distractor ids beyond rendering them (no styling/filtering on
// distractor_object_ids -- already covered structurally by the no-template-branch test's literal
// ban, since the key name itself never appears); no comparison of a selection or box size against
// target_n; no de-duplication or repair of a selection. Comment-stripped source scan, two
// meta-tests, mirroring every other archetype's own convention.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

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

// A selection/box length ever compared against .value or .length of the target -- e.g.
// `placed.length === spec.targetValue.value` or `selectedIds.size === target_n`.
function codeComparesLengthToTarget(source: string): boolean {
  const stripped = stripComments(source);
  return (
    /\.length\s*===?\s*spec\.targetValue/.test(stripped) ||
    /\.size\s*===?\s*spec\.targetValue/.test(stripped) ||
    /spec\.targetValue[^;]*===?\s*\w+\.length/.test(stripped) ||
    /spec\.targetValue[^;]*===?\s*\w+\.size/.test(stripped)
  );
}

// De-duplication of a selection -- a Set constructed FROM the id list to strip duplicates before
// submission (as opposed to the resolver's own duplicate-id GUARD, which rejects rather than
// repairs -- see object-set-action-logic.ts's own duplicate-id fail-closed control). Narrow:
// specifically catches `[...new Set(` used as a repair step, which none of the new files do (the
// surface submits `Array.from(selectedIds)`/`placed` directly, and ObjectPool's own Set is a
// selection-membership index, not a de-duplication of the submitted array).
function codeDeduplicatesSelection(source: string): boolean {
  const stripped = stripComments(source);
  return /\[\.\.\.new Set\(\s*(selectedIds|placed|objectIds)\s*\)\]/.test(stripped);
}

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: never compares a selection/box length against the target value`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeComparesLengthToTarget(source), false);
  });

  test(`${filePath.split(/[\\/]/).pop()}: never de-duplicates a selection before submission`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeDeduplicatesSelection(source), false);
  });
}

test('the length/target checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const ok = placed.length === spec.targetValue.value;';
  assert.equal(codeComparesLengthToTarget(fabricated), true);
});

test('the length/target checker does NOT fire on the same fabricated string kept only in a comment', () => {
  const commentOnly = '// must never check placed.length === spec.targetValue.value\nconst x = 1;';
  assert.equal(codeComparesLengthToTarget(commentOnly), false);
});

test('the de-duplication checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const cleaned = [...new Set(selectedIds)];';
  assert.equal(codeDeduplicatesSelection(fabricated), true);
});

test('the de-duplication checker does NOT fire on the same fabricated string kept only in a comment', () => {
  const commentOnly = '// must never do [...new Set(selectedIds)]\nconst x = 1;';
  assert.equal(codeDeduplicatesSelection(commentOnly), false);
});
