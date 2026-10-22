// Leak guard specific to `line-position` (10d): `target_position` is the task's GIVEN, not the
// answer, but it must still never be rendered as a standalone numeral token OUTSIDE the line itself
// -- see line-position-logic.ts's header for why the line's own tick labels (which show every
// position, not just the target) are not the same kind of leak a separate printed digit would be.
// This proves the surface only ever hands `target_position` to `UnitStepper`'s own
// `targetForwardOffset` prop, and never renders `spec.targetPosition` inside an `<AppText>` the way
// `payloadValues` (a real, ordinary numeral token) are rendered.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const surfacePath = resolve(here, '..', '..', 'features', 'c-session', 'archetypes', 'line-position-surface.tsx');

function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// Matches spec.targetPosition being interpolated directly into JSX text content, e.g.
// `<AppText>{spec.targetPosition}</AppText>` or `{spec.targetPosition}` inside a text node -- the
// direct textual shape a leak would take in this codebase's own style.
function codeRendersTargetPositionAsText(source: string): boolean {
  const stripped = stripComments(source);
  return /<AppText[^>]*>\s*\{[^}]*spec\.targetPosition[^}]*\}\s*<\/AppText>/.test(stripped);
}

test('line-position-surface.tsx never renders spec.targetPosition inside an AppText node', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  assert.equal(codeRendersTargetPositionAsText(source), false);
});

test('line-position-surface.tsx passes spec.targetPosition only to UnitStepper\'s targetForwardOffset prop', () => {
  const source = readFileSync(surfacePath, 'utf-8');
  const stripped = stripComments(source);
  assert.match(stripped, /targetForwardOffset=\{spec\.targetPosition\}/);
  // Exactly one occurrence of `spec.targetPosition` in executable code: the prop above. A second
  // occurrence anywhere else would be a second, unaccounted-for use of the value.
  const occurrences = (stripped.match(/spec\.targetPosition/g) ?? []).length;
  assert.equal(occurrences, 1);
});

test('the leak checker fires on a fabricated violation (negative control), proving it is not vacuous', () => {
  const fabricated = '<AppText>{spec.targetPosition}</AppText>';
  assert.equal(codeRendersTargetPositionAsText(fabricated), true);
});

test('the leak checker does NOT fire on the same fabricated string kept only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// must never render <AppText>{spec.targetPosition}</AppText>\nconst x = 1;';
  assert.equal(codeRendersTargetPositionAsText(commentOnly), false);
});
