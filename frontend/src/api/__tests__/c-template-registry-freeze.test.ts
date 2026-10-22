// The frontend half of the C template registry's drift protection (mirrors
// contract-freeze.test.ts's shape for the same purpose against a different artefact). The
// backend half lives in backend/tests/test_c_template_registry_freeze.py; until both halves
// exist the protection is one-sided, which is the exact condition that let the generated
// TypeScript types rot for eighteen commits (see backend/buildLog1.md, "C template registry").
//
// Two kinds of negative control appear here, and they prove different things:
//   - The four `mutated structural assertions` tests below feed hand-mutated in-memory clones of
//     the real registry through the same predicate functions the primary tests use, and assert
//     each predicate rejects. These are permanent, committed, and run every time.
//   - A one-time REAL-FILE mutation (edit the committed bytes, rebuild, observe the checksum
//     test go red, revert, and prove the revert byte-perfect by re-hashing) is NOT performed by
//     this test file and is not run by the builder in this batch — in-memory re-hashing proves
//     `createHash` works, not that this file reads the real artefact on disk. That demonstration
//     is the supervisor's VERIFY step, the same division of labour every prior artefact-freeze
//     batch in this project used (the registry and exemplar backend batches were demonstrated by
//     the supervisor, never the builder).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const registryPath = resolve(repoRoot, 'backend', 'contract', 'c-template-registry.json');
const metaPath = resolve(repoRoot, 'backend', 'contract', 'c-template-registry.meta.json');

type RegistryEntry = { template_id: string; valid_action_space: Record<string, string> };

// Recognised type-string vocabulary, per action_payload_validation.py's own docstring:
// int | bool | number | list[X] | a pipe-string exact-choice set (e.g. "same|changed"). A
// pipe-string requires at least two non-empty, pipe-free alternatives — "|" alone or a value
// with an empty alternative is not a valid choice set and must not be silently accepted.
const PIPE_STRING = /^[^|]+(\|[^|]+)+$/;
const LIST_TYPE = /^list\[.+\]$/;

function isRecognisedType(declaredType: string): boolean {
  if (declaredType === 'int' || declaredType === 'bool' || declaredType === 'number') return true;
  if (LIST_TYPE.test(declaredType)) return true;
  if (PIPE_STRING.test(declaredType)) return true;
  return false;
}

function isSortedByTemplateId(entries: readonly RegistryEntry[]): boolean {
  for (let i = 1; i < entries.length; i += 1) {
    if (entries[i - 1].template_id >= entries[i].template_id) return false;
  }
  return true;
}

function hasExactlyTheAllowedFields(entry: RegistryEntry): boolean {
  const keys = Object.keys(entry).sort();
  return keys.length === 2 && keys[0] === 'template_id' && keys[1] === 'valid_action_space';
}

function everyDeclaredTypeIsRecognised(entries: readonly RegistryEntry[]): boolean {
  return entries.every((entry) =>
    Object.values(entry.valid_action_space).every((declaredType) => isRecognisedType(declaredType)),
  );
}

function hasUniqueTemplateIds(entries: readonly RegistryEntry[]): boolean {
  return new Set(entries.map((entry) => entry.template_id)).size === entries.length;
}

test('the frozen registry artefact is byte-identical to its sidecar checksum', () => {
  const raw = readFileSync(registryPath);
  const meta = JSON.parse(readFileSync(metaPath, 'utf-8'));
  const digest = createHash('sha256').update(raw).digest('hex');
  assert.equal(digest, meta.checksum_sha256);
});

test('the registry has exactly 30 entries, 30 unique ids, sorted', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  assert.equal(entries.length, 30);
  assert.equal(hasUniqueTemplateIds(entries), true);
  assert.equal(isSortedByTemplateId(entries), true);
});

test('every registry entry has exactly the two allowed fields and nothing else', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  for (const entry of entries) {
    assert.equal(
      hasExactlyTheAllowedFields(entry),
      true,
      `${entry.template_id} has an unexpected field set: ${Object.keys(entry).join(', ')}`,
    );
  }
});

test('every declared type string in the registry is drawn from the recognised vocabulary', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  assert.equal(everyDeclaredTypeIsRecognised(entries), true);
});

// --- Negative controls: mutated in-memory structures fed through the same predicates ---

test('negative control: a mutated byte changes the checksum', () => {
  const raw = readFileSync(registryPath);
  const mutated = Buffer.from(raw);
  mutated[0] = mutated[0] ^ 0xff;
  const originalDigest = createHash('sha256').update(raw).digest('hex');
  const mutatedDigest = createHash('sha256').update(mutated).digest('hex');
  assert.notEqual(mutatedDigest, originalDigest);
});

test('negative control: a duplicated id is rejected by the uniqueness check', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const withDuplicate = [...entries, { ...entries[0] }];
  assert.equal(hasUniqueTemplateIds(withDuplicate), false);
});

test('negative control: an out-of-order id is rejected by the sortedness check', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  assert.ok(entries.length >= 2, 'registry must have at least two entries to test ordering');
  const outOfOrder = [entries[1], entries[0], ...entries.slice(2)];
  assert.equal(isSortedByTemplateId(outOfOrder), false);
});

test('negative control: an unrecognised declared type is rejected, never falls through', () => {
  const entries: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
  const withBadType = entries.map((entry, index) =>
    index === 0
      ? { ...entry, valid_action_space: { ...entry.valid_action_space, [Object.keys(entry.valid_action_space)[0]]: 'float' } }
      : entry,
  );
  assert.equal(isRecognisedType('float'), false);
  assert.equal(everyDeclaredTypeIsRecognised(withBadType), false);
});

test('negative control: a bare pipe or a pipe-string with an empty alternative is rejected', () => {
  assert.equal(isRecognisedType('|'), false);
  assert.equal(isRecognisedType('same|'), false);
  assert.equal(isRecognisedType('|changed'), false);
  assert.equal(isRecognisedType('same|changed'), true);
});
