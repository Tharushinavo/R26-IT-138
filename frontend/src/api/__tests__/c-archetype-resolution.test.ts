// The resolution layer's own tests (10.0b-i): the archetype table's coverage against the frozen
// registry artefact, the field-kind layer's completeness and fail-closed behaviour, and
// `encodeActionPayload`'s correctness across all 30 registry entries -- including the four
// multi-key cases the archetype table was revised to accommodate (C-JB-04, C-TC-04, C-CC-01,
// C-SF-02). Mirrors c-template-registry-freeze.test.ts's negative-control style: permanent
// in-memory-mutation tests, run every time, proving each guard actually fires.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { resolveArchetype, archetypeTableTemplateIds } from '@/src/features/c-session/archetypes/registry';
import { bindFieldKind, isValidForKind } from '@/src/features/c-session/archetypes/field-kinds';
import { encodeActionPayload, keySetEquals } from '@/src/features/c-session/archetypes/encode-action-payload';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..', '..');
const registryPath = resolve(repoRoot, 'backend', 'contract', 'c-template-registry.json');

type RegistryEntry = { template_id: string; valid_action_space: Record<string, string> };

const registry: RegistryEntry[] = JSON.parse(readFileSync(registryPath, 'utf-8'));
const registryTemplateIds = registry.map((entry) => entry.template_id);

function idSetEquals(a: readonly string[], b: readonly string[]): boolean {
  const as = [...a].sort();
  const bs = [...b].sort();
  if (as.length !== bs.length) return false;
  return as.every((value, index) => value === bs[index]);
}

// One valid sample value per declared type, used to drive encodeActionPayload across every real
// registry entry. Not answer content -- these are arbitrary well-typed values, never read by the
// server as anything but a structurally valid submission in this test.
function sampleValueFor(declaredType: string): unknown {
  const binding = bindFieldKind(declaredType);
  assert.ok(binding, `no field-kind binding for declared type ${declaredType}`);
  switch (binding.kind) {
    case 'integer-field':
      return 3;
    case 'numeric-field':
      return 3.5;
    case 'boolean-control':
      return true;
    case 'ordered-integer-collection':
      return [1, 2, 3];
    case 'id-set-collection':
      return ['obj-1', 'obj-2'];
    case 'exact-choice-control':
      return binding.alternatives[0];
    default:
      throw new Error('unreachable');
  }
}

function sampleValuesFor(validActionSpace: Record<string, string>): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const [key, declaredType] of Object.entries(validActionSpace)) {
    values[key] = sampleValueFor(declaredType);
  }
  return values;
}

// --- Table-coverage assertion: the archetype table's id set equals the registry's 30 ---

test('the archetype table\'s template-id set exactly equals the registry\'s 30 ids', () => {
  assert.equal(registryTemplateIds.length, 30);
  assert.equal(idSetEquals(archetypeTableTemplateIds(), registryTemplateIds), true);
});

test('negative control: an id added to the table breaks set equality', () => {
  const withExtra = [...archetypeTableTemplateIds(), 'C-FAKE-99'];
  assert.equal(idSetEquals(withExtra, registryTemplateIds), false);
});

test('negative control: an id removed from the table breaks set equality', () => {
  const withoutOne = archetypeTableTemplateIds().slice(1);
  assert.equal(idSetEquals(withoutOne, registryTemplateIds), false);
});

// --- Every registry entry resolves to an archetype; every declared type is bound ---

test('every registry entry resolves to a non-null archetype', () => {
  for (const entry of registry) {
    const archetype = resolveArchetype(entry.template_id, entry.valid_action_space);
    assert.notEqual(archetype, null, `${entry.template_id} failed to resolve`);
  }
});

test('every declared type across the registry is bound by the field-kind layer', () => {
  for (const entry of registry) {
    for (const [key, declaredType] of Object.entries(entry.valid_action_space)) {
      assert.notEqual(
        bindFieldKind(declaredType),
        null,
        `${entry.template_id}.${key}: declared type "${declaredType}" is not bound`,
      );
    }
  }
});

// --- resolveArchetype's null paths ---

test('resolveArchetype returns null for an unknown template id', () => {
  assert.equal(resolveArchetype('C-DOES-NOT-EXIST', {}), null);
});

test('resolveArchetype returns null for a template id that is an Object.prototype member name', () => {
  assert.equal(resolveArchetype('constructor', {}), null);
  assert.equal(resolveArchetype('toString', {}), null);
  assert.equal(resolveArchetype('__proto__', {}), null);
  assert.equal(resolveArchetype('hasOwnProperty', {}), null);
});

test('resolveArchetype returns null when valid_action_space carries an unrecognised declared type', () => {
  // C-JB-01 is a real, known id; its declared type is deliberately corrupted here in memory only.
  assert.equal(resolveArchetype('C-JB-01', { submitted_total: 'float' }), null);
});

// --- bindFieldKind / isValidForKind: the boolean trap and wrong-typed elements ---

