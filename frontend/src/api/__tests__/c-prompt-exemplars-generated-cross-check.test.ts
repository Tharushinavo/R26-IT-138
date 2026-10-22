// Cross-check for the generated c-prompt-exemplars.ts module (10.0b-fix): asserts the generated
// copy agrees with the frozen backend artefact it was derived from -- it did not lose or alter
// anything in translation. This is deliberately independent of
// c-prompt-exemplars-generated-freeze.test.ts (which proves the committed file matches what the
// generator produces right now) and of the existing c-prompt-exemplars-freeze.test.ts (which
// proves the frozen artefact itself is well-formed) -- this file reads the frozen artefact
// directly and compares it to the generated module's exported data, not to itself.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { EXEMPLAR_ENTRIES, TEST_FIXTURE_ONLY_EXEMPLARS_LABEL } from '../generated/c-prompt-exemplars';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const exemplarsPath = resolve(repoRoot, 'backend', 'contract', 'c-prompt-exemplars.json');
const registryPath = resolve(repoRoot, 'backend', 'contract', 'c-template-registry.json');

type ExemplarEntry = {
  game_task_template_id: string;
  difficulty_level: number;
  prompt_payload: Record<string, unknown>;
  interactive_assets: Record<string, unknown>;
  valid_action_space: Record<string, string>;
  blanks: number | null;
  prompt_text: string;
};
type RegistryEntry = { template_id: string; valid_action_space: Record<string, string> };

const ALLOWED_ENTRY_FIELDS = [
  'blanks',
  'difficulty_level',
  'game_task_template_id',
  'interactive_assets',
  'prompt_payload',
  'prompt_text',
  'valid_action_space',
].sort();

function hasExactlyTheAllowedFields(entry: ExemplarEntry): boolean {
  const keys = Object.keys(entry).sort();
  return keys.length === ALLOWED_ENTRY_FIELDS.length && keys.every((key, i) => key === ALLOWED_ENTRY_FIELDS[i]);
}

function actionSpacesAgree(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a).sort();
  const bKeys = Object.keys(b).sort();
  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every((key, i) => key === bKeys[i] && a[key] === b[key]);
}

test('the generated module carries the TEST_FIXTURE_ONLY label from the frozen artefact', () => {
  const artefact: { label: string } = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  assert.equal(artefact.label, 'TEST_FIXTURE_ONLY');
  assert.equal(TEST_FIXTURE_ONLY_EXEMPLARS_LABEL, 'TEST_FIXTURE_ONLY');
  assert.equal(TEST_FIXTURE_ONLY_EXEMPLARS_LABEL, artefact.label);
});

test('the generated module has exactly the 150 entries the frozen artefact declares', () => {
  const artefact: { entries: ExemplarEntry[] } = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  assert.equal(artefact.entries.length, 150);
  assert.equal(EXEMPLAR_ENTRIES.length, 150);
  assert.deepEqual(EXEMPLAR_ENTRIES, artefact.entries);
});

test('every generated entry has exactly the seven allow-listed fields and nothing else', () => {
  for (const entry of EXEMPLAR_ENTRIES) {
    assert.equal(
      hasExactlyTheAllowedFields(entry),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level} has an unexpected field set: ${Object.keys(entry).join(', ')}`,
    );
  }
});

test("every generated entry's valid_action_space agrees with the registry", () => {
  const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const registryById = new Map(registry.map((entry) => [entry.template_id, entry.valid_action_space]));
  for (const entry of EXEMPLAR_ENTRIES) {
    const fromRegistry = registryById.get(entry.game_task_template_id);
    assert.ok(fromRegistry, `${entry.game_task_template_id} is not in the registry`);
    assert.equal(
      actionSpacesAgree(entry.valid_action_space, fromRegistry as Record<string, string>),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level}'s valid_action_space disagrees with the registry`,
    );
  }
});

test('negative control: an eighth key on one generated entry is rejected by the allow-list check', () => {
  const tampered = { ...EXEMPLAR_ENTRIES[0], extra_field: 'should not be here' } as unknown as ExemplarEntry;
  assert.equal(hasExactlyTheAllowedFields(tampered), false);
});
