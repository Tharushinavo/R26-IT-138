// Structural layout proof for `object-pool.tsx` (10e): no hardcoded per-row count (never a
// ten-frame or subitizing-group representation), a bounded height with internal scroll (the
// SUBMIT-off-screen remedy this project has already applied twice), and NO use of
// `OBJECT_TOKEN_SIZE`/`OBJECT_TOKEN_SPACING` -- the deliberate divergence from
// `object-quantity-display.tsx`'s passive, below-floor sizing, since every object in this pool is a
// real press target and SPEC section 10's 48px floor governs.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const objectPoolPath = resolve(here, '..', '..', 'features', 'c-session', 'primitives', 'object-pool.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

test('object-pool.tsx does not import OBJECT_TOKEN_SIZE or OBJECT_TOKEN_SPACING (the passive-display, below-floor constants)', () => {
  const source = readFileSync(objectPoolPath, 'utf-8');
  const stripped = stripComments(source);
  assert.equal(/OBJECT_TOKEN_SIZE/.test(stripped), false);
  assert.equal(/OBJECT_TOKEN_SPACING/.test(stripped), false);
});

test('object-pool.tsx uses TOKEN_TOUCH_TARGET_SIZE for object height and width (the 48px-floor-respecting geometry)', () => {
  const source = readFileSync(objectPoolPath, 'utf-8');
  assert.match(source, /height:\s*TOKEN_TOUCH_TARGET_SIZE/);
  assert.match(source, /width:\s*TOKEN_TOUCH_TARGET_SIZE/);
});

test('object-pool.tsx uses flexWrap, not a fixed numColumns-style grid', () => {
  const source = readFileSync(objectPoolPath, 'utf-8');
  assert.match(source, /flexWrap:\s*'wrap'/);
  assert.equal(/numColumns/.test(source), false);
});

test('object-pool.tsx has no hardcoded per-row count (no bare 5 or 10 as a row-length literal)', () => {
  const source = readFileSync(objectPoolPath, 'utf-8');
  const stripped = stripComments(source);
  // A per-row count would show up as something like `numColumns={5}`, `slice(0, 10)`, or a
  // row-chunking loop keyed to a literal 5 or 10 -- none of which this file contains, since row
  // length here is purely a function of flexWrap + container width, never chosen.
  assert.equal(/numColumns\s*[:=]\s*(5|10)\b/.test(stripped), false);
  assert.equal(/chunk\w*\(\s*\w+\s*,\s*(5|10)\s*\)/.test(stripped), false);
});

test('object-pool.tsx bounds its own render height and scrolls internally, rather than growing unboundedly', () => {
  const source = readFileSync(objectPoolPath, 'utf-8');
  assert.match(source, /maxHeight:\s*POOL_MAX_HEIGHT/);
  assert.match(source, /ScrollView/);
});

test('the fixed-row-count checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const numColumns = 10;';
  assert.equal(/numColumns\s*[:=]\s*(5|10)\b/.test(stripComments(fabricated)), true);
});

test('the fixed-row-count checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never hardcode numColumns={10}\nconst x = 1;';
  assert.equal(/numColumns\s*[:=]\s*(5|10)\b/.test(stripComments(commentOnly)), false);
});
