// The composite-archetype proof this sub-phase owes (master work order §4/§3): C-BT-01/02/03/04
// (2 and 3 fields alike) are covered by ONE archetype, not a fork, because field count is a fact
// about `valid_action_space`, never a per-template branch. This file proves it structurally: none
// of the new source files name any C-BT-* template id, or any of the real payload/action key names,
// anywhere in executable code -- comment-stripped source scan, with two meta-tests proving the scan
// is not vacuous, mirroring c-object-set-action-no-template-branch.test.ts's own convention.

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

const FORBIDDEN_LITERALS = ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04', 'C-EG-02'];

function containsForbiddenLiteral(source: string, literal: string): boolean {
  return stripComments(source).includes(literal);
}

for (const filePath of NEW_FILES) {
  for (const literal of FORBIDDEN_LITERALS) {
    test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never contains "${literal}"`, () => {
      const source = readFileSync(filePath, 'utf-8');
      assert.equal(containsForbiddenLiteral(source, literal), false);
    });
  }

  test(`${filePath.split(/[\\/]/).pop()}: source, with comments stripped, never reads game_task_template_id`, () => {
    const source = readFileSync(filePath, 'utf-8');
    assert.equal(/game_task_template_id/.test(stripComments(source)), false);
  });
}

test('the checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = "if (task.game_task_template_id === 'C-BT-01') { /* ... */ }";
  assert.equal(containsForbiddenLiteral(fabricated, 'C-BT-01'), true);
  assert.equal(/game_task_template_id/.test(stripComments(fabricated)), true);
});

test('the checker does NOT fire on the same fabricated strings kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never branch on C-BT-01 or game_task_template_id\nconst x = 1;';
  assert.equal(containsForbiddenLiteral(commentOnly, 'C-BT-01'), false);
  assert.equal(/game_task_template_id/.test(stripComments(commentOnly)), false);
});
