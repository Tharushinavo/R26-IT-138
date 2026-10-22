import { test } from 'node:test';
import assert from 'node:assert/strict';

import { EXEMPLAR_ENTRIES } from '@/src/api/generated/c-prompt-exemplars';
import type { CNextTaskResponse } from '@/src/api/generated/openapi-types';
import { planTask } from '@/src/features/c-session/c-session-logic';
import { resolveLinePositionSpec } from '@/src/features/c-session/archetypes/line-position-logic';
import { resolveLineTraversalSpec } from '@/src/features/c-session/archetypes/line-traversal-logic';
import { resolveNamedIntegerFieldsSpec } from '@/src/features/c-session/archetypes/named-integer-fields-logic';
import { resolveObjectSetActionSpec } from '@/src/features/c-session/archetypes/object-set-action-logic';
import { resolveOptionSelectSpec } from '@/src/features/c-session/archetypes/option-select-logic';
import { resolveOrderedValueSequenceSpec } from '@/src/features/c-session/archetypes/ordered-value-sequence-logic';
import { resolvePartitionAllocationSpec } from '@/src/features/c-session/archetypes/partition-allocation-logic';
import { resolveValueReportSpec } from '@/src/features/c-session/archetypes/value-report-logic';

// WHICH TEMPLATES THIS APP CANNOT DRAW -- measured, not asserted from memory.
//
// The backend excludes exactly these from the selection pool so a child never meets "This one
// isn't ready" mid-game (backend/app/domain/live_engine_c/client_support.py, owner instruction
// 2026-09-28). That list is a copy of this app's behaviour, and a copy can go stale in either
// direction: ship a surface and the backend keeps excluding a template that now works; break a
// resolver and the backend keeps serving one that no longer does.
//
// This test is the thing that makes that impossible to do quietly. It runs every frozen exemplar
// -- all five difficulty levels of all thirty templates -- through the app's REAL resolvers, and
// asserts the unrenderable set is EXACTLY the three the backend knows about. Either kind of drift
// fails here, with a message naming the file to update.

const EXPECTED_UNRENDERABLE = ['C-CC-04', 'C-SF-02', 'C-TC-02'] as const;

const RESOLVERS: Record<string, (task: CNextTaskResponse) => unknown> = {
  'line-position': resolveLinePositionSpec,
  'line-traversal': resolveLineTraversalSpec,
  'named-integer-fields': resolveNamedIntegerFieldsSpec,
  'object-set-action': resolveObjectSetActionSpec,
  'option-select': resolveOptionSelectSpec,
  'ordered-value-sequence': resolveOrderedValueSequenceSpec,
  'partition-allocation': resolvePartitionAllocationSpec,
  'value-report': resolveValueReportSpec,
};

type Entry = (typeof EXEMPLAR_ENTRIES)[number] & Record<string, unknown>;

function makeTask(entry: Entry): CNextTaskResponse {
  return {
    blanks: (entry.blanks as number | null) ?? null,
    c_task_instance_id: 'instance-1',
    difficulty_level: (entry.difficulty_level as number) ?? 1,
    game_family_id: (entry.game_family_id as string) ?? 'C-GF-01',
    game_task_template_id: entry.game_task_template_id as string,
    interactive_assets: (entry.interactive_assets as Record<string, unknown>) ?? {},
    prompt_payload: (entry.prompt_payload as Record<string, unknown>) ?? {},
    prompt_text: entry.prompt_text as string,
    representation_mode: (entry.representation_mode as string) ?? 'concrete',
    request_id: 'req-1',
    scaffold_state: (entry.scaffold_state as string) ?? 'C0',
    skill_id: (entry.skill_id as string) ?? 'counting',
    task_index: 1,
    technical_status: 'OK',
    valid_action_space: (entry.valid_action_space as Record<string, string>) ?? {},
  };
}

function renderableCounts() {
  const rows = new Map<string, { ok: number; failed: number }>();
  for (const raw of EXEMPLAR_ENTRIES) {
    const entry = raw as Entry;
    const id = entry.game_task_template_id as string;
    const row = rows.get(id) ?? { ok: 0, failed: 0 };
    const task = makeTask(entry);
    const plan = planTask(task);
    const resolver = plan.kind === 'fail-closed' ? null : RESOLVERS[plan.archetypeId];
    if (!resolver || resolver(task) === null) row.failed += 1;
    else row.ok += 1;
    rows.set(id, row);
  }
  return rows;
}

test('exactly the templates the backend excludes are the ones this app cannot draw', () => {
  const rows = renderableCounts();
  const unrenderable = [...rows.entries()]
    .filter(([, row]) => row.ok === 0)
    .map(([id]) => id)
    .sort();
  assert.deepEqual(
    unrenderable,
    [...EXPECTED_UNRENDERABLE],
    'Update CLIENT_UNRENDERABLE_TEMPLATE_IDS in backend/app/domain/live_engine_c/client_support.py to match, then this list.',
  );
});

test('no template renders at some difficulty levels and not others', () => {
  // A partial template is the worst case: the backend cannot exclude it without losing the levels
  // that work, and cannot serve it without the child hitting a dead end on the levels that do not.
  // If one ever appears, it needs a decision, not a silent denylist entry.
  const partial = [...renderableCounts().entries()]
    .filter(([, row]) => row.ok > 0 && row.failed > 0)
    .map(([id]) => id);
  assert.deepEqual(partial, [], 'partially renderable templates need an owner decision');
});

test('the vast majority of templates do render, so the exclusion list stays small', () => {
  const rows = renderableCounts();
  const renderable = [...rows.values()].filter((row) => row.ok > 0).length;
  assert.equal(rows.size, 30);
  assert.equal(renderable, 30 - EXPECTED_UNRENDERABLE.length);
});
