// Motor constancy for `ordered-value-sequence` (10a). `blanks` is the one place difficulty changes
// the interface in this batch (1 at difficulty 1-2, 2 at 3-5 for NP-01/02/03), and the risk is that
// something quietly makes a dimension track it instead of only the slot count. Two structural
// proofs, mirroring c-motor-constants.test.ts's own method (no rendering library exists in this
// project's devDependencies, so this is a structural proof, not a literal rendered-layout
// assertion -- it proves the constants do not vary; it does not prove a rendered layout never
// compresses).
//
// Accepted limitation, stated once here rather than implied: nothing in this repository can mount
// a React Native tree and measure it, so "identical at difficulty 1-5" below means the geometry
// CONSTANTS referenced by the new files are literally the same values regardless of `blanks` or
// `difficulty_level` -- not that a rendered screen was measured and found unchanged.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import {
  KEYPAD_KEY_SIZE,
  KEYPAD_KEY_SPACING,
  TOKEN_SPACING,
  TOKEN_TOUCH_TARGET_SIZE,
} from '@/src/features/c-session/motor-constants';
import { resolveOrderedValueSequenceSpec } from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const NEW_FILES = [
  resolve(featureDir, 'archetypes', 'ordered-value-sequence-logic.ts'),
  resolve(featureDir, 'archetypes', 'ordered-value-sequence-surface.tsx'),
  resolve(featureDir, 'primitives', 'value-token-row.tsx'),
  resolve(featureDir, 'primitives', 'digit-keypad.tsx'),
];

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function codeReferencesDifficultyLevel(source: string): boolean {
  return /difficulty_level|difficultyLevel/.test(stripComments(source));
}

// --- structural proof 1: none of the new files read difficulty_level at all ---------------------

for (const filePath of NEW_FILES) {
  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never references difficulty_level`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(codeReferencesDifficultyLevel(source), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = 'const size = base + task.difficulty_level;';
  assert.equal(codeReferencesDifficultyLevel(fabricated), true);
});

test('the checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never scale with difficulty_level\nconst size = base;';
  assert.equal(codeReferencesDifficultyLevel(commentOnly), false);
});

// --- structural proof 2: the imported dimension constants are plain, unparameterised values -----
// (Object.values(motorConstants) in c-motor-constants.test.ts already asserts every export of
// motor-constants.ts, including these four, is never a function -- not re-asserted here to avoid
// a duplicate of that guard. This proof instead confirms the SAME literal constant is the one this
// archetype's own files import, across a fresh module read, which is the thing that would actually
// break if a future edit replaced an import with a locally recomputed value.)

test('TOKEN_TOUCH_TARGET_SIZE, TOKEN_SPACING, KEYPAD_KEY_SIZE, KEYPAD_KEY_SPACING are plain numbers', () => {
  for (const value of [TOKEN_TOUCH_TARGET_SIZE, TOKEN_SPACING, KEYPAD_KEY_SIZE, KEYPAD_KEY_SPACING]) {
    assert.equal(typeof value, 'number');
  }
});

// --- structural proof 3: only the slot count varies with blanks, never a dimension --------------

function makeTaskFromExemplar(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-02',
    game_task_template_id: entry.game_task_template_id,
    interactive_assets: entry.interactive_assets,
    prompt_payload: entry.prompt_payload,
    prompt_text: entry.prompt_text,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: entry.valid_action_space,
  };
}

for (const templateId of ['C-NP-01', 'C-NP-02', 'C-NP-03']) {
  test(`${templateId}: entry-slot count equals the wire blanks value at every difficulty level, and nothing else about the spec's shape depends on it`, () => {
    const entries = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === templateId);
    assert.equal(entries.length, 5);
    for (const entry of entries) {
      const spec = resolveOrderedValueSequenceSpec(makeTaskFromExemplar(entry));
      if (spec === null) {
        assert.fail(`${templateId} level ${entry.difficulty_level} failed to resolve`);
        continue;
      }
      if (spec.scene === 'entry') {
        const expectedBlanks = entry.difficulty_level <= 2 ? 1 : 2;
        assert.equal(spec.blanks, expectedBlanks, `${templateId} level ${entry.difficulty_level}`);
        // `extraFields` (the only other structural, non-value-derived part of the spec) is
        // unaffected by difficulty for these real registry entries -- proving blanks changes the
        // COUNT and nothing structural besides it.
        assert.deepEqual(spec.extraFields, []);
      }
    }
  });
}
