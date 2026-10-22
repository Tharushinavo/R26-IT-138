// `resolvePartitionAllocationSpec` (10g): resolution over C-EG-01 and C-SF-01 (the two fixed-bin-
// count templates), proving one resolver covers both with no per-template branch, plus the
// bin-count-excluded-from-payloadValues rule and the by-name collection-key vocabulary.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES, type ExemplarEntry } from '@/src/api/generated/c-prompt-exemplars';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';

function makeTask(entry: ExemplarEntry, familyId: string): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: familyId,
    game_task_template_id: entry.game_task_template_id,
    interactive_assets: entry.interactive_assets,
    prompt_payload: entry.prompt_payload,
    prompt_text: entry.prompt_text,
    representation_mode: 'TEST_FIXTURE_ONLY_REPRESENTATION',
    request_id: 'req-1',
    scaffold_state: 'C0',
    skill_id: 'number-sense',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: entry.valid_action_space,
  };
}

const EG01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-01');
const SF01_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-SF-01');

test('C-EG-01 and C-SF-01: exactly 5 exemplar rows (difficulty 1-5) each, all present in the frozen fixture', () => {
  assert.equal(EG01_ENTRIES.length, 5);
  assert.equal(SF01_ENTRIES.length, 5);
});

test('C-EG-01: resolves at every difficulty level, binCount from number_of_groups, group_size the only payloadValue', () => {
  for (const entry of EG01_ENTRIES) {
    const spec = resolvePartitionAllocationSpec(makeTask(entry, 'C-GF-07'));
    if (spec === null) {
      assert.fail(`C-EG-01 level ${entry.difficulty_level} failed to resolve`);
      continue;
    }
    const payload = entry.prompt_payload as { number_of_groups: number; group_size: number };
    assert.equal(spec.binCount, payload.number_of_groups, `level ${entry.difficulty_level}`);
    assert.equal(spec.binsKey, 'groups');
    assert.deepEqual(spec.payloadValues.map((v) => v.key), ['group_size']);
    assert.equal(spec.payloadValues[0]!.value, payload.group_size);
    assert.equal(spec.promptText, entry.prompt_text);
    assert.deepEqual(spec.interactiveAssets, entry.interactive_assets);
  }
});

test('C-SF-01: resolves at every difficulty level, binCount from recipient_count, total the only payloadValue', () => {
  for (const entry of SF01_ENTRIES) {
    const spec = resolvePartitionAllocationSpec(makeTask(entry, 'C-GF-08'));
    if (spec === null) {
      assert.fail(`C-SF-01 level ${entry.difficulty_level} failed to resolve`);
      continue;
    }
    const payload = entry.prompt_payload as { recipient_count: number; total: number };
    assert.equal(spec.binCount, payload.recipient_count, `level ${entry.difficulty_level}`);
    assert.equal(spec.binsKey, 'allocations');
    assert.deepEqual(spec.payloadValues.map((v) => v.key), ['total']);
    assert.equal(spec.payloadValues[0]!.value, payload.total);
  }
});

test('C-EG-01 binCount ramps 2 -> 5 across L1-L5, measured directly from the frozen fixture', () => {
  const counts = EG01_ENTRIES.map((entry) => (entry.prompt_payload as { number_of_groups: number }).number_of_groups);
  assert.deepEqual(counts, [2, 3, 3, 4, 5]);
});

test('the bin-count payload key never appears in payloadValues (consumed structurally, not rendered twice)', () => {
  for (const entry of [...EG01_ENTRIES, ...SF01_ENTRIES]) {
    const spec = resolvePartitionAllocationSpec(makeTask(entry, 'C-GF-07'));
    assert.notEqual(spec, null);
    const payloadKeys = spec!.payloadValues.map((v) => v.key);
    assert.equal(payloadKeys.includes('number_of_groups'), false);
    assert.equal(payloadKeys.includes('recipient_count'), false);
  }
});

test('resolves: a synthetic differently-named collection key still resolves if in COLLECTION_KEY_VOCABULARY (allocations)', () => {
  const task = makeTask(SF01_ENTRIES[0]!, 'C-GF-08');
  const spec = resolvePartitionAllocationSpec(task);
  assert.notEqual(spec, null);
  assert.equal(spec!.binsKey, 'allocations');
});

test('C-EG-01 resolves to partition-allocation, not any other archetype', () => {
  const entry = EG01_ENTRIES[0]!;
  assert.equal(resolveArchetype('C-EG-01', entry.valid_action_space), 'partition-allocation');
});

test('C-SF-01 resolves to partition-allocation, not any other archetype', () => {
  const entry = SF01_ENTRIES[0]!;
  assert.equal(resolveArchetype('C-SF-01', entry.valid_action_space), 'partition-allocation');
});
