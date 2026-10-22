// `object-quantity-display.tsx` (10e-0): the new read-only quantity-as-objects primitive. Nothing
// in this repository can mount a component tree, so these are structural/source-scan proofs, not a
// rendered-and-measured observation -- matching every other primitive's own test method in this
// codebase.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { OBJECT_TOKEN_SIZE, OBJECT_TOKEN_SPACING } from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const filePath = resolve(here, '..', '..', 'features', 'c-session', 'primitives', 'object-quantity-display.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// --- geometry: derived from motor-constants.ts, never a bare literal --------------------------------

test('OBJECT_TOKEN_SIZE and OBJECT_TOKEN_SPACING are plain values, not functions', () => {
  assert.equal(typeof OBJECT_TOKEN_SIZE, 'number');
  assert.equal(typeof OBJECT_TOKEN_SPACING, 'number');
});

test('object-quantity-display.tsx imports its object geometry from motor-constants.ts, never a bare literal', () => {
  const source = readFileSync(filePath, 'utf-8');
  assert.match(source, /from '@\/src\/features\/c-session\/motor-constants'/);
  assert.match(source, /OBJECT_TOKEN_SIZE/);
  assert.match(source, /OBJECT_TOKEN_SPACING/);
});

test('never references difficulty_level (comments stripped) -- geometry cannot vary by difficulty because the concept never enters this file', () => {
  const source = stripComments(readFileSync(filePath, 'utf-8'));
  assert.doesNotMatch(source, /difficulty_level|difficultyLevel/);
});

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const size = base + task.difficulty_level;';
  assert.match(stripComments(fabricated), /difficulty_level/);
});

// --- wrap, never scroll; never a fixed column/row count ----------------------------------------------

test('wraps rather than scrolls: the row style declares flexWrap, never a ScrollView', () => {
  const source = readFileSync(filePath, 'utf-8');
  assert.match(source, /flexWrap:\s*'wrap'/);
  assert.doesNotMatch(source, /ScrollView/);
});

test('never hardcodes a per-row object count (no numColumns, no fixed row-length constant of any kind) -- the row length is left to fall out of flexWrap + fixed object size, never a chosen number that could encode a ten-frame or a subitizing group', () => {
  const source = stripComments(readFileSync(filePath, 'utf-8'));
  assert.doesNotMatch(source, /numColumns/);
  assert.doesNotMatch(source, /PER_ROW/i);
  assert.doesNotMatch(source, /COLUMNS?\s*=/i);
});

test('the checker fires on a fabricated per-row constant (negative control), proving it is not vacuous', () => {
  const fabricated = 'const OBJECTS_PER_ROW = 10;';
  assert.match(fabricated, /PER_ROW/i);
});

// --- renders exactly `count` objects, clamped by RENDER_CAP ------------------------------------------

test('renders exactly `count` object elements for a representative range of quantities (source-level: Array.from({length: renderCount}) with renderCount derived from the count prop, clamped)', () => {
  const source = readFileSync(filePath, 'utf-8');
  assert.match(source, /Array\.from\(\{\s*length:\s*renderCount\s*\}/);
  assert.match(source, /Math\.min\(count,\s*RENDER_CAP\)/);
  assert.match(source, /Math\.max\(0,/);
});

test('RENDER_CAP is 100, numerically matching (but independently defined from) option-select-logic.ts\'s own MAX_QUANTITY -- a defensive rendering ceiling, not the primary guard', () => {
  const source = readFileSync(filePath, 'utf-8');
  assert.match(source, /RENDER_CAP\s*=\s*100/);
});

// --- the accessibility answer-leak guard --------------------------------------------------------------
// The quantity IS the answer on this path (option-select-logic.ts's own header). An accessibility
// label announcing the count, or a screen reader able to count individually-exposed object elements,
// would leak that answer through a channel the numeral-free visual rendering does not use.

test('the accessibility label contains no digit, ever -- a fixed, quantity-blind string', () => {
  const source = readFileSync(filePath, 'utf-8');
  const labelMatch = source.match(/QUANTITY_BLIND_LABEL\s*=\s*'([^']*)'/);
  assert.notEqual(labelMatch, null, 'QUANTITY_BLIND_LABEL constant not found');
  const label = labelMatch![1]!;
  assert.doesNotMatch(label, /[0-9]/);
});

test('individual object elements are hidden from the accessibility tree entirely (accessibilityElementsHidden and importantForAccessibility="no-hide-descendants"), so a screen reader cannot recover the count by counting stops', () => {
  const source = readFileSync(filePath, 'utf-8');
  assert.match(source, /accessibilityElementsHidden/);
  assert.match(source, /importantForAccessibility="no-hide-descendants"/);
});

test('the outer row is exactly one accessible element carrying the fixed label, not one element per object', () => {
  const source = stripComments(readFileSync(filePath, 'utf-8'));
  const accessibleUsages = (source.match(/\baccessible\b(?!Element|Role|Label)/g) ?? []).length;
  assert.equal(accessibleUsages, 1);
});
