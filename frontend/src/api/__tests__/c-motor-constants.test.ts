// Motor-constancy is a structural guarantee, not a measured one (10.0b-ii SCOPE section 5; sequence
// doc section 5.1): the mathematical level a task is set at must never be able to reach the module
// that defines touch targets, hit-slop, gesture thresholds and animation durations, because that
// module has no input at all. This project has no component-rendering test capability
// (`npm run test:contract` is `node --import tsx --test` over plain `.ts`, and devDependencies carry
// no rendering library), so the proof here is two structural checks rather than a render: every
// export is a plain value, never a function of anything; and the module's own source, with
// comments stripped, never references the level concept.
//
// The comment-stripping matters and is not incidental. `no-node-builtins-outside-tests-and-
// scripts.test.ts` was first written as a bare substring match and the supervisor's VERIFY run
// found it red on its own two subject files' EXPLANATORY COMMENTS, not on any real import
// (buildLog1.md, "Component C 10.0b-fix", the CORRECTION paragraph). motor-constants.ts's own
// header comment explains the design in prose and would trip a bare substring check the same way.
// This guard strips `//` and `/* */` comments before matching, exactly as that guard's repair does.
//
// Stated limits, same shape as the guard it mirrors: the comment-stripping is regex-shaped, not a
// real tokenizer -- a string literal containing a literal "//" on the same line as real code could
// have trailing text mis-treated as commented out. No line in motor-constants.ts does this today.
// A constructed/dynamic reference (e.g. string concatenation spelling out the word) would not be
// caught; true AST analysis would close this and was judged out of proportion to this batch.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import * as motorConstants from '@/src/features/c-session/motor-constants';

const here = dirname(fileURLToPath(import.meta.url));
const modulePath = resolve(here, '..', '..', 'features', 'c-session', 'motor-constants.ts');

function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
}

function codeReferencesLevelConcept(source: string): boolean {
  return /difficulty/i.test(stripComments(source));
}

test('motor-constants.ts exports only plain values, never a function', () => {
  const values = Object.values(motorConstants);
  assert.ok(values.length > 0, 'expected at least one exported constant');
  for (const value of values) {
    assert.notEqual(typeof value, 'function');
  }
});

test('motor-constants.ts source, with comments stripped, never references the level concept', () => {
  const source = readFileSync(modulePath, 'utf-8');
  assert.equal(codeReferencesLevelConcept(source), false);
});

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = '// safe to mention difficulty here in a comment\nexport const X = (difficultyLevel: number) => difficultyLevel;';
  assert.equal(codeReferencesLevelConcept(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string with only the comment (proves comment-stripping works)', () => {
  const commentOnly = '// this constant must never vary by difficulty\nexport const X = 1;';
  assert.equal(codeReferencesLevelConcept(commentOnly), false);
});
