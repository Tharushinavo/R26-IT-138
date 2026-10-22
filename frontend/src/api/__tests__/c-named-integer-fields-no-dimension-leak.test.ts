// Leak guard specific to C-EG-02 (10g): `spec.grid.rows`/`.cols` are simultaneously GIVEN and part
// of the answer (`valid_action_space` declares `rows: int`/`cols: int` alongside
// `submitted_product`), so printing either as a standalone numeral would hand the child 2 of the 3
// answers outright -- see named-integer-fields-logic.ts's own header. This proves the surface only
// ever hands `spec.grid` to `ArrayGrid`'s own `rows`/`cols` props, and never renders either value
// inside an `<AppText>` node the way `payloadValues` (real, ordinary numeral tokens) are rendered.
// Also proves `spec.direction` is carried but never rendered or branched on anywhere in the surface
// or the grid primitive -- 10a's own standing ruling for `C-NP-04.direction`, applied unchanged.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const surfacePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'named-integer-fields-surface.tsx');
const gridPath = resolve(here, '..', '..', 'features', 'c-session', 'primitives', 'array-grid.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// Matches spec.grid.rows/.cols being interpolated directly into JSX text content -- the direct
// textual shape a leak would take in this codebase's own style (see
// c-line-position-no-target-leak.test.ts's identical pattern for target_position).
function codeRendersGridDimensionAsText(source: string): boolean {
  const stripped = stripComments(source);
  return /<AppText[^>]*>\s*\{[^}]*spec\.grid\.(rows|cols)[^}]*\}\s*<\/AppText>/.test(stripped);
}

test('named-integer-fields-surface.tsx never renders spec.grid.rows or spec.grid.cols inside an AppText node', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  assert.equal(codeRendersGridDimensionAsText(source), false);
});

test('named-integer-fields-surface.tsx passes spec.grid.rows/.cols only to ArrayGrid\'s rows/cols props, one occurrence each', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /rows=\{spec\.grid\.rows\}/);
  assert.match(stripped, /cols=\{spec\.grid\.cols\}/);
  assert.equal((stripped.match(/spec\.grid\.rows/g) ?? []).length, 1);
  assert.equal((stripped.match(/spec\.grid\.cols/g) ?? []).length, 1);
});

test('the leak checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = '<AppText>{spec.grid.rows}</AppText>';
  assert.equal(codeRendersGridDimensionAsText(fabricated), true);
});

test('the leak checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never render <AppText>{spec.grid.rows}</AppText>\nconst x = 1;';
  assert.equal(codeRendersGridDimensionAsText(commentOnly), false);
});

test('named-integer-fields-surface.tsx never reads spec.direction (relayed by resolution, never rendered or branched on)', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  assert.equal(/spec\.direction/.test(stripComments(source)), false);
});

test('array-grid.tsx accepts no direction prop and never renders rows/cols as text -- it only draws cells', () => {
  const source = readFileSync(gridPath, 'utf-8');
  const stripped = stripComments(source);
  assert.equal(/direction/.test(stripped), false);
  assert.equal(/\{rows\}|\{cols\}/.test(stripped), false);
});

test("array-grid.tsx's accessibilityLabel is dimension-blind (never interpolates rows or cols into the announced label)", () => {
  const source = readFileSync(gridPath, 'utf-8');
  const stripped = stripComments(source);
  const match = stripped.match(/accessibilityLabel="([^"]*)"/);
  assert.notEqual(match, null);
  assert.equal(/\{/.test(match![1]!), false, 'accessibilityLabel should be a static string, never interpolated with rows/cols');
});
