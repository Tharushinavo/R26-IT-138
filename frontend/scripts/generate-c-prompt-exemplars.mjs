#!/usr/bin/env node
// Mechanically converts the frozen backend prompt-exemplar artefact into a bundler-safe
// TypeScript module. No hand-authored entries: every field comes straight from
// backend/contract/c-prompt-exemplars.json. Re-run via `npm run generate:c-prompt-exemplars`
// whenever the backend re-freezes that artefact; the drift test fails if the committed output
// diverges from what this script would produce right now.
//
// Why this script exists (10.0b-fix): the previous approach (dev-fixture-exemplars.ts reading
// the artefact off disk via node:fs + import.meta.url at runtime) fails to bundle for iOS/Android
// -- Hermes rejects `import.meta`, and node:fs has no React Native equivalent. This mirrors the
// existing generate-contract-types.mjs pattern (second instance of it): read the frozen artefact
// here, in a Node-only script that is never bundled, and emit a plain data-and-types module that
// the app can import with zero node builtins and zero import.meta.

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..');
const exemplarsPath = resolve(repoRoot, 'backend', 'contract', 'c-prompt-exemplars.json');
const outputPath = resolve(here, '..', 'src', 'api', 'generated', 'c-prompt-exemplars.ts');

export function generate() {
  const artefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const label = artefact.label;
  if (label !== 'TEST_FIXTURE_ONLY') {
    throw new Error(
      `c-prompt-exemplars.json's label is ${JSON.stringify(label)}, not "TEST_FIXTURE_ONLY" -- ` +
        'refusing to silently relabel the generated module. Update this script deliberately if the ' +
        'artefact\'s label has genuinely changed.',
    );
  }

  const header = [
    '// GENERATED FILE — do not hand-edit.',
    '// Source: backend/contract/c-prompt-exemplars.json (label: "TEST_FIXTURE_ONLY").',
    '// Regenerate with `npm run generate:c-prompt-exemplars` after the backend re-freezes the artefact.',
    '//',
    '// Data and types only. No node builtin, no `import.meta` -- this module is imported by',
    '// application code and must survive Hermes bundling for iOS and Android.',
    '',
  ].join('\n');

  const typeBlock = [
    'export type ExemplarEntry = {',
    '  blanks: number | null;',
    '  difficulty_level: number;',
    '  game_task_template_id: string;',
    '  interactive_assets: Record<string, unknown>;',
    '  prompt_payload: Record<string, unknown>;',
    '  prompt_text: string;',
    '  valid_action_space: Record<string, string>;',
    '};',
  ].join('\n');

  const labelConst = `export const TEST_FIXTURE_ONLY_EXEMPLARS_LABEL = ${JSON.stringify(label)};`;

  const dataConst =
    'export const EXEMPLAR_ENTRIES: readonly ExemplarEntry[] = ' +
    JSON.stringify(artefact.entries, null, 2) +
    ';';

  return `${header}\n${typeBlock}\n\n${labelConst}\n\n${dataConst}\n`;
}

function main() {
  const content = generate();
  writeFileSync(outputPath, content);
  console.log(`Wrote ${outputPath}`);
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) main();
