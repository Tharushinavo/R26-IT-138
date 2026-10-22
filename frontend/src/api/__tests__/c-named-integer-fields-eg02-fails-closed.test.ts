// NAMED EXCEPTION (10g): this file previously asserted C-EG-02 fails closed at every difficulty
// level. That fact is exactly what this batch changes -- C-EG-02 is now a supported, second scene
// of `named-integer-fields`, reading `rows`/`cols` structurally as the array grid's dimensions and
// admitting `direction` as a single named string exception (see named-integer-fields-logic.ts's own
// header, "C-EG-02 IS SUPPORTED HERE"). The file is inverted here rather than deleted, following
// 10d's own `c-mcl-family-surface-registration.test.ts` precedent for the identical situation: the
// tests below now assert C-EG-02 RESOLVES, with the corrected reasoning documented alongside each.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';
import { resolveNamedIntegerFieldsSpec } from '@/src/features/c-session/archetypes/named-integer-fields-logic';

const EG02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-EG-02');

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-07',
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

test('C-EG-02 has 5 exemplar rows and resolves to the named-integer-fields archetype id', () => {
  assert.equal(EG02_ENTRIES.length, 5);
  const entry = EG02_ENTRIES[0]!;
  assert.equal(resolveArchetype('C-EG-02', entry.valid_action_space), 'named-integer-fields');
});

test('C-EG-02 resolves at every difficulty level (10g reverses 10f\'s own deliberate refusal, having built the grid the payload/action-key overlap required)', () => {
  for (const entry of EG02_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    if (spec === null) {
      assert.fail(`C-EG-02 level ${entry.difficulty_level} should resolve now`);
      continue;
    }
    const payload = entry.prompt_payload as { rows: number; cols: number; direction: string };
    assert.deepEqual(spec.grid, { rows: payload.rows, cols: payload.cols }, `level ${entry.difficulty_level}`);
    assert.equal(spec.direction, payload.direction, `level ${entry.difficulty_level}`);
    assert.equal(spec.promptText, entry.prompt_text);
  }
});

test('difficulty 1-4 carry direction "read"; difficulty 5 alone carries "build", matching the real data\'s own asymmetry', () => {
  const directions = EG02_ENTRIES.map((entry) => (entry.prompt_payload as { direction: string }).direction);
  assert.deepEqual(directions, ['read', 'read', 'read', 'read', 'build']);
});

test('difficulty 5\'s prompt_text differs from L1-4\'s (the build variant vs the read one) and both survive resolution unchanged', () => {
  const l4 = EG02_ENTRIES[3]!;
  const l5 = EG02_ENTRIES[4]!;
  assert.notEqual(l4.prompt_text, l5.prompt_text);
  // Asserted by VARIANT, not by literal wording: this test is about resolution, and pinning
  // the sentence made a content edit fail it. The copy is pinned by the backend artefact.
  assert.equal((l5.prompt_payload as { direction: string }).direction, 'build');
  assert.equal((l4.prompt_payload as { direction: string }).direction, 'read');
  const specL4 = resolveNamedIntegerFieldsSpec(makeTask(l4));
  const specL5 = resolveNamedIntegerFieldsSpec(makeTask(l5));
  assert.notEqual(specL4, null);
  assert.notEqual(specL5, null);
  assert.equal(specL4!.promptText, l4.prompt_text);
  assert.equal(specL5!.promptText, l5.prompt_text);
});

test('rows and cols never appear in payloadValues for C-EG-02 (consumed structurally by spec.grid instead)', () => {
  for (const entry of EG02_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    const payloadKeys = spec!.payloadValues.map((v) => v.key);
    assert.equal(payloadKeys.includes('rows'), false);
    assert.equal(payloadKeys.includes('cols'), false);
    assert.deepEqual(spec!.payloadValues, [], `level ${entry.difficulty_level}: C-EG-02 has no payload key outside rows/cols/direction`);
  }
});

test('C-EG-02 still resolves exactly 3 integer fields (rows, cols, submitted_product), same two-layer rule as every other named-integer-fields template', () => {
  for (const entry of EG02_ENTRIES) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.equal(spec!.fields.length, 3, `level ${entry.difficulty_level}`);
    assert.deepEqual(spec!.fields.map((f) => f.key).sort(), ['cols', 'rows', 'submitted_product']);
  }
});

test('C-BT-01..04 are unaffected: grid and direction are both null for them', () => {
  const btEntries = EXEMPLAR_ENTRIES.filter((entry) => ['C-BT-01', 'C-BT-02', 'C-BT-03', 'C-BT-04'].includes(entry.game_task_template_id));
  for (const entry of btEntries) {
    const spec = resolveNamedIntegerFieldsSpec(makeTask(entry));
    assert.notEqual(spec, null);
    assert.equal(spec!.grid, null, `${entry.game_task_template_id} level ${entry.difficulty_level}`);
    assert.equal(spec!.direction, null, `${entry.game_task_template_id} level ${entry.difficulty_level}`);
  }
});
