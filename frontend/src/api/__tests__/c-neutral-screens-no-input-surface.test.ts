// Structural proof that the fail-closed frame and the technical-block screen offer no input
// surface (10.0b-ii SCOPE sections 1-2; acceptance criterion 3). B's renderers/registry.ts
// documents why this matters: a fallback input lets a child enter something the item cannot
// accept and then be marked wrong for it -- exactly the failure the authority boundary exists to
// prevent. There is no component-rendering test capability in this project, so the proof is a
// source-text scan of the three files in this doctrine's path
// (neutral-message-screen.tsx, fail-closed-frame.tsx, technical-block-screen.tsx) for TextInput,
// an `editable` prop, or an import from an archetypes or renderer module -- with comments stripped
// first, for the same reason c-motor-constants.test.ts and c-telemetry-no-network-call.test.ts
// strip them: a guard that matches an explanatory comment instead of real code is exactly the
// defect the supervisor's VERIFY caught in 10.0b-fix's node-builtins guard (buildLog1.md,
// "Component C 10.0b-fix", the CORRECTION paragraph), and all three files here explain this
// doctrine in prose, which would trip a bare substring match on the comment alone.
//
// Stated limits, same shape as the guard this mirrors: regex-shaped comment-stripping, not a real
// tokenizer (a same-line "//" inside a string literal could be mishandled; no line in these three
// files does this today); no detection of a constructed/dynamic specifier; and this checks only
// the closed set of three files that make up the neutral-screen doctrine, not every `.tsx` in the
// tree -- a future fourth file in this family would need to be added to the list explicitly.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const featureDir = resolve(here, '..', '..', 'features', 'c-session');

const GUARDED_FILES = [
  'neutral-message-screen.tsx',
  'fail-closed-frame.tsx',
  'technical-block-screen.tsx',
];

function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
}

const FORBIDDEN_PATTERNS: RegExp[] = [
  /\bTextInput\b/,
  /\beditable\s*[:=]/,
  /from\s+['"][^'"]*\/archetypes\//,
  /from\s+['"][^'"]*\/renderers\//,
];

function containsInputSurface(source: string): boolean {
  const code = stripComments(source);
  return FORBIDDEN_PATTERNS.some((pattern) => pattern.test(code));
}

for (const fileName of GUARDED_FILES) {
  test('offers no input surface: ' + fileName, () => {
    const source = readFileSync(resolve(featureDir, fileName), 'utf-8');
    assert.equal(containsInputSurface(source), false);
  });
}

test('the checker fires on a fabricated TextInput import (negative control), proving it is not vacuous', () => {
  const fabricated = "import { TextInput } from 'react-native';\nexport const X = TextInput;";
  assert.equal(containsInputSurface(fabricated), true);
});

test('the checker fires on a fabricated editable prop (negative control)', () => {
  const fabricated = 'const el = <View editable={true} />;';
  assert.equal(containsInputSurface(fabricated), true);
});

test('the checker fires on a fabricated archetypes/renderers import (negative control)', () => {
  const fabricated = "import { ChoiceGrid } from '@/src/features/session/renderers/choice-grid';";
  assert.equal(containsInputSurface(fabricated), true);
});

test('the checker does NOT fire when the same words appear only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// never render a TextInput here, and never import from archetypes/ or renderers/\nexport const X = 1;';
  assert.equal(containsInputSurface(commentOnly), false);
});
