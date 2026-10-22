// C-EG-02's own field layout (10g, 2026-08-26 correction): "Cols x Rows = Product", one row, never
// wrapping -- found by the owner testing C-EG-02 in the browser, where the generic wrapped
// `fieldsRow` every other named-integer-fields template uses put "Submitted Product" on its own
// line (that label's own width, unabbreviated, was wider than the remaining row space). This file
// proves the equation row exists, is cosmetic-only (the resolver's own field label is untouched),
// and covers exactly the three real C-EG-02 keys.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const surfacePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'named-integer-fields-surface.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

test('named-integer-fields-surface.tsx renders EquationFieldsRow when spec.grid is not null, the generic fieldsRow otherwise', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /spec\.grid !== null \? \(\s*<EquationFieldsRow/);
});

test('equationRow style has no flexWrap: wrap (deliberately, unlike fieldsRow)', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  const equationRowBlock = stripped.match(/equationRow:\s*\{[^}]*\}/);
  assert.notEqual(equationRowBlock, null);
  assert.equal(/flexWrap/.test(equationRowBlock![0]), false);
});

test("EQUATION_FIELD_LABEL_OVERRIDE only renames the display label -- spec.fields' own label ('Submitted Product', from humanizeActionKey) is never mutated", () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /EQUATION_FIELD_LABEL_OVERRIDE\s*:\s*Record<string,\s*string>\s*=\s*\{\s*submitted_product:\s*'Product',?\s*\}/);
  // The override object is a local const, never assigned back onto a `field.label`.
  assert.equal(/field\.label\s*=/.test(stripped), false);
});

test('EquationFieldsRow fails closed to null (not a partial equation) when any of cols/rows/submitted_product is missing from spec.fields', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /colsField === undefined \|\| rowsField === undefined \|\| productField === undefined/);
  assert.match(stripped, /return null;/);
});

test('the three equation boxes are rendered through one shared renderBox helper, not three separately hand-written boxes', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  const renderBoxCallCount = (stripped.match(/renderBox\(/g) ?? []).length;
  assert.equal(renderBoxCallCount, 3, 'renderBox(colsField), renderBox(rowsField), renderBox(productField, override)');
});
