// 10.0b-fix: proves, as a test rather than a one-off grep, that no node builtin import and no
// `import.meta` is reachable from application code. Mirrors no-auth-bypass.test.ts's own
// precedent for this style ("A grep-as-a-test is inelegant, but it is exactly what stops this
// regression class cold") -- Hermes rejects `import.meta` and has no equivalent for node:fs /
// node:path / node:url, so a static occurrence of either, anywhere under src/ or app/ outside
// __tests__/ or scripts/, is a native-bundling failure waiting to happen, not a style nit.
//
// CORRECTION (recorded, not quietly fixed): the first version of this guard was a bare substring
// match (`/node:fs|node:path|node:url|import\.meta/`) over raw source text. The supervisor's
// suite run caught it failing on its own subject files -- src/api/dev-fixture-exemplars.ts and
// src/api/generated/c-prompt-exemplars.ts -- because both files' *comments* explain, in prose,
// why the real imports were removed, and those explanatory comments contain the very strings the
// substring match was looking for. Neither file had an actual import left; the guard could not
// tell a comment from code. This is the project's documented text-search-over-AST trap, in its
// purest form, and it was found in supervisor VERIFY, not by the builder -- the builder does not
// run this suite, by design, which is exactly why the division of labour caught it instead of
// shipping it.
//
// THE REPAIR, AND ITS STATED LIMITS. This version strips `//` line comments and `/* */` block
// comments before matching, then requires import/require *syntax*, not a bare substring, for the
// node-builtin check:
//   - `import ... from 'node:fs'` / `"node:fs"` (default, named, namespace, or bare side-effect
//     `import 'node:fs'`), including `import type ... from 'node:fs'`;
//   - `require('node:fs')`;
//   - dynamic `import('node:fs')`.
// `import.meta` is still a bare token match (word-bounded), since after comment-stripping there is
// no legitimate non-Hermes-fatal reason for that token to appear in application code.
//
// What this still does NOT catch, on purpose, named rather than silently accepted:
//   - a bare (non-`node:`-prefixed) specifier, e.g. `from 'fs'` / `from 'path'` / `from 'url'` --
//     out of scope per this batch's own acceptance criterion, which names `node:fs`/`node:path`/
//     `node:url` specifically; none of those bare specifiers exist in this codebase today;
//   - the comment-stripping regex is line/block-comment-shaped, not a real tokenizer -- a string
//     literal containing a literal `//` (e.g. a URL) could have text after it on the same line
//     incorrectly treated as commented-out. No file in src/ or app/ does this today; if one ever
//     does, this guard could under- or over-match on that one line;
//   - `require('node' + ':fs')` or any other constructed/dynamic specifier that isn't a static
//     string literal -- true AST analysis (e.g. via TypeScript's own compiler API) would close
//     this, and was not built here because it is a materially larger change than this batch's
//     scope; this is a real, named blind spot, not a false guarantee.
// This guard is stronger than the substring version and weaker than a real parser. That trade is
// deliberate and documented here so a future reader does not mistake "test passes" for "provably
// no node builtin is reachable."
//
// One test per candidate file (not one blanket test over the whole tree) so a regression's
// failure message names exactly which file broke, the same shape no-auth-bypass.test.ts uses for
// its guarded-file list.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve, sep } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..', '..', '..');

const NODE_BUILTIN_SPECIFIER = String.raw`['"]node:(?:fs|path|url)['"]`;
const NODE_BUILTIN_IMPORT_PATTERNS: RegExp[] = [
  // import ... from 'node:fs' / "node:fs" (default, named, namespace, `import type`)
  new RegExp(String.raw`\bfrom\s+${NODE_BUILTIN_SPECIFIER}`),
  // bare side-effect import: import 'node:fs'
  new RegExp(String.raw`^\s*import\s+${NODE_BUILTIN_SPECIFIER}`, 'm'),
  // require('node:fs')
  new RegExp(String.raw`\brequire\(\s*${NODE_BUILTIN_SPECIFIER}\s*\)`),
  // dynamic import('node:fs')
  new RegExp(String.raw`\bimport\(\s*${NODE_BUILTIN_SPECIFIER}\s*\)`),
];
const IMPORT_META_PATTERN = /\bimport\.meta\b/;

function isExcluded(relativePath: string): boolean {
  const segments = relativePath.split(sep);
  return segments.includes('__tests__') || segments.includes('scripts');
}

function collectSourceFiles(root: string): string[] {
  const results: string[] = [];
  const rootsToWalk = ['src', 'app'];
  for (const rootDir of rootsToWalk) {
    const absoluteRoot = join(root, rootDir);
    walk(absoluteRoot, root, results);
  }
  return results;
}

function walk(dir: string, frontendRootPath: string, results: string[]): void {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return;
  }
  for (const entry of entries) {
    const absolute = join(dir, entry);
    const stat = statSync(absolute);
    if (stat.isDirectory()) {
      walk(absolute, frontendRootPath, results);
    } else if (entry.endsWith('.ts') || entry.endsWith('.tsx')) {
      const relative = absolute.slice(frontendRootPath.length + 1);
      if (!isExcluded(relative)) results.push(relative);
    }
  }
}

// Strips `//` line comments and `/* */` block comments before matching. Documented limitation:
// this is regex-shaped comment stripping, not a real tokenizer, so a string literal containing a
// literal `//` could have trailing same-line text mistakenly treated as commented-out. See the
// header comment above for why this trade was accepted rather than building a full parser.
function stripComments(source: string): string {
  const withoutBlockComments = source.replace(/\/\*[\s\S]*?\*\//g, '');
  return withoutBlockComments.replace(/\/\/.*$/gm, '');
}

function findForbiddenUsage(source: string): string | null {
  const codeOnly = stripComments(source);
  for (const pattern of NODE_BUILTIN_IMPORT_PATTERNS) {
    const match = codeOnly.match(pattern);
    if (match) return match[0];
  }
  const metaMatch = codeOnly.match(IMPORT_META_PATTERN);
  if (metaMatch) return metaMatch[0];
  return null;
}

const candidateFiles = collectSourceFiles(frontendRoot);

// Sanity check on the test itself: if this ever finds zero files, the walk is broken, not the
// codebase clean -- a silently-empty file list would make every test below vacuously pass. (This
// project has already shipped that failure mode once, elsewhere; kept here deliberately.)
test('the source-file walk for src/ and app/ finds a non-trivial number of files', () => {
  assert.ok(candidateFiles.length > 20, `expected more than 20 candidate files, found ${candidateFiles.length}`);
});

for (const relativePath of candidateFiles) {
  test(`${relativePath} contains no node builtin import and no import.meta`, () => {
    const source = readFileSync(join(frontendRoot, relativePath), 'utf-8');
    const found = findForbiddenUsage(source);
    assert.equal(
      found,
      null,
      `${relativePath} must not import a node builtin (node:fs/node:path/node:url) or use ` +
        `import.meta -- found ${found ?? ''}`,
    );
  });
}
