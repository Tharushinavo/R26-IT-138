// AC 7: no client code reads or branches on representation_mode. Comment-stripped source scan of
// the three files 10e introduces, mirroring c-line-traversal-no-representation-mode.test.ts's own
// method, with a negative control proving the scan is not vacuous.

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

function codeReferencesRepresentationMode(source: string): boolean {
  return /representation_mode/.test(stripComments(source));
}

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references representation_mode`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeReferencesRepresentationMode(source), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'if (task.representation_mode === "x") { /* ... */ }';
  assert.equal(codeReferencesRepresentationMode(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never branch on representation_mode\nconst x = 1;';
  assert.equal(codeReferencesRepresentationMode(commentOnly), false);
});
