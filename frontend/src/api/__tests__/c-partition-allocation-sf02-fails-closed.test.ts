// C-SF-02 resolves to `partition-allocation` (registry.ts maps it there), so registering that
// surface makes SF-02 reachable. This file pins down that it fails closed anyway -- structurally, on
// its own declared shape (an extra `integer-field` key alongside the collection), never on a
// template-id refusal -- and pins WHY, so the guard is not later "tidied away" as apparently
// redundant. See partition-allocation-logic.ts's header, "THE FIXED/VARIABLE DISCRIMINANT IS
// TYPE-LEVEL, NEVER A TEMPLATE ID".
//
// 10H RULED THIS REFUSAL PERMANENT (2026-08-26). This file was originally written under 10f's
// convention (c-named-integer-fields-eg02-fails-closed.test.ts), where the analogous C-EG-02 refusal
// was provisional and a later batch duly closed it. C-SF-02's is NOT that kind: unlike C-EG-01 and
// C-SF-01, it declares no bin-count key in `prompt_payload` at all, so the number of bins IS the
// answer (and is itself a declared `valid_action_space` key). Rendering the right number of slots
// would render the answer; deriving it from `total`/`group_size` would compute an answer key
// client-side. That falsifies C-18's "a new template within an existing archetype is configuration,
// not a new screen" -- the §2.3 falsification test finding, in backend/buildLog2.md's 10h entry.
// These four tests are therefore a permanent guard, not a placeholder awaiting inversion: do not
// delete or invert them without a fresh owner ruling superseding 10h's.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import assert from 'node:assert/strict';

import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import { resolveArchetype } from '@/src/features/c-session/archetypes/registry';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';

const here = dirname(fileURLToPath(import.meta.url));

const SF02_ENTRIES = EXEMPLAR_ENTRIES.filter((entry) => entry.game_task_template_id === 'C-SF-02');

function makeTask(entry: (typeof EXEMPLAR_ENTRIES)[number]): CNextTaskResponse {
  return {
    blanks: entry.blanks,
    c_task_instance_id: 'task-1',
    difficulty_level: entry.difficulty_level,
    game_family_id: 'C-GF-08',
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

test('C-SF-02 has 5 exemplar rows and resolves to the partition-allocation archetype id', () => {
  assert.equal(SF02_ENTRIES.length, 5);
  const entry = SF02_ENTRIES[0]!;
  assert.equal(resolveArchetype('C-SF-02', entry.valid_action_space), 'partition-allocation');
});

// A surface IS registered for partition-allocation by this batch -- SF-02 therefore genuinely
// reaches this resolver, not a missing-surface fail-closed. Checked by reading archetype-surfaces.ts
// as text rather than importing it, since that module pulls in real React Native surface components
// which esbuild/node --test cannot transform -- the same constraint every prior archetype's own
// analogous test observes.
test('archetype-surfaces.ts registers a SURFACE_TABLE entry for partition-allocation (source check, not a runtime import)', () => {
  const source = readFileSync(
    resolve(here, '..', '..', 'features', 'c-session', 'archetype-surfaces.ts'),
    'utf-8',
  );
  assert.match(source, /'partition-allocation':\s*PartitionAllocationSurface/);
});

test('C-SF-02 nonetheless fails closed at every difficulty level, because its declared action space carries an extra integer-field key (submitted_group_count)', () => {
  for (const entry of SF02_ENTRIES) {
    assert.ok(
      Object.prototype.hasOwnProperty.call(entry.valid_action_space, 'submitted_group_count'),
      `level ${entry.difficulty_level}: expected the real data to declare submitted_group_count`,
    );
    const spec = resolvePartitionAllocationSpec(makeTask(entry));
    assert.equal(spec, null, `C-SF-02 level ${entry.difficulty_level} should fail closed`);
  }
});

test('the refusal is structural (the extra integer-field guard), not a game_task_template_id === \'C-SF-02\' branch', () => {
  const task = makeTask(SF02_ENTRIES[0]!);
  // Strip the offending extra action-space key AND supply a recognised bin-count payload key (real
  // C-SF-02 data has neither `number_of_groups` nor `recipient_count`, so leaving the payload
  // untouched would fail closed on THAT guard instead, muddying which guard this test isolates) --
  // confirm resolution then SUCCEEDS, proving the refusal traces to the integer-field guard alone,
  // not to template-id special-casing anywhere in the file.
  const { submitted_group_count: _extra, ...fixedShapeActionSpace } = task.valid_action_space;
  task.valid_action_space = fixedShapeActionSpace;
  task.prompt_payload = { ...(task.prompt_payload as Record<string, unknown>), recipient_count: 3 };
  const spec = resolvePartitionAllocationSpec(task);
  assert.notEqual(spec, null, 'with the extra key removed and a bin-count key supplied, the same C-SF-02 task resolves fine -- proving no template-id refusal exists');
});
