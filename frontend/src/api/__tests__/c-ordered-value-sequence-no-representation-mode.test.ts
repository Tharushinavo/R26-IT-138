// AC 8: no client code reads or branches on representation_mode -- asserted, not asserted-in-a-
// comment. Comment-stripped source scan of the four files 10a introduces, mirroring
// c-motor-constants.test.ts's method, with a negative control proving the scan is not vacuous.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'ordered-value-sequence-logic.ts'),
  resolve(featureDir, 'archetypes', 'ordered-value-sequence-surface.tsx'),
  resolve(featureDir, 'primitives', 'value-token-row.tsx'),
  resolve(featureDir, 'primitives', 'digit-keypad.tsx'),
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
