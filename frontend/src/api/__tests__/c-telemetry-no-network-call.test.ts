// Structural proof that no network call exists anywhere in the local-only telemetry capture path
// (10.0b-ii SCOPE section 4; acceptance criterion 6). telemetry.ts is checked for `fetch(`,
// `XMLHttpRequest`, `WebSocket`, and any import from an API module -- with comments stripped first,
// for the same reason c-motor-constants.test.ts strips them: a guard that matches an explanatory
// comment instead of real code is exactly the defect the supervisor's VERIFY caught in
// 10.0b-fix's node-builtins guard (buildLog1.md, "Component C 10.0b-fix", the CORRECTION
// paragraph), and telemetry.ts's own header comment explains, in prose, why it avoids these APIs --
// which would trip a bare substring match on the comment alone.
//
// Stated limits, same shape as the guard this mirrors: regex-shaped comment-stripping, not a real
// tokenizer (a same-line "//" inside a string literal could be mishandled; no line here does
// this); no detection of a constructed/dynamic specifier (e.g. string concatenation spelling out
// "fetch"); and this file's own import list is the closed set of forbidden APIs checked -- it does
// not attempt a general "no side effect" proof.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const modulePath = resolve(here, '..', '..', 'features', 'c-session', 'telemetry.ts');

function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '');
}

const FORBIDDEN_PATTERNS: RegExp[] = [
  /\bfetch\s*\(/,
  /\bXMLHttpRequest\b/,
  /\bWebSocket\b/,
  /from\s+['"]@\/src\/api\//,
  /require\(\s*['"]@\/src\/api\//,
];

function containsNetworkCall(source: string): boolean {
  const code = stripComments(source);
  return FORBIDDEN_PATTERNS.some((pattern) => pattern.test(code));
}

test('telemetry.ts contains no network call and no import from an API module', () => {
  const source = readFileSync(modulePath, 'utf-8');
  assert.equal(containsNetworkCall(source), false);
});

test('the checker fires on a fabricated network call (negative control), proving it is not vacuous', () => {
  const fabricated = "export async function leak() { return fetch('https://example.invalid'); }";
  assert.equal(containsNetworkCall(fabricated), true);
});

test('the checker fires on a fabricated API import (negative control)', () => {
  const fabricated = "import { createComponentCApi } from '@/src/api/component-c-api';";
  assert.equal(containsNetworkCall(fabricated), true);
});

test('the checker does NOT fire when the same words appear only in a comment (proves comment-stripping works)', () => {
  const commentOnly = '// this module must never call fetch() or import from @/src/api/anything\nexport const X = 1;';
  assert.equal(containsNetworkCall(commentOnly), false);
});
