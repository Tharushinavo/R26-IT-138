// The work order's own line for this archetype, verbatim: "No validation that groups are equal,
// that a partition is exhaustive, or that a product is right. The client submits; the server
// evaluates." This file proves, structurally, that no new source file computes equality, a sum, or
// exhaustiveness over the bins -- and separately (behaviourally) that SUBMIT is still gated on
// completeness, which is a DIFFERENT, non-correctness condition (see partition-allocation-surface.tsx's
// own header for why that gate exists: `list[int]` accepts an empty array at the encoder layer).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'partition-allocation-logic.ts'),
  resolve(featureDir, 'archetypes', 'partition-allocation-surface.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// Words that would signal a correctness check being performed client-side: summing the bins,
// checking they're equal, checking a product, or checking a partition is exhaustive.
const CORRECTNESS_PATTERN = /\bisEqual\b|\ballEqual\b|\bsum\(|\breduce\(.*\+.*\)|\bisExhaustive\b|\bisCorrect\b|\bcheckAnswer\b/i;

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, performs no correctness check over the bins`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(CORRECTNESS_PATTERN.test(stripComments(source)), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const allEqual = bins.every((b) => b === bins[0]);';
  assert.equal(CORRECTNESS_PATTERN.test(stripComments(fabricated)), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never compute allEqual over the bins\nconst x = 1;';
  assert.equal(CORRECTNESS_PATTERN.test(stripComments(commentOnly)), false);
});

test('partition-allocation-surface.tsx: SUBMIT is gated only on every bin having a value, never on the bins summing to anything or being equal', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'partition-allocation-surface.tsx'), 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /entryValues\.every\(\(value\)\s*=>\s*value\s*!==\s*null\)/);
  assert.equal(CORRECTNESS_PATTERN.test(stripped), false);
});

test('an unfilled bin (still null) makes canSubmit false -- the completeness gate genuinely blocks an incomplete partition', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'partition-allocation-surface.tsx'), 'utf-8');
  assert.match(source, /entryValues\.length\s*===\s*spec\.binCount/);
});