test('bindFieldKind returns null for an unrecognised type string, never a default', () => {
  assert.equal(bindFieldKind('float'), null);
  assert.equal(bindFieldKind('str'), null);
  assert.equal(bindFieldKind(''), null);
  assert.equal(bindFieldKind('|'), null);
  assert.equal(bindFieldKind('same|'), null);
});

test('int rejects a boolean', () => {
  const binding = bindFieldKind('int')!;
  assert.equal(isValidForKind(binding, true), false);
  assert.equal(isValidForKind(binding, false), false);
  assert.equal(isValidForKind(binding, 3), true);
});

test('number rejects a boolean', () => {
  const binding = bindFieldKind('number')!;
  assert.equal(isValidForKind(binding, true), false);
  assert.equal(isValidForKind(binding, 3.5), true);
  assert.equal(isValidForKind(binding, 3), true);
});

test('list[int] rejects a wrong-typed element', () => {
  const binding = bindFieldKind('list[int]')!;
  assert.equal(isValidForKind(binding, [1, 2, 'x']), false);
  assert.equal(isValidForKind(binding, [1, 2, 3]), true);
});

test('list[str] rejects a wrong-typed element', () => {
  const binding = bindFieldKind('list[str]')!;
  assert.equal(isValidForKind(binding, ['a', 1]), false);
  assert.equal(isValidForKind(binding, ['a', 'b']), true);
});

test('a pipe-string control rejects a value outside its parsed alternatives', () => {
  const binding = bindFieldKind('same|changed')!;
  assert.equal(isValidForKind(binding, 'different'), false);
  assert.equal(isValidForKind(binding, 'same'), true);
  assert.equal(isValidForKind(binding, 'changed'), true);
});

// --- encodeActionPayload: correctness across all 30 registry entries ---

test('encodeActionPayload produces a key set exactly equal to valid_action_space for all 30 registry entries', () => {
  for (const entry of registry) {
    const values = sampleValuesFor(entry.valid_action_space);
    const payload = encodeActionPayload(entry.valid_action_space, values);
    assert.notEqual(payload, null, `${entry.template_id} failed to encode`);
    assert.equal(
      keySetEquals(payload as Record<string, unknown>, entry.valid_action_space),
      true,
      `${entry.template_id}'s encoded key set disagrees with valid_action_space`,
    );
    assert.deepEqual(payload, values, `${entry.template_id}'s encoded values were altered`);
  }
});

// The four multi-key cases the archetype table was revised to accommodate, named individually so
// a regression in any one of them fails by name rather than being absorbed into the loop above.
for (const templateId of ['C-JB-04', 'C-TC-04', 'C-CC-01', 'C-SF-02']) {
  test(`encodeActionPayload emits both declared keys for ${templateId}`, () => {
    const entry = registry.find((candidate) => candidate.template_id === templateId);
    assert.ok(entry, `${templateId} not found in the registry`);
    assert.equal(Object.keys(entry!.valid_action_space).length, 2, `${templateId} is expected to declare two keys`);

    const values = sampleValuesFor(entry!.valid_action_space);
    const payload = encodeActionPayload(entry!.valid_action_space, values);
    assert.notEqual(payload, null);
    assert.equal(keySetEquals(payload as Record<string, unknown>, entry!.valid_action_space), true);
  });
}

// --- encodeActionPayload: fail-closed paths and negative controls ---

test('encodeActionPayload returns null when a required key is missing from values', () => {
  const validActionSpace = { submitted_total: 'int' };
  assert.equal(encodeActionPayload(validActionSpace, {}), null);
});

test('encodeActionPayload returns null when the declared type is unrecognised', () => {
  const validActionSpace = { some_field: 'float' };
  assert.equal(encodeActionPayload(validActionSpace, { some_field: 3 }), null);
});

test('encodeActionPayload rejects a boolean where int is declared', () => {
  const validActionSpace = { submitted_total: 'int' };
  assert.equal(encodeActionPayload(validActionSpace, { submitted_total: true }), null);
});

test('encodeActionPayload rejects a boolean where number is declared', () => {
  const validActionSpace = { marker_position: 'number' };
  assert.equal(encodeActionPayload(validActionSpace, { marker_position: false }), null);
});

test('encodeActionPayload rejects a wrong-typed list element', () => {
  const validActionSpace = { jumps: 'list[int]' };
  assert.equal(encodeActionPayload(validActionSpace, { jumps: [1, 'not-a-number'] }), null);
});

test('negative control: an extra key on an encoded payload is rejected by keySetEquals', () => {
  const validActionSpace = { submitted_total: 'int' };
  const payload = encodeActionPayload(validActionSpace, { submitted_total: 5 })!;
  const tampered = { ...payload, extra_key: 'should not be here' };
  assert.equal(keySetEquals(tampered, validActionSpace), false);
});

test('negative control: a missing key on an encoded payload is rejected by keySetEquals', () => {
  const validActionSpace = { exchange_performed: 'bool', submitted_sum: 'int' };
  const payload = encodeActionPayload(validActionSpace, { exchange_performed: true, submitted_sum: 5 })!;
  const { submitted_sum: _omit, ...missingOne } = payload;
  assert.equal(keySetEquals(missingOne, validActionSpace), false);
});
