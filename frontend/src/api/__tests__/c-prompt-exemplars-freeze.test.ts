// The frontend half of the prompt-exemplar artefact's drift protection (mirrors
// contract-freeze.test.ts's shape). The backend half lives in
// backend/tests/test_c_prompt_exemplars_freeze.py.
//
// THE RESIDUAL LIMIT THIS FILE MUST NOT CLAIM TO CLOSE. The backend's leak protection is
// allow-list construction: correct_answer_payload and difficulty_vector are never read when
// building an entry, so they are structurally absent rather than filtered out after the fact.
// That guarantee holds and this file re-checks it (the five-key allow-list assertion below).
// But if a generator template ever placed answer-bearing data inside `prompt_payload` itself —
// the field this artefact is required to carry — the artefact would carry it and nothing on
// either side of this project would catch it. That is a property of the generator templates,
// not of this artefact or its tests, and no assertion in this file inspects `prompt_payload`'s
// *content* for anything answer-shaped. A prohibited-term scan was deliberately not built here,
// for the same reason the backend didn't build one: C-NP-01/02/03's prompt_payload is
// `{"shown_sequence": [6, 7, 8]}` — the numbers shown to the child, correct and intended — which
// would trip a naive term scan on "sequenc", and the fix (a per-key exemption list) is tuning
// away the measurement rather than building one. This file proves the artefact is unmodified,
// complete, correctly shaped, and consistent with the registry. It does not, and cannot, prove
// its content is answer-free.
//
// Negative controls here are the same two kinds as c-template-registry-freeze.test.ts: permanent
// in-memory-mutation tests (below, committed and run every time) and a one-time real-file
// mutation + rebuild + revert demonstration, which is the supervisor's VERIFY step, not
// performed by this file or by the builder in this batch.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const exemplarsPath = resolve(repoRoot, 'backend', 'contract', 'c-prompt-exemplars.json');
const metaPath = resolve(repoRoot, 'backend', 'contract', 'c-prompt-exemplars.meta.json');
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
type ExemplarsArtefact = { entries: ExemplarEntry[]; label: string };
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

function hasCompleteCoverage(entries: readonly ExemplarEntry[], templateIds: readonly string[]): boolean {
  const byTemplate = new Map<string, Set<number>>();
  for (const entry of entries) {
    const levels = byTemplate.get(entry.game_task_template_id) ?? new Set<number>();
    levels.add(entry.difficulty_level);
    byTemplate.set(entry.game_task_template_id, levels);
  }
  return templateIds.every((id) => {
    const levels = byTemplate.get(id);
    if (!levels) return false;
    return [1, 2, 3, 4, 5].every((level) => levels.has(level));
  });
}

function hasNoDuplicatePairs(entries: readonly ExemplarEntry[]): boolean {
  const seen = new Set<string>();
  for (const entry of entries) {
    const key = `${entry.game_task_template_id}#${entry.difficulty_level}`;
    if (seen.has(key)) return false;
    seen.add(key);
  }
  return true;
}

function actionSpacesAgree(a: Record<string, string>, b: Record<string, string>): boolean {
  const aKeys = Object.keys(a).sort();
  const bKeys = Object.keys(b).sort();
  if (aKeys.length !== bKeys.length) return false;
  return aKeys.every((key, i) => key === bKeys[i] && a[key] === b[key]);
}

function isEmptyRecord(value: Record<string, unknown>): boolean {
  return Object.keys(value).length === 0;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

const BLANKS_TEMPLATE_IDS = ['C-NP-01', 'C-NP-02', 'C-NP-03'];

function templateIdsWithNonNullBlanks(entries: readonly ExemplarEntry[]): Set<string> {
  const ids = new Set<string>();
  for (const entry of entries) {
    if (entry.blanks !== null) ids.add(entry.game_task_template_id);
  }
  return ids;
}

test('the frozen exemplars artefact is byte-identical to its sidecar checksum', () => {
  const raw = readFileSync(exemplarsPath);
  const meta = JSON.parse(readFileSync(metaPath, 'utf-8'));
  const digest = createHash('sha256').update(raw).digest('hex');
  assert.equal(digest, meta.checksum_sha256);
});

test('the exemplars artefact has exactly 150 entries: 30 templates x levels 1-5, complete', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  assert.equal(artefact.entries.length, 150);
  assert.equal(hasNoDuplicatePairs(artefact.entries), true);
  assert.equal(
    hasCompleteCoverage(artefact.entries, registry.map((r) => r.template_id)),
    true,
  );
});

