// Drift protection for the generated c-prompt-exemplars.ts module (10.0b-fix), mirroring
// contract-freeze.test.ts's staleness assertion for openapi-types.ts.
//
// Per the sibling freeze tests' own established division of labour (see
// c-template-registry-freeze.test.ts and c-prompt-exemplars-freeze.test.ts's header comments):
// a one-time REAL-FILE mutation + rebuild + revert demonstration is the supervisor's VERIFY step,
// not performed by this file or by the builder in this batch. This file's negative control is a
// permanent, committed, in-memory one: a byte-flipped copy of the committed generated file's
// content is asserted to differ from what the generator would produce right now.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { generate } from '../../../scripts/generate-c-prompt-exemplars.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const generatedPath = resolve(here, '..', 'generated', 'c-prompt-exemplars.ts');

test('the committed generated c-prompt-exemplars.ts is not stale relative to the frozen artefact', () => {
  const committed = readFileSync(generatedPath, 'utf-8');
  const freshlyGenerated = generate();
  assert.equal(committed, freshlyGenerated);
});

test('negative control: a one-character mutation of the generated output is caught by the equality check', () => {
  const freshlyGenerated = generate();
  const mutated = freshlyGenerated.slice(0, 20) + (freshlyGenerated[20] === 'x' ? 'y' : 'x') + freshlyGenerated.slice(21);
  assert.notEqual(mutated, freshlyGenerated);
});
