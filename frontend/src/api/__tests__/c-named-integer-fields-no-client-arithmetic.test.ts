// The interaction-cost / answer-leak guard this archetype owes (master work order §10f row: "No
// auto-carry, no auto-borrow, no pre-fill"). Decomposing `target_number` (BT-01/02) and performing
// the trade from `pre_tens`/`pre_ones` (BT-03/04) ARE the assessed skills -- a client that computed
// either would be grading the child (a leak: a gated SUBMIT that only enables on a correct answer
// tells the child the answer) or silently doing the child's work (pre-fill). This file proves,
// structurally, that no new source file performs arithmetic between a field value and a payload
// value, and that no field starts pre-filled from the payload.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'),
  resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'),
  resolve(featureDir, 'primitives', 'named-field-row.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// Arithmetic operators applied to a payload-derived identifier -- `target_number`, `pre_tens`,
// `pre_ones`, `payloadValue`, `payloadValues` -- would be the auto-carry/auto-borrow/decomposition
// this archetype must never perform. `+`/`-`/`*` used elsewhere (array index math, string
// concatenation) is untouched; this pattern only flags arithmetic ON a payload-shaped identifier.
const PAYLOAD_ARITHMETIC_PATTERN = /(target_number|pre_tens|pre_ones|payloadValue)\s*[-+*/]|[-+*/]\s*(target_number|pre_tens|pre_ones|payloadValue)/;

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, performs no arithmetic on a payload value`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(PAYLOAD_ARITHMETIC_PATTERN.test(stripComments(source)), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const carried = pre_tens + 1;';
  assert.equal(PAYLOAD_ARITHMETIC_PATTERN.test(stripComments(fabricated)), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never compute pre_tens + 1\nconst x = 1;';
  assert.equal(PAYLOAD_ARITHMETIC_PATTERN.test(stripComments(commentOnly)), false);
});

test('named-integer-fields-logic.ts: NamedIntegerFieldsSpec has no derived/computed field, only raw payload passthrough and mechanical labels', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-logic.ts'), 'utf-8');
  // No comparison of a field key's expected value against target_number/pre_tens/pre_ones sums.
  assert.equal(/correct|isValid\(|checkAnswer|validateSum/i.test(stripComments(source)), false);
});

test('named-field-row.tsx: every field buffer starts as an empty string, never seeded from a payload value', () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'named-field-row.tsx'), 'utf-8');
  assert.match(stripComments(source), /initial\[field\.key\]\s*=\s*'';/);
});

test('named-integer-fields-surface.tsx: SUBMIT is gated only on every field having a value, never on a sum matching target_number', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'named-integer-fields-surface.tsx'), 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /entry\.values\.every\(\(value\)\s*=>\s*value\s*!==\s*null\)/);
  assert.equal(/===\s*spec\.payloadValues/.test(stripped), false);
});