test('every exemplar entry has exactly the seven allow-listed fields and nothing else', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  for (const entry of artefact.entries) {
    assert.equal(
      hasExactlyTheAllowedFields(entry),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level} has an unexpected field set: ${Object.keys(entry).join(', ')}`,
    );
  }
});

test('every exemplar entry\'s valid_action_space agrees with the registry, key-and-type exact, at all five levels', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const registryById = new Map(registry.map((entry) => [entry.template_id, entry.valid_action_space]));
  for (const entry of artefact.entries) {
    const fromRegistry = registryById.get(entry.game_task_template_id);
    assert.ok(fromRegistry, `${entry.game_task_template_id} is not in the registry`);
    assert.equal(
      actionSpacesAgree(entry.valid_action_space, fromRegistry as Record<string, string>),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level}'s valid_action_space disagrees with the registry`,
    );
  }
});

test('interactive_assets is {} for all 150 entries', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  for (const entry of artefact.entries) {
    assert.equal(
      isEmptyRecord(entry.interactive_assets),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level} has a non-empty interactive_assets`,
    );
  }
});

test('prompt_text is a non-empty string on all 150 entries', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  for (const entry of artefact.entries) {
    assert.equal(
      isNonEmptyString(entry.prompt_text),
      true,
      `${entry.game_task_template_id}#${entry.difficulty_level} has a missing or empty prompt_text`,
    );
  }
});

test('blanks is non-null on exactly the C-NP-01/02/03 template set (15 entries) and null on the other 135', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const nonNullEntries = artefact.entries.filter((entry) => entry.blanks !== null);
  assert.equal(nonNullEntries.length, 15);
  assert.equal(artefact.entries.length - nonNullEntries.length, 135);

  const idsWithBlanks = templateIdsWithNonNullBlanks(artefact.entries);
  assert.deepEqual([...idsWithBlanks].sort(), [...BLANKS_TEMPLATE_IDS].sort());

  for (const entry of artefact.entries) {
    const shouldBeNonNull = BLANKS_TEMPLATE_IDS.includes(entry.game_task_template_id);
    assert.equal(
      entry.blanks !== null,
      shouldBeNonNull,
      `${entry.game_task_template_id}#${entry.difficulty_level}'s blanks nullity disagrees with its template's expected set membership`,
    );
  }
});

// --- Negative controls: mutated in-memory structures fed through the same predicates ---

test('negative control: a mutated byte changes the checksum', () => {
  const raw = readFileSync(exemplarsPath);
  const mutated = Buffer.from(raw);
  mutated[0] = mutated[0] ^ 0xff;
  const originalDigest = createHash('sha256').update(raw).digest('hex');
  const mutatedDigest = createHash('sha256').update(mutated).digest('hex');
  assert.notEqual(mutatedDigest, originalDigest);
});

test('negative control: removing a (template, level) entry breaks coverage', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const withoutOne = artefact.entries.slice(1);
  assert.equal(
    hasCompleteCoverage(withoutOne, registry.map((r) => r.template_id)),
    false,
  );
});

test('negative control: an eighth key on one entry is rejected by the allow-list check', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const tampered = { ...artefact.entries[0], extra_field: 'should not be here' } as unknown as ExemplarEntry;
  assert.equal(hasExactlyTheAllowedFields(tampered), false);
});

test('negative control: valid_action_space altered in one artefact but not the other is caught', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const registryById = new Map(registry.map((entry) => [entry.template_id, entry.valid_action_space]));
  const target = artefact.entries[0];
  const fromRegistry = registryById.get(target.game_task_template_id) as Record<string, string>;
  const tamperedActionSpace = { ...target.valid_action_space, extra_key: 'int' };
  assert.equal(actionSpacesAgree(tamperedActionSpace, fromRegistry), false);
});

test('negative control: an empty or non-string prompt_text is rejected', () => {
  assert.equal(isNonEmptyString(''), false);
  assert.equal(isNonEmptyString(undefined), false);
  assert.equal(isNonEmptyString('a real prompt'), true);
});

test('negative control: a template silently acquiring or losing non-null blanks is caught', () => {
  const artefact: ExemplarsArtefact = JSON.parse(readFileSync(exemplarsPath, 'utf-8'));
  const withAnExtraTemplateBlanked = artefact.entries.map((entry) =>
    entry.game_task_template_id === 'C-BT-01' ? { ...entry, blanks: 2 } : entry,
  );
  const idsWithBlanks = templateIdsWithNonNullBlanks(withAnExtraTemplateBlanked);
  assert.notDeepEqual([...idsWithBlanks].sort(), [...BLANKS_TEMPLATE_IDS].sort());

  const withOneLosingBlanks = artefact.entries.map((entry) =>
    entry.game_task_template_id === 'C-NP-01' ? { ...entry, blanks: null } : entry,
  );
  const idsStillWithBlanks = templateIdsWithNonNullBlanks(withOneLosingBlanks);
  assert.notDeepEqual([...idsStillWithBlanks].sort(), [...BLANKS_TEMPLATE_IDS].sort());
});

test('negative control: a non-empty interactive_assets is rejected', () => {
  assert.equal(isEmptyRecord({ hint: 'not allowed' }), false);
  assert.equal(isEmptyRecord({}), true);
});
