// 10c-specific leak guard, not present in any prior sub-phase because no earlier archetype has an
// answer that is a SUM of two payload values it also renders. C-JB-02's answer is
// `addend_a + addend_b` (the server's `correct_answer_payload.sum`); the line's own extent, if ever
// derived from that sum, would show the answer to the child before they had done anything. This
// file proves, structurally, that no new file computes it.
//
// WHAT THIS CANNOT DO, STATED PLAINLY: a source scan cannot catch every conceivable way to smuggle
// `addend_a + addend_b` into a rendered value (e.g. reading both keys under renamed local variables
// and adding them many lines apart from any recognisable pattern). It catches the direct, textual
// forms an addition would actually take in this codebase's own style, and is a structural guard,
// not a proof of absence for arbitrarily obfuscated code.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'line-traversal-logic.ts'),
  resolve(featureDir, 'archetypes', 'line-traversal-surface.tsx'),
  resolve(featureDir, 'primitives', 'unit-stepper.tsx'),
  resolve(featureDir, 'primitives', 'jump-accumulator.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// Matches the direct textual shapes an addend sum would take: `addend_a + addend_b` (either
// order), or a `.value` access on two payloadValues entries added together. Deliberately narrow --
// see the file header's stated limitation.
function codeSumsTheAddends(source: string): boolean {
  const stripped = stripComments(source);
  return (
    /addend_a\s*\+\s*addend_b/.test(stripped) ||
    /addend_b\s*\+\s*addend_a/.test(stripped) ||
    /payloadValues\[0\]!?\.value\s*\+\s*payloadValues\[1\]!?\.value/.test(stripped)
  );
}

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never sums the two addends together`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeSumsTheAddends(source), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const lineEnd = addend_a + addend_b;';
  assert.equal(codeSumsTheAddends(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never compute addend_a + addend_b\nconst x = 1;';
  assert.equal(codeSumsTheAddends(commentOnly), false);
});

test("unit-stepper.tsx's line-length bound is a literal, not computed from any payload-derived variable (no arithmetic expression assigned to MAX_LINE_FORWARD_STEPS)", () => {
  const source = readFileSync(resolve(featureDir, 'primitives', 'unit-stepper.tsx'), 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /const MAX_LINE_FORWARD_STEPS = \d+;/);
});

// `line-traversal-surface.tsx` DOES compute `spec.startValue + jumps.length` (2026-08-26 correction
// -- no separate typed "where you landed" field; the marker's own visible position is submitted
// directly). This is deliberately NOT what the guard above catches, and the distinction matters:
// `startValue` and `jumps.length` are never the forbidden `addend_a + addend_b` sum -- they read
// off what the child's own jumps already produced and made visible on screen (the identical
// arithmetic `UnitStepper` already uses for its own marker), not the task's unseen answer. This
// test pins that the surface's own derivation is exactly this shape and nothing closer to the
// forbidden one.
test('line-traversal-surface.tsx derives the submitted position as spec.startValue + jumps.length -- never as a sum of the two addends', () => {
  const source = readFileSync(resolve(featureDir, 'archetypes', 'line-traversal-surface.tsx'), 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /spec\.startValue\s*\+\s*jumps\.length/);
  assert.equal(codeSumsTheAddends(stripped), false);
});
