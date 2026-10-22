// Structural layout proof for `named-field-row.tsx` (10f): no hardcoded field count, boxes sized
// from the interactive TOKEN_TOUCH_TARGET_SIZE floor (never the passive, below-floor
// OBJECT_TOKEN_SIZE), matching `value-report-surface.tsx`'s own payload-token size exactly (2026-08-26
// correction: fields render in the SAME row as payload tokens, so the two must be the same size --
// see named-field-row.tsx's own header). The row/wrap behaviour itself lives in the SURFACE
// (valuesRow, `flexWrap: 'wrap'`), not in this primitive, since this file now exports state +
// single-box rendering rather than owning a row.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const namedFieldRowPath = resolve(here, '..', '..', 'features', 'c-session', 'primitives', 'named-field-row.tsx');
const surfacePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'named-integer-fields-surface.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

test('named-field-row.tsx does not import OBJECT_TOKEN_SIZE or OBJECT_TOKEN_SPACING (the passive-display, below-floor constants)', () => {
  const source = readFileSync(namedFieldRowPath, 'utf-8');
  const stripped = stripComments(source);
  assert.equal(/OBJECT_TOKEN_SIZE/.test(stripped), false);
  assert.equal(/OBJECT_TOKEN_SPACING/.test(stripped), false);
});

test('named-field-row.tsx sizes its box from TOKEN_TOUCH_TARGET_SIZE (the 48px-floor-respecting geometry), never a bare literal', () => {
  const source = readFileSync(namedFieldRowPath, 'utf-8');
  assert.match(source, /FIELD_BOX_SIZE\s*=\s*TOKEN_TOUCH_TARGET_SIZE\s*;/);
});

test('named-field-row.tsx has no hardcoded field count anywhere (state is derived from the fields array passed in)', () => {
  const source = readFileSync(namedFieldRowPath, 'utf-8');
  const stripped = stripComments(source);
  assert.equal(/numColumns\s*[:=]\s*\d+\b/.test(stripped), false);
  assert.match(stripped, /fields\.map\(/);
});

test('the fixed-row-count checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const numColumns = 3;';
  assert.equal(/numColumns\s*[:=]\s*\d+\b/.test(stripComments(fabricated)), true);
});

test('the fixed-row-count checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never hardcode numColumns={3}\nconst x = 1;';
  assert.equal(/numColumns\s*[:=]\s*\d+\b/.test(stripComments(commentOnly)), false);
});

test('named-integer-fields-surface.tsx wraps its combined payload+field row (flexWrap), never a fixed grid', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  // `valuesRow` since 2026-10-10, when the given-value row and the entry row were merged into one
  // line (the test's own name already described the combined row). The ASSERTION is unchanged:
  // whatever holds that row must wrap rather than be a fixed grid, so a task with more quantities
  // than fit reflows instead of overflowing the card.
  assert.match(source, /valuesRow:\s*\{[^}]*flexWrap:\s*'wrap'/s);
});

test("named-field-row.tsx's field box size matches named-integer-fields-surface.tsx's payload token size exactly (same row, same size -- both TOKEN_TOUCH_TARGET_SIZE, no multiplier, so a 4-column row fits on one line)", () => {
  const rowSource = readFileSync(namedFieldRowPath, 'utf-8');
  const surfaceSource = readFileSync(surfacePath, 'utf-8');
  assert.match(rowSource, /FIELD_BOX_SIZE\s*=\s*TOKEN_TOUCH_TARGET_SIZE\s*;/);
  assert.match(surfaceSource, /PAYLOAD_TOKEN_SIZE\s*=\s*TOKEN_TOUCH_TARGET_SIZE\s*;/);
});
